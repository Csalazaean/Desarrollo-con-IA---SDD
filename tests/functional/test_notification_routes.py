def _login_as(client, email="notifuser@example.com", password="Password123!"):
    client.post(
        "/auth/register",
        data={"email": email, "password": password},
        headers={"Accept": "application/json"},
    )
    client.post(
        "/auth/login",
        data={"email": email, "password": password},
        headers={"Accept": "application/json"},
    )


def _create_and_assign_task(client, owner_email, recipient_email, title="Tarea"):
    _login_as(client, recipient_email)  # pre-registra al destinatario
    _login_as(client, owner_email)
    res = client.post("/tasks", data={"title": title}, headers={"Accept": "application/json"})
    task_id = res.get_json()["data"]["id"]
    client.post(
        f"/tasks/{task_id}/assign",
        data={"assigned_to_email": recipient_email},
        headers={"Accept": "application/json"},
    )
    return task_id


# --- US2 (Incremento 4): Notificaciones Internas de Asignación (HU-11) ---

def test_list_notifications_unauthenticated_fails(client):
    """Verifica 401 Unauthorized sin sesión activa."""
    response = client.get("/notifications", headers={"Accept": "application/json"})
    assert response.status_code == 401


def test_list_notifications_includes_unread_count(client):
    """Verifica que GET /notifications incluya unread_count y la notificación generada."""
    _create_and_assign_task(client, "notifowner@example.com", "notifreceiver@example.com", "Tarea Notificada")

    _login_as(client, "notifreceiver@example.com")
    resp = client.get("/notifications", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["unread_count"] == 1
    assert len(data["notifications"]) == 1
    assert "Tarea Notificada" in data["notifications"][0]["message"]


def test_mark_notification_as_read_route(client):
    """Verifica que marcar una notificación como leída funcione vía HTTP."""
    _create_and_assign_task(client, "notifowner2@example.com", "notifreceiver2@example.com")

    _login_as(client, "notifreceiver2@example.com")
    listing = client.get("/notifications", headers={"Accept": "application/json"})
    notification_id = listing.get_json()["data"]["notifications"][0]["id"]

    resp = client.post(f"/notifications/{notification_id}/read", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_read"] is True


def test_mark_notification_as_read_other_user_404(client):
    """Verifica 404 al intentar marcar una notificación de otro usuario."""
    _create_and_assign_task(client, "notifowner3@example.com", "notifreceiver3@example.com")

    _login_as(client, "notifreceiver3@example.com")
    listing = client.get("/notifications", headers={"Accept": "application/json"})
    notification_id = listing.get_json()["data"]["notifications"][0]["id"]

    _login_as(client, "notifintruder@example.com")
    resp = client.post(f"/notifications/{notification_id}/read", headers={"Accept": "application/json"})
    assert resp.status_code == 404


def test_mark_all_as_read_route(client):
    """Verifica que marcar todas como leídas funcione vía HTTP."""
    _create_and_assign_task(client, "notifowner4@example.com", "notifreceiver4@example.com", "Tarea 1")
    _login_as(client, "notifowner4@example.com")
    task2 = client.post("/tasks", data={"title": "Tarea 2"}, headers={"Accept": "application/json"}).get_json()["data"]["id"]
    client.post(
        f"/tasks/{task2}/assign",
        data={"assigned_to_email": "notifreceiver4@example.com"},
        headers={"Accept": "application/json"},
    )

    _login_as(client, "notifreceiver4@example.com")
    resp = client.post("/notifications/mark-all-read", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["updated_count"] == 2

    listing = client.get("/notifications", headers={"Accept": "application/json"})
    assert listing.get_json()["data"]["unread_count"] == 0
