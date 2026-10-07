from datetime import datetime, timedelta, timezone
from src.taskcontrol.extensions import db
from src.taskcontrol.models.password_reset import PasswordResetToken
from src.taskcontrol.models.user import User
from src.taskcontrol.services.user_service import UserService


def test_register_route_success(client):
    """Verifica que el endpoint de registro responda adecuadamente según el contrato."""
    response = client.post(
        "/auth/register",
        data={"email": "newuser@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code in [201, 302]
    if response.status_code == 201:
        data = response.get_json()
        assert data["status"] == "success"
        assert data["data"]["email"] == "newuser@example.com"


def test_register_route_duplicate_email(client):
    """Verifica respuesta 409 Conflict al registrar correo existente."""
    client.post(
        "/auth/register",
        data={"email": "dupe@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )
    response = client.post(
        "/auth/register",
        data={"email": "dupe@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 409
    data = response.get_json()
    assert data["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_route_validation_error(client):
    """Verifica respuesta 400 Bad Request cuando los datos son inválidos."""
    response = client.post(
        "/auth/register",
        data={"email": "invalid-email", "password": "123"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == "VALIDATION_ERROR"


def test_login_route_success(client):
    """Verifica inicio de sesión exitoso con establecimiento de sesión."""
    client.post(
        "/auth/register",
        data={"email": "loginuser@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )
    response = client.post(
        "/auth/login",
        data={"email": "loginuser@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"

    # Verificar que la sesión contiene el user_id
    with client.session_transaction() as sess:
        assert "user_id" in sess


def test_login_route_invalid_credentials(client):
    """Verifica rechazo con 401 Unauthorized ante credenciales erróneas."""
    response = client.post(
        "/auth/login",
        data={"email": "nonexistent@example.com", "password": "WrongPassword!"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["code"] == "INVALID_CREDENTIALS"


def test_logout_route(client):
    """Verifica que el cierre de sesión destruya la sesión activa."""
    client.post(
        "/auth/register",
        data={"email": "logoutuser@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )
    client.post(
        "/auth/login",
        data={"email": "logoutuser@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )
    response = client.post(
        "/auth/logout",
        headers={"Accept": "application/json"},
    )
    assert response.status_code in [200, 302]

    # Verificar que user_id fue eliminado de la sesión
    with client.session_transaction() as sess:
        assert "user_id" not in sess


# ---------------------------------------------------------------------------
# HU-14: Endpoints de recuperación de contraseña
# ---------------------------------------------------------------------------

MENSAJE_NEUTRO = "Si el correo ingresado coincide con una cuenta activa"


def _registrar(client, email, password="Password123!"):
    client.post(
        "/auth/register",
        data={"email": email, "password": password},
        headers={"Accept": "application/json"},
    )
    return User.query.filter_by(email=email).first()


def _emitir_token(user, minutes=30, used=False):
    """Emite un token de restablecimiento y retorna su valor en claro."""
    raw_token = UserService.generate_reset_token()
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=UserService.hash_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
        used_at=datetime.now(timezone.utc) if used else None,
    )
    db.session.add(token)
    db.session.commit()
    return raw_token


def test_forgot_password_endpoint_neutral_response(client):
    """El endpoint responde 200 con el mismo mensaje exista o no la cuenta."""
    _registrar(client, "olvido@example.com")

    respuesta_existente = client.post(
        "/auth/forgot-password",
        data={"email": "olvido@example.com"},
        headers={"Accept": "application/json"},
    )
    respuesta_inexistente = client.post(
        "/auth/forgot-password",
        data={"email": "nadie@example.com"},
        headers={"Accept": "application/json"},
    )

    assert respuesta_existente.status_code == 200
    assert respuesta_inexistente.status_code == 200

    # Indistinguibles: mismo código y mismo cuerpo
    assert respuesta_existente.get_json() == respuesta_inexistente.get_json()
    assert MENSAJE_NEUTRO in respuesta_existente.get_json()["message"]


def test_forgot_password_invalid_email_format(client):
    """Un correo mal formado responde 400 con el código del contrato."""
    response = client.post(
        "/auth/forgot-password",
        data={"email": "no-es-correo"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_EMAIL_FORMAT"


def test_reset_password_get_endpoint_valid_and_invalid_token(client):
    """GET muestra el formulario con token vigente y rechaza uno inválido."""
    user = _registrar(client, "getreset@example.com")
    raw_token = _emitir_token(user)

    valido = client.get(f"/auth/reset-password/{raw_token}")
    assert valido.status_code == 200

    invalido = client.get("/auth/reset-password/token-que-no-existe")
    assert invalido.status_code == 400


def test_reset_password_post_endpoint_success(client):
    """POST válido actualiza la contraseña, consume el token y redirige al login."""
    user = _registrar(client, "postreset@example.com", "PasswordVieja123!")
    raw_token = _emitir_token(user)

    response = client.post(
        f"/auth/reset-password/{raw_token}",
        data={"new_password": "PasswordNueva456!", "confirm_password": "PasswordNueva456!"},
    )
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

    assert PasswordResetToken.query.one().used_at is not None
    assert UserService.authenticate_user("postreset@example.com", "PasswordNueva456!") is not None


def test_reset_password_post_password_mismatch_or_short(client):
    """Contraseñas que no coinciden o demasiado cortas responden 400."""
    user = _registrar(client, "mismatch@example.com")
    raw_token = _emitir_token(user)

    no_coinciden = client.post(
        f"/auth/reset-password/{raw_token}",
        data={"new_password": "PasswordNueva456!", "confirm_password": "OtraDistinta789!"},
        headers={"Accept": "application/json"},
    )
    assert no_coinciden.status_code == 400
    assert no_coinciden.get_json()["code"] == "PASSWORD_RESET_FAILED"

    demasiado_corta = client.post(
        f"/auth/reset-password/{raw_token}",
        data={"new_password": "corta", "confirm_password": "corta"},
        headers={"Accept": "application/json"},
    )
    assert demasiado_corta.status_code == 400

    # Ningún intento fallido consume el token
    assert PasswordResetToken.query.one().used_at is None


def test_reset_password_post_used_or_expired_token(client):
    """Un token ya consumido o vencido responde 400."""
    user = _registrar(client, "consumido@example.com")

    usado = _emitir_token(user, used=True)
    respuesta_usado = client.post(
        f"/auth/reset-password/{usado}",
        data={"new_password": "PasswordNueva456!", "confirm_password": "PasswordNueva456!"},
        headers={"Accept": "application/json"},
    )
    assert respuesta_usado.status_code == 400
    assert respuesta_usado.get_json()["code"] == "PASSWORD_RESET_FAILED"

    expirado = _emitir_token(user, minutes=-1)
    respuesta_expirado = client.post(
        f"/auth/reset-password/{expirado}",
        data={"new_password": "PasswordNueva456!", "confirm_password": "PasswordNueva456!"},
        headers={"Accept": "application/json"},
    )
    assert respuesta_expirado.status_code == 400


def test_login_page_offers_password_recovery_link(client):
    """La pantalla de login enlaza al flujo de recuperación (HU-14)."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert "/auth/forgot-password" in response.get_data(as_text=True)
