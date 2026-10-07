def _login_as(client, email="catuser@example.com", password="Password123!"):
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


# --- US2 (Incremento 3): Agrupación por Categorías o Proyectos (HU-08) ---

def test_list_categories_unauthenticated_fails(client):
    """Verifica 401 Unauthorized sin sesión activa."""
    response = client.get("/categories", headers={"Accept": "application/json"})
    assert response.status_code == 401


def test_create_and_list_categories(client):
    """Verifica creación exitosa y que aparezca en el listado con task_count."""
    _login_as(client, "catlistuser@example.com")

    resp = client.post(
        "/categories",
        data={"name": "Trabajo", "description": "Oficina", "color": "#2563EB"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["data"]["name"] == "Trabajo"

    listing = client.get("/categories", headers={"Accept": "application/json"})
    assert listing.status_code == 200
    categories = listing.get_json()["data"]["categories"]
    assert len(categories) == 1
    assert categories[0]["task_count"] == 0


def test_create_category_duplicate_name_fails(client):
    """Verifica 400 DUPLICATE_CATEGORY_NAME al repetir nombre."""
    _login_as(client, "catdupuser@example.com")
    client.post(
        "/categories", data={"name": "Universidad"}, headers={"Accept": "application/json"}
    )
    resp = client.post(
        "/categories", data={"name": "Universidad"}, headers={"Accept": "application/json"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "DUPLICATE_CATEGORY_NAME"


def test_create_category_invalid_color_fails(client):
    """Verifica 400 INVALID_CATEGORY_COLOR con un color mal formado."""
    _login_as(client, "catcoloruser@example.com")
    resp = client.post(
        "/categories",
        data={"name": "ColorMalo", "color": "noesunColor"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_CATEGORY_COLOR"


def test_edit_category_success(client):
    """Verifica edición exitosa de una categoría propia."""
    _login_as(client, "cateditsuccess@example.com")
    res = client.post(
        "/categories", data={"name": "Original"}, headers={"Accept": "application/json"}
    )
    category_id = res.get_json()["data"]["id"]

    resp = client.post(
        f"/categories/{category_id}/edit",
        data={"name": "Editada", "color": "#10B981"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "Editada"


def test_edit_category_not_found_or_other_user(client):
    """Verifica 404 al editar una categoría inexistente o de otro usuario."""
    _login_as(client, "cateditowner@example.com")
    res = client.post(
        "/categories", data={"name": "De Owner"}, headers={"Accept": "application/json"}
    )
    category_id = res.get_json()["data"]["id"]

    _login_as(client, "cateditintruder@example.com")
    resp = client.post(
        f"/categories/{category_id}/edit",
        data={"name": "Hackeada"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 404


def test_delete_category_unlinks_tasks(client):
    """Verifica que eliminar una categoría desvincule las tareas sin borrarlas (HTTP end-to-end)."""
    _login_as(client, "catdeleteuser@example.com")
    cat_res = client.post(
        "/categories", data={"name": "Para Borrar"}, headers={"Accept": "application/json"}
    )
    category_id = cat_res.get_json()["data"]["id"]

    task_res = client.post(
        "/tasks", data={"title": "Tarea Asociada"}, headers={"Accept": "application/json"}
    )
    task_id = task_res.get_json()["data"]["id"]

    client.post(
        f"/tasks/{task_id}/category",
        data={"category_id": category_id},
        headers={"Accept": "application/json"},
    )

    del_resp = client.post(
        f"/categories/{category_id}/delete", headers={"Accept": "application/json"}
    )
    assert del_resp.status_code == 200

    task_check = client.get("/tasks", headers={"Accept": "application/json"})
    tasks = task_check.get_json()["data"]["tasks"]
    found = next(t for t in tasks if t["id"] == task_id)
    assert found["category"] is None


def test_delete_category_not_found_or_other_user(client):
    """Verifica 404 al eliminar una categoría inexistente o ajena."""
    _login_as(client, "catdelowner@example.com")
    resp = client.post(
        "/categories/999999/delete", headers={"Accept": "application/json"}
    )
    assert resp.status_code == 404


def test_assign_category_to_task_success(client):
    """Verifica asignación exitosa de categoría a una tarea vía HTTP."""
    _login_as(client, "catassignuser@example.com")
    cat_res = client.post(
        "/categories", data={"name": "Asignable"}, headers={"Accept": "application/json"}
    )
    category_id = cat_res.get_json()["data"]["id"]

    task_res = client.post(
        "/tasks", data={"title": "Tarea a Categorizar"}, headers={"Accept": "application/json"}
    )
    task_id = task_res.get_json()["data"]["id"]

    resp = client.post(
        f"/tasks/{task_id}/category",
        data={"category_id": category_id},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200


def test_assign_category_not_owned_fails(client):
    """Verifica 404 al intentar asignar una categoría que no pertenece al usuario."""
    _login_as(client, "catassignowner@example.com")
    cat_res = client.post(
        "/categories", data={"name": "De Otro"}, headers={"Accept": "application/json"}
    )
    category_id = cat_res.get_json()["data"]["id"]

    _login_as(client, "catassignintruder@example.com")
    task_res = client.post(
        "/tasks", data={"title": "Tarea Intrusa"}, headers={"Accept": "application/json"}
    )
    task_id = task_res.get_json()["data"]["id"]

    resp = client.post(
        f"/tasks/{task_id}/category",
        data={"category_id": category_id},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 404
