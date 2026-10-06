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
