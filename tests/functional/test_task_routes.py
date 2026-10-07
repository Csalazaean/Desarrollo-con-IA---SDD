import re


def _login_as(client, email="user@example.com", password="Password123!"):
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


# --- US3: Creación de Tareas ---

def test_create_task_unauthenticated_fails(client):
    """Verifica 401 Unauthorized sin sesión activa."""
    response = client.post(
        "/tasks",
        data={"title": "Tarea no autorizada"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 401


def test_create_task_authenticated_success(client):
    """Verifica creación de tarea con sesión activa."""
    _login_as(client, "createuser@example.com")

    response = client.post(
        "/tasks",
        data={
            "title": "Aprender Spec Kit",
            "description": "Monolito y principios",
            "due_date": "2026-10-20",
        },
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["status"] == "success"
    assert data["data"]["title"] == "Aprender Spec Kit"
    assert data["data"]["status"] == "pending"


def test_create_task_validation_error(client):
    """Verifica error 400 Bad Request si el título está vacío."""
    _login_as(client, "emptyuser@example.com")

    response = client.post(
        "/tasks",
        data={"title": "   "},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == "VALIDATION_ERROR"


# --- US4: Listado y Filtrado de Tareas ---

def test_list_tasks_authenticated(client):
    """Verifica listado exclusivo de tareas del usuario y soporte de filtros."""
    _login_as(client, "listuser@example.com")

    client.post(
        "/tasks",
        data={"title": "Tarea Pendiente"},
        headers={"Accept": "application/json"},
    )
    res2 = client.post(
        "/tasks",
        data={"title": "Tarea Para Completar"},
        headers={"Accept": "application/json"},
    )
    t2_id = res2.get_json()["data"]["id"]

    client.post(
        f"/tasks/{t2_id}/status",
        data={"status": "completed"},
        headers={"Accept": "application/json"},
    )

    # 1. Listar todas
    response_all = client.get("/tasks", headers={"Accept": "application/json"})
    assert response_all.status_code == 200
    assert response_all.get_json()["data"]["count"] == 2

    # 2. Filtrar por completadas
    response_completed = client.get(
        "/tasks?status=completed", headers={"Accept": "application/json"}
    )
    assert response_completed.status_code == 200
    assert response_completed.get_json()["data"]["count"] == 1


# --- US5: Cambio de Estado de Tareas ---

def test_update_task_status_route(client):
    """Verifica transición de estado válida y rechazo de reapertura."""
    _login_as(client, "statususer@example.com")

    res = client.post(
        "/tasks",
        data={"title": "Tarea Ciclo"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    # pending -> in_progress
    resp = client.post(
        f"/tasks/{task_id}/status",
        data={"status": "in_progress"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["current_status"] == "in_progress"

    # in_progress -> completed
    resp = client.post(
        f"/tasks/{task_id}/status",
        data={"status": "completed"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["current_status"] == "completed"

    # completed -> pending (BLOQUEADO en este incremento)
    resp = client.post(
        f"/tasks/{task_id}/status",
        data={"status": "pending"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_STATE_TRANSITION"


# --- US6: Edición de Tareas ---

def test_edit_task_route(client):
    """Verifica edición de título y descripción con validación de permisos."""
    _login_as(client, "edituser@example.com")

    res = client.post(
        "/tasks",
        data={"title": "Tarea Original"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    # Edición exitosa
    resp = client.post(
        f"/tasks/{task_id}/edit",
        data={"title": "Tarea Editada", "description": "Nueva descripción"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["title"] == "Tarea Editada"

    # Título vacío falla con 400
    resp_empty = client.post(
        f"/tasks/{task_id}/edit",
        data={"title": ""},
        headers={"Accept": "application/json"},
    )
    assert resp_empty.status_code == 400


# --- US1 (HU-05): Eliminación Lógica de Tareas (Endpoints) ---

def test_delete_task_unauthenticated(client):
    """Verifica 401 Unauthorized sin sesión activa."""
    resp = client.post("/tasks/1/delete", headers={"Accept": "application/json"})
    assert resp.status_code == 401


def test_delete_task_success_json(client):
    """Verifica eliminación lógica vía POST y DELETE con respuesta JSON 200 OK."""
    _login_as(client, "deletejson@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea para borrar en JSON"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(f"/tasks/{task_id}/delete", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["task_id"] == task_id
    assert data["data"]["is_deleted"] is True

    # Comprobar que ya no aparece en GET /tasks
    list_resp = client.get("/tasks", headers={"Accept": "application/json"})
    active_ids = [t["id"] for t in list_resp.get_json()["data"]["tasks"]]
    assert task_id not in active_ids


def test_delete_task_success_html(client):
    """Verifica eliminación lógica con formulario HTML retornando 302 Found hacia /tasks."""
    _login_as(client, "deletehtml@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea para borrar en HTML"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(f"/tasks/{task_id}/delete", headers={"Accept": "text/html"})
    assert resp.status_code == 302
    assert "/tasks" in resp.headers["Location"]


def test_delete_task_unauthorized_other_user(client):
    """Verifica que un usuario no pueda eliminar la tarea de otro (404 Not Found)."""
    _login_as(client, "owner@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea privada"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    _login_as(client, "intruder@example.com")
    resp = client.post(f"/tasks/{task_id}/delete", headers={"Accept": "application/json"})
    assert resp.status_code == 404


def test_delete_task_already_deleted_fails(client):
    """Verifica que eliminar una tarea ya eliminada falle con 400/409 TASK_ALREADY_DELETED."""
    _login_as(client, "doubledelete@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea doble eliminación"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    first_delete = client.post(f"/tasks/{task_id}/delete", headers={"Accept": "application/json"})
    assert first_delete.status_code == 200

    second_delete = client.post(f"/tasks/{task_id}/delete", headers={"Accept": "application/json"})
    assert second_delete.status_code in {400, 409}
    assert second_delete.get_json()["code"] == "TASK_ALREADY_DELETED"


# --- US2 (HU-06): Reapertura de Tareas Completadas (Endpoints) ---

def test_reopen_task_unauthenticated(client):
    """Verifica 401 Unauthorized sin sesión activa."""
    resp = client.post("/tasks/1/reopen", headers={"Accept": "application/json"})
    assert resp.status_code == 401


def test_reopen_task_success_json(client):
    """Verifica reapertura exitosa vía JSON 200 OK retornando status pending."""
    _login_as(client, "reopenjson@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea a reabrir JSON"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    # Completar la tarea
    client.post(
        f"/tasks/{task_id}/status",
        data={"status": "completed"},
        headers={"Accept": "application/json"},
    )

    # Reabrir la tarea
    resp = client.post(f"/tasks/{task_id}/reopen", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["task_id"] == task_id
    assert data["data"]["status"] == "pending"


def test_reopen_task_success_html(client):
    """Verifica reapertura exitosa vía formulario HTML retornando 302 Found hacia /tasks."""
    _login_as(client, "reopenhtml@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea a reabrir HTML"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    client.post(
        f"/tasks/{task_id}/status",
        data={"status": "completed"},
        headers={"Accept": "application/json"},
    )

    resp = client.post(f"/tasks/{task_id}/reopen", headers={"Accept": "text/html"})
    assert resp.status_code == 302
    assert "/tasks" in resp.headers["Location"]


def test_reopen_task_invalid_state_fails(client):
    """Verifica error 400 si se intenta reabrir una tarea no completada."""
    _login_as(client, "reopeninvalid@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea aún pendiente"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(f"/tasks/{task_id}/reopen", headers={"Accept": "application/json"})
    assert resp.status_code == 400
    assert resp.get_json()["code"] in {"INVALID_STATE_FOR_REOPEN", "INVALID_STATE_TRANSITION"}


def test_reopen_task_unauthorized_other_user(client):
    """Verifica que un usuario no pueda reabrir tareas de otro (404 Not Found)."""
    _login_as(client, "owner2@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea completada de owner2"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]
    client.post(f"/tasks/{task_id}/status", data={"status": "completed"}, headers={"Accept": "application/json"})

    _login_as(client, "intruder2@example.com")
    resp = client.post(f"/tasks/{task_id}/reopen", headers={"Accept": "application/json"})
    assert resp.status_code == 404


# --- Regresión de interfaz: los formularios renderizados deben ser utilizables ---


def test_rendered_delete_form_action_accepts_post(client):
    """El formulario "Eliminar" del listado debe funcionar tal como se renderiza.

    Regresión: `url_for` resolvía al endpoint que solo acepta DELETE, así que el
    formulario del navegador apuntaba a /tasks/<id> y respondía 405. Las pruebas
    anteriores no lo detectaban porque invocaban /tasks/<id>/delete directamente.
    """
    _login_as(client, "formdelete@example.com")
    client.post("/tasks", data={"title": "Tarea para borrar desde la interfaz"})

    pagina = client.get("/tasks").get_data(as_text=True)
    accion = re.search(r'action="(/tasks/\d+(?:/delete)?)" method="POST"', pagina)
    assert accion, "El listado debe renderizar el formulario de eliminación"

    respuesta = client.post(accion.group(1))
    assert respuesta.status_code != 405, (
        f"El formulario apunta a {accion.group(1)}, que no acepta POST"
    )
    assert respuesta.status_code in (200, 302)

    # Y la tarea efectivamente desaparece del listado
    restante = client.get("/tasks").get_data(as_text=True)
    assert "Tarea para borrar desde la interfaz" not in restante


def test_rendered_reopen_form_action_accepts_post(client):
    """El formulario "Reabrir" de una tarea completada debe funcionar tal como se renderiza."""
    _login_as(client, "formreopen@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea para reabrir desde la interfaz"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]
    client.post(f"/tasks/{task_id}/status", data={"status": "completed"})

    pagina = client.get("/tasks").get_data(as_text=True)
    accion = re.search(r'action="(/tasks/\d+/reopen)"', pagina)
    assert accion, "Una tarea completada debe ofrecer el formulario de reapertura"

    respuesta = client.post(accion.group(1))
    assert respuesta.status_code != 405
    assert respuesta.status_code in (200, 302)
