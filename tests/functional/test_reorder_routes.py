JSON = {"Accept": "application/json"}


def _registrar_y_entrar(client, email, password="Password123!"):
    client.post("/auth/register", data={"email": email, "password": password}, headers=JSON)
    client.post("/auth/login", data={"email": email, "password": password}, headers=JSON)


def _crear(client, titulo):
    return client.post("/tasks", data={"title": titulo}, headers=JSON).get_json()["data"]["id"]


def test_reorder_endpoint_requires_session(client):
    """Sin sesión activa no se puede reordenar (Principio VII)."""
    res = client.post("/tasks/reorder", json={"task_ids": [1, 2]}, headers=JSON)
    assert res.status_code == 401


def test_reorder_endpoint_success(client):
    """POST /tasks/reorder persiste el nuevo orden según contrato."""
    _registrar_y_entrar(client, "ordr-a@example.com")
    a = _crear(client, "Primera")
    b = _crear(client, "Segunda")
    c = _crear(client, "Tercera")

    res = client.post("/tasks/reorder", json={"task_ids": [c, a, b]}, headers=JSON)
    assert res.status_code == 200
    assert res.get_json()["data"]["reordered_count"] == 3

    titulos = [t["title"] for t in client.get("/tasks", headers=JSON).get_json()["data"]["tasks"]]
    assert titulos == ["Tercera", "Primera", "Segunda"]


def test_list_tasks_respects_personal_order(client):
    """El orden personal sobrevive a consultas sucesivas (FR-008, SC-003)."""
    _registrar_y_entrar(client, "ordr-b@example.com")
    a = _crear(client, "Alfa")
    b = _crear(client, "Beta")
    client.post("/tasks/reorder", json={"task_ids": [a, b]}, headers=JSON)

    for _ in range(2):
        titulos = [t["title"] for t in client.get("/tasks", headers=JSON).get_json()["data"]["tasks"]]
        assert titulos == ["Alfa", "Beta"]


def test_reorder_endpoint_invalid_payload_returns_400(client):
    """Un payload mal formado responde 400 con el código del contrato."""
    _registrar_y_entrar(client, "ordr-c@example.com")

    sin_campo = client.post("/tasks/reorder", json={}, headers=JSON)
    assert sin_campo.status_code == 400
    assert sin_campo.get_json()["code"] == "INVALID_TASK_ORDER"

    no_es_lista = client.post("/tasks/reorder", json={"task_ids": "1,2"}, headers=JSON)
    assert no_es_lista.status_code == 400

    valores_no_numericos = client.post(
        "/tasks/reorder", json={"task_ids": ["abc"]}, headers=JSON
    )
    assert valores_no_numericos.status_code == 400


def test_reorder_endpoint_reports_ignored_ids(client):
    """Los identificadores ajenos se informan y no alteran nada (FR-010, SC-004)."""
    _registrar_y_entrar(client, "ordr-d@example.com")
    ajena = _crear(client, "De otro usuario")

    _registrar_y_entrar(client, "ordr-e@example.com")
    propia = _crear(client, "Propia")

    res = client.post("/tasks/reorder", json={"task_ids": [ajena, propia]}, headers=JSON)
    assert res.status_code == 200

    datos = res.get_json()["data"]
    assert datos["reordered_count"] == 1
    assert ajena in datos["ignored_ids"]

    # La tarea ajena sigue visible e intacta para su dueño
    _registrar_y_entrar(client, "ordr-d@example.com")
    suyas = client.get("/tasks", headers=JSON).get_json()["data"]["tasks"]
    assert [t["title"] for t in suyas] == ["De otro usuario"]
    assert suyas[0]["position"] == 0


def test_status_endpoint_returns_json_for_fetch(client):
    """El endpoint de estado responde JSON: es el contrato del que depende el fetch (FR-002)."""
    _registrar_y_entrar(client, "ordr-f@example.com")
    task_id = _crear(client, "Completar sin recargar")

    res = client.post(
        f"/tasks/{task_id}/status", json={"status": "completed"}, headers=JSON
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"


def test_status_endpoint_invalid_transition_returns_error_for_fetch(client):
    """Una transición inválida devuelve un código de error para que el cliente revierta (FR-003)."""
    _registrar_y_entrar(client, "ordr-g@example.com")
    task_id = _crear(client, "Transición imposible")
    client.post(f"/tasks/{task_id}/status", json={"status": "completed"}, headers=JSON)

    # De completada no se puede volver a pendiente sin la reapertura explícita
    res = client.post(
        f"/tasks/{task_id}/status", json={"status": "pending"}, headers=JSON
    )
    assert res.status_code >= 400
