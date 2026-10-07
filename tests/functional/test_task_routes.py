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


# --- US1 (Incremento 2): Eliminación Lógica de Tareas (HU-05) ---

def test_delete_task_unauthenticated_fails(client):
    """Verifica 401 Unauthorized al eliminar sin sesión activa."""
    response = client.post(
        "/tasks/1/delete", headers={"Accept": "application/json"}
    )
    assert response.status_code == 401


def test_delete_task_success_json(client):
    """Verifica eliminación lógica exitosa vía JSON."""
    _login_as(client, "deleteuser@example.com")

    res = client.post(
        "/tasks",
        data={"title": "Tarea a Eliminar"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(
        f"/tasks/{task_id}/delete", headers={"Accept": "application/json"}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["is_deleted"] is True
    assert data["data"]["deleted_at"] is not None

    # Ya no aparece en el listado por defecto
    listing = client.get("/tasks", headers={"Accept": "application/json"})
    assert listing.get_json()["data"]["count"] == 0


def test_delete_task_success_html_redirects(client):
    """Verifica eliminación exitosa vía formulario HTML (302 redirect)."""
    _login_as(client, "deletehtmluser@example.com")

    res = client.post(
        "/tasks",
        data={"title": "Tarea HTML"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(f"/tasks/{task_id}/delete")
    assert resp.status_code == 302


def test_delete_task_not_found_or_other_user(client):
    """Verifica 404 para tarea inexistente o de otro usuario."""
    _login_as(client, "deleteowner@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea Privada"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    # Tarea inexistente
    resp = client.post(
        "/tasks/999999/delete", headers={"Accept": "application/json"}
    )
    assert resp.status_code == 404

    # Tarea de otro usuario
    _login_as(client, "deleteintruder@example.com")
    resp_other = client.post(
        f"/tasks/{task_id}/delete", headers={"Accept": "application/json"}
    )
    assert resp_other.status_code == 404


def test_cannot_delete_already_deleted_task_route(client):
    """Verifica 400/409 al intentar eliminar una tarea ya eliminada."""
    _login_as(client, "doubledeleteuser@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea Doble"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    client.post(f"/tasks/{task_id}/delete", headers={"Accept": "application/json"})
    resp = client.post(
        f"/tasks/{task_id}/delete", headers={"Accept": "application/json"}
    )
    assert resp.status_code in (400, 409)
    assert resp.get_json()["code"] == "TASK_ALREADY_DELETED"


# --- US2 (Incremento 2): Reapertura de Tareas Completadas (HU-06) ---

def test_reopen_task_unauthenticated_fails(client):
    """Verifica 401 Unauthorized al reabrir sin sesión activa."""
    response = client.post(
        "/tasks/1/reopen", headers={"Accept": "application/json"}
    )
    assert response.status_code == 401


def test_reopen_task_success_json(client):
    """Verifica reapertura exitosa de una tarea completada vía JSON."""
    _login_as(client, "reopenuser@example.com")

    res = client.post(
        "/tasks",
        data={"title": "Tarea a Reabrir"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]
    client.post(
        f"/tasks/{task_id}/status",
        data={"status": "completed"},
        headers={"Accept": "application/json"},
    )

    resp = client.post(
        f"/tasks/{task_id}/reopen", headers={"Accept": "application/json"}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["data"]["status"] == "pending"
    assert data["data"]["previous_status"] == "completed"


def test_reopen_task_not_found_or_other_user(client):
    """Verifica 404 para tarea inexistente o de otro usuario."""
    _login_as(client, "reopenowner@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea Privada Reabrir"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]
    client.post(
        f"/tasks/{task_id}/status",
        data={"status": "completed"},
        headers={"Accept": "application/json"},
    )

    resp = client.post(
        "/tasks/999999/reopen", headers={"Accept": "application/json"}
    )
    assert resp.status_code == 404

    _login_as(client, "reopenintruder@example.com")
    resp_other = client.post(
        f"/tasks/{task_id}/reopen", headers={"Accept": "application/json"}
    )
    assert resp_other.status_code == 404


def test_cannot_reopen_pending_task_route(client):
    """Verifica 400 al intentar reabrir una tarea que no está completada."""
    _login_as(client, "reopenpendinguser@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea Pendiente Reabrir"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(
        f"/tasks/{task_id}/reopen", headers={"Accept": "application/json"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_STATE_FOR_REOPEN"


# --- US1 (Incremento 3): Prioridad de Tareas y Ordenamiento (HU-07) ---

def test_create_task_accepts_explicit_priority(client):
    """Verifica que POST /tasks acepte priority opcional en la creación."""
    _login_as(client, "priorityonCreate@example.com")
    resp = client.post(
        "/tasks",
        data={"title": "Tarea con Prioridad", "priority": "high"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["data"]["priority"] == "high"


def test_update_task_priority_route_success(client):
    """Verifica cambio de prioridad exitoso vía JSON."""
    _login_as(client, "priorityuser@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea Base"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(
        f"/tasks/{task_id}/priority",
        data={"priority": "low"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["priority"] == "low"


def test_update_task_priority_invalid_value_route(client):
    """Verifica 400 Bad Request ante un valor de prioridad inválido."""
    _login_as(client, "priorityinvaliduser@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(
        f"/tasks/{task_id}/priority",
        data={"priority": "urgente"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400


def test_update_task_priority_unauthenticated_fails(client):
    """Verifica 401 Unauthorized sin sesión activa."""
    resp = client.post(
        "/tasks/1/priority",
        data={"priority": "high"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 401


def test_update_task_priority_other_user_task_404(client):
    """Verifica 404 al intentar cambiar la prioridad de una tarea de otro usuario."""
    _login_as(client, "priorityowner@example.com")
    res = client.post(
        "/tasks",
        data={"title": "Tarea Privada"},
        headers={"Accept": "application/json"},
    )
    task_id = res.get_json()["data"]["id"]

    _login_as(client, "priorityintruder@example.com")
    resp = client.post(
        f"/tasks/{task_id}/priority",
        data={"priority": "high"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 404


def test_list_tasks_sorted_by_priority_desc(client):
    """Verifica que GET /tasks?sort=priority_desc retorne la lista ordenada por prioridad."""
    _login_as(client, "sortuser@example.com")
    client.post(
        "/tasks", data={"title": "Baja", "priority": "low"},
        headers={"Accept": "application/json"},
    )
    client.post(
        "/tasks", data={"title": "Alta", "priority": "high"},
        headers={"Accept": "application/json"},
    )

    resp = client.get("/tasks?sort=priority_desc", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.get_json()["data"]["tasks"]]
    assert titles == ["Alta", "Baja"]


# --- US3 (Incremento 3): Indicación Confiable de Tareas Vencidas (HU-09) ---

def test_list_tasks_exposes_is_overdue(client):
    """Verifica que GET /tasks expone is_overdue correctamente para tareas vencidas y no vencidas."""
    _login_as(client, "overdueuser@example.com")

    client.post(
        "/tasks",
        data={"title": "Vencida", "due_date": "2020-01-01"},
        headers={"Accept": "application/json"},
    )
    client.post(
        "/tasks",
        data={"title": "Futura", "due_date": "2099-01-01"},
        headers={"Accept": "application/json"},
    )

    resp = client.get("/tasks", headers={"Accept": "application/json"})
    tasks = {t["title"]: t["is_overdue"] for t in resp.get_json()["data"]["tasks"]}
    assert tasks["Vencida"] is True
    assert tasks["Futura"] is False


# --- US1 (Incremento 4): Asignación Segura de Tareas entre Usuarios (HU-10) ---

def test_assign_task_success(client):
    """Verifica asignación exitosa vía JSON."""
    _login_as(client, "assignowner@example.com")
    res = client.post(
        "/tasks", data={"title": "Tarea a Asignar"}, headers={"Accept": "application/json"}
    )
    task_id = res.get_json()["data"]["id"]

    _login_as(client, "assignreceiver@example.com")
    _login_as(client, "assignowner@example.com")  # vuelve a loguearse como creador

    resp = client.post(
        f"/tasks/{task_id}/assign",
        data={"assigned_to_email": "assignreceiver@example.com"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["assigned_to"]["email"] == "assignreceiver@example.com"


def test_assign_task_nonexistent_email_404(client):
    """Verifica 404 ASSIGNEE_NOT_FOUND al asignar a un correo no registrado."""
    _login_as(client, "assignowner2@example.com")
    res = client.post(
        "/tasks", data={"title": "Tarea"}, headers={"Accept": "application/json"}
    )
    task_id = res.get_json()["data"]["id"]

    resp = client.post(
        f"/tasks/{task_id}/assign",
        data={"assigned_to_email": "fantasma@example.com"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "ASSIGNEE_NOT_FOUND"


def test_assign_task_other_users_task_404(client):
    """Verifica 404 al intentar asignar una tarea que no es propia."""
    _login_as(client, "assignrealowner@example.com")
    res = client.post(
        "/tasks", data={"title": "Tarea Ajena"}, headers={"Accept": "application/json"}
    )
    task_id = res.get_json()["data"]["id"]

    _login_as(client, "assignintruder@example.com")
    resp = client.post(
        f"/tasks/{task_id}/assign",
        data={"assigned_to_email": "assignintruder@example.com"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 404


def test_assign_task_unauthenticated_fails(client):
    """Verifica 401 Unauthorized sin sesión activa."""
    resp = client.post(
        "/tasks/1/assign",
        data={"assigned_to_email": "x@example.com"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 401


def test_unassign_task_success(client):
    """Verifica desasignación exitosa vía JSON."""
    _login_as(client, "unassignowner@example.com")
    res = client.post(
        "/tasks", data={"title": "Tarea a Desasignar"}, headers={"Accept": "application/json"}
    )
    task_id = res.get_json()["data"]["id"]
    client.post(
        f"/tasks/{task_id}/assign",
        data={"assigned_to_email": "unassignowner@example.com"},
        headers={"Accept": "application/json"},
    )

    resp = client.post(f"/tasks/{task_id}/unassign", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["assigned_to"] is None


def test_list_tasks_view_filter(client):
    """Verifica que GET /tasks?view=created|assigned filtre correctamente."""
    _login_as(client, "viewowner@example.com")
    client.post("/tasks", data={"title": "Mia"}, headers={"Accept": "application/json"})

    resp_created = client.get("/tasks?view=created", headers={"Accept": "application/json"})
    assert resp_created.status_code == 200
    assert resp_created.get_json()["data"]["count"] == 1

    resp_assigned = client.get("/tasks?view=assigned", headers={"Accept": "application/json"})
    assert resp_assigned.get_json()["data"]["count"] == 0


def test_assignee_can_change_status_via_route(client):
    """Verifica que el asignatario pueda cambiar el estado vía HTTP (hallazgo E1)."""
    _login_as(client, "statusassignee@example.com")  # pre-registra al asignatario
    _login_as(client, "statusowner@example.com")
    res = client.post(
        "/tasks", data={"title": "Tarea Delegada HTTP"}, headers={"Accept": "application/json"}
    )
    task_id = res.get_json()["data"]["id"]
    assign_resp = client.post(
        f"/tasks/{task_id}/assign",
        data={"assigned_to_email": "statusassignee@example.com"},
        headers={"Accept": "application/json"},
    )
    assert assign_resp.status_code == 200

    _login_as(client, "statusassignee@example.com")
    resp = client.post(
        f"/tasks/{task_id}/status",
        data={"status": "completed"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200


# --- US2 (Incremento 5): Reordenar Tareas Arrastrándolas (HU-16) ---

def test_reorder_tasks_success(client):
    """Verifica reordenamiento exitoso vía JSON."""
    _login_as(client, "reorderuser@example.com")
    ids = []
    for title in ["Tarea A", "Tarea B", "Tarea C"]:
        res = client.post("/tasks", data={"title": title}, headers={"Accept": "application/json"})
        ids.append(res.get_json()["data"]["id"])

    resp = client.post(
        "/tasks/reorder",
        json={"task_ids": [ids[2], ids[0], ids[1]]},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["updated_count"] == 3

    listing = client.get("/tasks?sort=manual", headers={"Accept": "application/json"})
    ordered_ids = [t["id"] for t in listing.get_json()["data"]["tasks"]]
    assert ordered_ids == [ids[2], ids[0], ids[1]]


def test_reorder_tasks_empty_payload_rejected(client):
    """Verifica 400 VALIDATION_ERROR con un payload vacío o malformado."""
    _login_as(client, "reorderempty@example.com")
    resp = client.post(
        "/tasks/reorder", json={"task_ids": []}, headers={"Accept": "application/json"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "VALIDATION_ERROR"


def test_reorder_tasks_foreign_task_rejected_atomically(client):
    """Verifica 404 y que ninguna tarea del lote cambie si alguna no pertenece al usuario."""
    _login_as(client, "reorderowner@example.com")
    res = client.post("/tasks", data={"title": "Propia"}, headers={"Accept": "application/json"})
    own_id = res.get_json()["data"]["id"]

    _login_as(client, "reorderintruder@example.com")
    res2 = client.post("/tasks", data={"title": "Ajena"}, headers={"Accept": "application/json"})
    foreign_id = res2.get_json()["data"]["id"]

    _login_as(client, "reorderowner@example.com")
    resp = client.post(
        "/tasks/reorder",
        json={"task_ids": [own_id, foreign_id]},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "TASK_NOT_FOUND"


def test_reorder_tasks_unauthenticated_fails(client):
    """Verifica 401 Unauthorized sin sesión activa."""
    resp = client.post(
        "/tasks/reorder", json={"task_ids": [1]}, headers={"Accept": "application/json"}
    )
    assert resp.status_code == 401
