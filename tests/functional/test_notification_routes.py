JSON = {"Accept": "application/json"}


def _registrar_y_entrar(client, email, password="Password123!"):
    client.post("/auth/register", data={"email": email, "password": password}, headers=JSON)
    client.post("/auth/login", data={"email": email, "password": password}, headers=JSON)


def _registrar(client, email, password="Password123!"):
    client.post("/auth/register", data={"email": email, "password": password}, headers=JSON)


def _asignar_a(client, creador, destinatario, titulo="Tarea delegada"):
    """Crea una tarea como `creador` y se la asigna a `destinatario`."""
    _registrar_y_entrar(client, creador)
    task_id = client.post("/tasks", data={"title": titulo}, headers=JSON).get_json()["data"]["id"]
    client.post(
        f"/tasks/{task_id}/assign", data={"assignee_email": destinatario}, headers=JSON
    )
    return task_id


def test_notifications_require_session(client):
    """Todos los endpoints de notificación exigen sesión activa (FR-014)."""
    assert client.get("/notifications", headers=JSON).status_code == 401
    assert client.post("/notifications/1/read", headers=JSON).status_code == 401
    assert client.post("/notifications/read-all", headers=JSON).status_code == 401


def test_list_notifications_authenticated(client):
    """GET /notifications lista las propias con su contador de no leídas (FR-010)."""
    _registrar(client, "n-b@example.com")
    _asignar_a(client, "n-a@example.com", "n-b@example.com", "Revisar informe")

    _registrar_y_entrar(client, "n-b@example.com")
    res = client.get("/notifications", headers=JSON)
    assert res.status_code == 200

    datos = res.get_json()["data"]
    assert datos["unread_count"] == 1
    assert len(datos["notifications"]) == 1
    assert "Revisar informe" in datos["notifications"][0]["message"]
    assert datos["notifications"][0]["is_read"] is False


def test_mark_notification_read_endpoint(client):
    """POST /notifications/<id>/read marca la notificación y decrementa el contador."""
    _registrar(client, "n-d@example.com")
    _asignar_a(client, "n-c@example.com", "n-d@example.com")

    _registrar_y_entrar(client, "n-d@example.com")
    notificacion = client.get("/notifications", headers=JSON).get_json()["data"]["notifications"][0]

    res = client.post(f"/notifications/{notificacion['id']}/read", headers=JSON)
    assert res.status_code == 200
    assert res.get_json()["data"]["is_read"] is True
    assert res.get_json()["data"]["unread_count"] == 0

    # Sigue en el historial tras leerse (FR-013)
    posterior = client.get("/notifications", headers=JSON).get_json()["data"]
    assert len(posterior["notifications"]) == 1


def test_mark_all_read_endpoint(client):
    """POST /notifications/read-all marca el lote completo (FR-012)."""
    _registrar(client, "n-f@example.com")
    for titulo in ("Uno", "Dos", "Tres"):
        _asignar_a(client, "n-e@example.com", "n-f@example.com", titulo)

    _registrar_y_entrar(client, "n-f@example.com")
    assert client.get("/notifications", headers=JSON).get_json()["data"]["unread_count"] == 3

    res = client.post("/notifications/read-all", headers=JSON)
    assert res.status_code == 200
    assert res.get_json()["data"]["marked_count"] == 3
    assert res.get_json()["data"]["unread_count"] == 0


def test_cannot_mark_notification_of_another_user(client):
    """Una notificación ajena responde 404, sin confirmar siquiera que exista (FR-014)."""
    _registrar(client, "n-h@example.com")
    _asignar_a(client, "n-g@example.com", "n-h@example.com")

    _registrar_y_entrar(client, "n-h@example.com")
    notificacion_id = client.get("/notifications", headers=JSON).get_json()["data"]["notifications"][0]["id"]

    _registrar_y_entrar(client, "n-i@example.com")
    res = client.post(f"/notifications/{notificacion_id}/read", headers=JSON)
    assert res.status_code == 404

    # Y no aparece en el listado del intruso
    assert client.get("/notifications", headers=JSON).get_json()["data"]["notifications"] == []


def test_notification_counter_available_in_navigation(client):
    """El contador de no leídas se expone a las plantillas en cualquier página (FR-011)."""
    _registrar(client, "n-k@example.com")
    _asignar_a(client, "n-j@example.com", "n-k@example.com")

    _registrar_y_entrar(client, "n-k@example.com")
    html = client.get("/tasks").get_data(as_text=True)
    assert "/notifications" in html
    assert "notification-badge" in html
