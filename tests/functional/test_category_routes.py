from src.taskcontrol.models.task import Task


def _login_as(client, email="caturoute@example.com", password="Password123!"):
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


def _crear_categoria(client, name, color=None):
    res = client.post(
        "/categories",
        data={"name": name, "color": color or ""},
        headers={"Accept": "application/json"},
    )
    return res.get_json()["data"]["id"]


def test_category_endpoints_require_session(client):
    """Todos los endpoints de categoría exigen sesión activa (Principio VII)."""
    assert client.get("/categories", headers={"Accept": "application/json"}).status_code == 401
    assert client.post(
        "/categories", data={"name": "X"}, headers={"Accept": "application/json"}
    ).status_code == 401
    assert client.post(
        "/categories/1/delete", headers={"Accept": "application/json"}
    ).status_code == 401


def test_create_category_endpoint_success(client):
    """POST /categories crea la categoría y responde 201 según contrato."""
    _login_as(client, "catcreate@example.com")
    res = client.post(
        "/categories",
        data={"name": "Universidad", "description": "Entregas", "color": "#10B981"},
        headers={"Accept": "application/json"},
    )
    assert res.status_code == 201
    datos = res.get_json()
    assert datos["status"] == "success"
    assert datos["data"]["name"] == "Universidad"
    assert datos["data"]["color"] == "#10B981"


def test_create_category_duplicate_returns_400(client):
    """Un nombre repetido responde 400 con el código del contrato."""
    _login_as(client, "catdupe@example.com")
    _crear_categoria(client, "Trabajo")

    res = client.post(
        "/categories", data={"name": "Trabajo"}, headers={"Accept": "application/json"}
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == "DUPLICATE_CATEGORY_NAME"


def test_create_category_empty_name_returns_400(client):
    """Un nombre vacío responde 400."""
    _login_as(client, "catempty@example.com")
    res = client.post(
        "/categories", data={"name": "   "}, headers={"Accept": "application/json"}
    )
    assert res.status_code == 400


def test_list_categories_authenticated(client):
    """GET /categories lista las categorías del usuario con su conteo de tareas."""
    _login_as(client, "catlist@example.com")
    categoria_id = _crear_categoria(client, "Casa")

    tarea = client.post(
        "/tasks", data={"title": "Barrer"}, headers={"Accept": "application/json"}
    ).get_json()["data"]["id"]
    client.post(
        f"/tasks/{tarea}/category",
        data={"category_id": categoria_id},
        headers={"Accept": "application/json"},
    )

    res = client.get("/categories", headers={"Accept": "application/json"})
    assert res.status_code == 200
    categorias = res.get_json()["data"]["categories"]
    assert len(categorias) == 1
    assert categorias[0]["name"] == "Casa"
    assert categorias[0]["task_count"] == 1


def test_update_category_endpoint_success(client):
    """POST /categories/<id>/edit actualiza nombre y color (FR-007)."""
    _login_as(client, "catedit@example.com")
    categoria_id = _crear_categoria(client, "Antiguo")

    res = client.post(
        f"/categories/{categoria_id}/edit",
        data={"name": "Renombrado", "color": "#FF0000"},
        headers={"Accept": "application/json"},
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["name"] == "Renombrado"


def test_delete_category_endpoint_unlinks_tasks(client):
    """Eliminar la categoría desvincula sus tareas sin borrarlas (FR-009, SC-003)."""
    _login_as(client, "catdel@example.com")
    categoria_id = _crear_categoria(client, "Temporal")

    tarea_id = client.post(
        "/tasks", data={"title": "Sobrevive al borrado"}, headers={"Accept": "application/json"}
    ).get_json()["data"]["id"]
    client.post(
        f"/tasks/{tarea_id}/category",
        data={"category_id": categoria_id},
        headers={"Accept": "application/json"},
    )

    res = client.post(
        f"/categories/{categoria_id}/delete", headers={"Accept": "application/json"}
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["tasks_unlinked_count"] == 1

    # La tarea sigue existiendo y visible, ahora sin categoría
    tareas = client.get("/tasks", headers={"Accept": "application/json"}).get_json()["data"]["tasks"]
    assert len(tareas) == 1
    assert tareas[0]["title"] == "Sobrevive al borrado"
    assert tareas[0]["category"] is None


def test_delete_category_of_another_user_returns_404(client):
    """No se puede borrar una categoría ajena (Principio VII)."""
    _login_as(client, "catowner@example.com")
    categoria_id = _crear_categoria(client, "Privada")

    _login_as(client, "catintruder@example.com")
    res = client.post(
        f"/categories/{categoria_id}/delete", headers={"Accept": "application/json"}
    )
    assert res.status_code == 404
