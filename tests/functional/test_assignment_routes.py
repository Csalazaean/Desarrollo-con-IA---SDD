JSON = {"Accept": "application/json"}


def _registrar_y_entrar(client, email, password="Password123!"):
    client.post("/auth/register", data={"email": email, "password": password}, headers=JSON)
    client.post("/auth/login", data={"email": email, "password": password}, headers=JSON)


def _registrar(client, email, password="Password123!"):
    client.post("/auth/register", data={"email": email, "password": password}, headers=JSON)


def _crear_tarea(client, titulo):
    return client.post("/tasks", data={"title": titulo}, headers=JSON).get_json()["data"]["id"]


def test_assign_endpoint_success(client):
    """POST /tasks/<id>/assign vincula la tarea según contrato."""
    _registrar(client, "ruta-b@example.com")
    _registrar_y_entrar(client, "ruta-a@example.com")
    task_id = _crear_tarea(client, "Delegar esto")

    res = client.post(
        f"/tasks/{task_id}/assign",
        data={"assignee_email": "ruta-b@example.com"},
        headers=JSON,
    )
    assert res.status_code == 200
    datos = res.get_json()["data"]
    assert datos["assignee_email"] == "ruta-b@example.com"
    assert datos["notification_created"] is True


def test_assign_endpoint_unregistered_email_returns_400(client):
    """Un correo no registrado responde 400 con el código del contrato (FR-002)."""
    _registrar_y_entrar(client, "ruta-c@example.com")
    task_id = _crear_tarea(client, "Nadie la recibirá")

    res = client.post(
        f"/tasks/{task_id}/assign",
        data={"assignee_email": "fantasma@example.com"},
        headers=JSON,
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == "ASSIGNEE_NOT_FOUND"


def test_assign_endpoint_non_creator_returns_403(client):
    """Un tercero recibe 403, no 404: la tarea existe pero no es suya (Escenario 5)."""
    _registrar(client, "ruta-f@example.com")
    _registrar_y_entrar(client, "ruta-d@example.com")
    task_id = _crear_tarea(client, "Tarea del creador")

    _registrar_y_entrar(client, "ruta-e@example.com")
    res = client.post(
        f"/tasks/{task_id}/assign",
        data={"assignee_email": "ruta-f@example.com"},
        headers=JSON,
    )
    assert res.status_code == 403
    assert res.get_json()["code"] == "NOT_TASK_OWNER"


def test_assign_endpoint_nonexistent_task_returns_404(client):
    """Una tarea inexistente responde 404, distinto del 403 por falta de permiso."""
    _registrar_y_entrar(client, "ruta-g@example.com")
    res = client.post(
        "/tasks/99999/assign", data={"assignee_email": "ruta-g@example.com"}, headers=JSON
    )
    assert res.status_code == 404


def test_assign_endpoint_requires_session(client):
    """Sin sesión activa no se puede asignar (Principio VII)."""
    res = client.post(
        "/tasks/1/assign", data={"assignee_email": "x@example.com"}, headers=JSON
    )
    assert res.status_code == 401


def test_unassign_via_empty_email(client):
    """Enviar el correo vacío retira la asignación (FR-003)."""
    _registrar(client, "ruta-i@example.com")
    _registrar_y_entrar(client, "ruta-h@example.com")
    task_id = _crear_tarea(client, "Se desasignará")
    client.post(
        f"/tasks/{task_id}/assign", data={"assignee_email": "ruta-i@example.com"}, headers=JSON
    )

    res = client.post(f"/tasks/{task_id}/assign", data={"assignee_email": ""}, headers=JSON)
    assert res.status_code == 200
    assert res.get_json()["data"]["assigned_to_id"] is None


def test_list_tasks_scope_created_assigned_and_all(client):
    """El parámetro scope separa creadas, asignadas y todas (FR-006)."""
    _registrar(client, "ruta-k@example.com")
    _registrar_y_entrar(client, "ruta-j@example.com")
    delegada = _crear_tarea(client, "Delegada a K")
    client.post(
        f"/tasks/{delegada}/assign", data={"assignee_email": "ruta-k@example.com"}, headers=JSON
    )

    _registrar_y_entrar(client, "ruta-k@example.com")
    _crear_tarea(client, "Propia de K")

    def titulos(scope):
        url = "/tasks" if scope is None else f"/tasks?scope={scope}"
        return {t["title"] for t in client.get(url, headers=JSON).get_json()["data"]["tasks"]}

    assert titulos(None) == {"Delegada a K", "Propia de K"}
    assert titulos("all") == {"Delegada a K", "Propia de K"}
    assert titulos("created") == {"Propia de K"}
    assert titulos("assigned") == {"Delegada a K"}


def test_list_tasks_marks_authorship_for_viewer(client):
    """El backend resuelve is_mine / is_assigned_to_me respecto de quien consulta (FR-005)."""
    _registrar(client, "ruta-m@example.com")
    _registrar_y_entrar(client, "ruta-l@example.com")
    delegada = _crear_tarea(client, "Para M")
    client.post(
        f"/tasks/{delegada}/assign", data={"assignee_email": "ruta-m@example.com"}, headers=JSON
    )

    _registrar_y_entrar(client, "ruta-m@example.com")
    tarea = client.get("/tasks", headers=JSON).get_json()["data"]["tasks"][0]

    assert tarea["is_mine"] is False
    assert tarea["is_assigned_to_me"] is True
    assert tarea["creator_email"] == "ruta-l@example.com"
