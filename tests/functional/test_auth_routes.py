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


def _get_reset_token_for(email, caplog):
    """Extrae el token en texto plano del log de simulación tras una solicitud de reset."""
    for record in caplog.records:
        if "/auth/reset-password/" in record.message:
            return record.message.rsplit("/auth/reset-password/", 1)[1].strip()
    raise AssertionError("No se encontró el token simulado en el log")


# --- US3 (Incremento 2): Recuperación Segura de Contraseña (HU-14) ---

def test_forgot_password_neutral_response_for_existing_email(client, caplog):
    """Verifica respuesta neutra 200 para una cuenta existente."""
    client.post(
        "/auth/register",
        data={"email": "forgotexists@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )

    with caplog.at_level("INFO"):
        response = client.post(
            "/auth/forgot-password",
            data={"email": "forgotexists@example.com"},
            headers={"Accept": "application/json"},
        )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


def test_forgot_password_neutral_response_for_nonexistent_email(client):
    """Verifica la misma respuesta neutra 200 para una cuenta inexistente."""
    response = client.post(
        "/auth/forgot-password",
        data={"email": "noexiste@example.com"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


def test_forgot_password_invalid_email_format(client):
    """Verifica 400 Bad Request ante un formato de correo inválido."""
    response = client.post(
        "/auth/forgot-password",
        data={"email": "no-es-un-correo"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_EMAIL_FORMAT"


def test_reset_password_get_valid_token_renders_form(client, caplog):
    """Verifica que un token válido renderice el formulario (200)."""
    client.post(
        "/auth/register",
        data={"email": "resetformuser@example.com", "password": "Password123!"},
        headers={"Accept": "application/json"},
    )
    with caplog.at_level("INFO"):
        client.post(
            "/auth/forgot-password",
            data={"email": "resetformuser@example.com"},
            headers={"Accept": "application/json"},
        )
    token = _get_reset_token_for("resetformuser@example.com", caplog)

    response = client.get(f"/auth/reset-password/{token}")
    assert response.status_code == 200


def test_reset_password_get_invalid_token_returns_400(client):
    """Verifica 400 Bad Request para un token inexistente o alterado."""
    response = client.get("/auth/reset-password/token-invalido-inventado")
    assert response.status_code == 400


def test_reset_password_post_success_updates_password(client, caplog):
    """Verifica que el POST actualice la contraseña e invalide el token."""
    client.post(
        "/auth/register",
        data={"email": "resetpostuser@example.com", "password": "OldPassword123!"},
        headers={"Accept": "application/json"},
    )
    with caplog.at_level("INFO"):
        client.post(
            "/auth/forgot-password",
            data={"email": "resetpostuser@example.com"},
            headers={"Accept": "application/json"},
        )
    token = _get_reset_token_for("resetpostuser@example.com", caplog)

    response = client.post(
        f"/auth/reset-password/{token}",
        data={
            "new_password": "NewPassword456!",
            "confirm_password": "NewPassword456!",
        },
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"

    # El login con la nueva contraseña debe funcionar
    login_resp = client.post(
        "/auth/login",
        data={"email": "resetpostuser@example.com", "password": "NewPassword456!"},
        headers={"Accept": "application/json"},
    )
    assert login_resp.status_code == 200

    # El token ya no debe ser reutilizable
    reuse_resp = client.post(
        f"/auth/reset-password/{token}",
        data={
            "new_password": "AnotherPassword789!",
            "confirm_password": "AnotherPassword789!",
        },
        headers={"Accept": "application/json"},
    )
    assert reuse_resp.status_code == 400
    assert reuse_resp.get_json()["code"] == "PASSWORD_RESET_FAILED"


def test_reset_password_post_mismatched_passwords_fails(client, caplog):
    """Verifica 400 Bad Request cuando las contraseñas no coinciden."""
    client.post(
        "/auth/register",
        data={"email": "resetmismatch@example.com", "password": "OldPassword123!"},
        headers={"Accept": "application/json"},
    )
    with caplog.at_level("INFO"):
        client.post(
            "/auth/forgot-password",
            data={"email": "resetmismatch@example.com"},
            headers={"Accept": "application/json"},
        )
    token = _get_reset_token_for("resetmismatch@example.com", caplog)

    response = client.post(
        f"/auth/reset-password/{token}",
        data={"new_password": "NewPassword456!", "confirm_password": "Diferente789!"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400
    assert response.get_json()["code"] == "PASSWORD_RESET_FAILED"


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
