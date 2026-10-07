import pytest
from src.taskcontrol.extensions import db
from src.taskcontrol.models.audit import AuditLog
from src.taskcontrol.models.task import Task
from src.taskcontrol.services.category_service import (
    CategoryService,
    CategoryValidationError,
    DuplicateCategoryNameError,
    CategoryNotFoundError,
)
from src.taskcontrol.services.task_service import TaskService, TaskNotFoundError
from src.taskcontrol.services.user_service import UserService


def _usuario(email):
    return UserService.register_user(email, "Password123!")


# ---------------------------------------------------------------------------
# HU-08: Creación y unicidad
# ---------------------------------------------------------------------------


def test_create_category_success(app):
    """Una categoría se crea con nombre, color y descripción, y queda auditada."""
    with app.app_context():
        user = _usuario("cat1@example.com")
        categoria = CategoryService.create_category(
            user_id=user.id, name="Universidad", description="Entregas", color="#10B981"
        )

        assert categoria.id is not None
        assert categoria.name == "Universidad"
        assert categoria.color == "#10B981"
        assert categoria.user_id == user.id

        auditoria = AuditLog.query.filter_by(action=AuditLog.ACTION_CATEGORY_CREATED).all()
        assert len(auditoria) == 1
        assert auditoria[0].entity_id == categoria.id


def test_create_category_rejects_empty_or_too_long_name(app):
    """El nombre es obligatorio y no puede exceder 50 caracteres (FR-005)."""
    with app.app_context():
        user = _usuario("cat2@example.com")

        with pytest.raises(CategoryValidationError):
            CategoryService.create_category(user_id=user.id, name="   ")

        with pytest.raises(CategoryValidationError):
            CategoryService.create_category(user_id=user.id, name="X" * 51)


def test_create_category_rejects_duplicate_name_for_same_user(app):
    """Un usuario no puede tener dos categorías con el mismo nombre (FR-006)."""
    with app.app_context():
        user = _usuario("cat3@example.com")
        CategoryService.create_category(user_id=user.id, name="Trabajo")

        with pytest.raises(DuplicateCategoryNameError):
            CategoryService.create_category(user_id=user.id, name="Trabajo")


def test_create_category_rejects_duplicate_name_ignoring_case(app):
    """La unicidad ignora mayúsculas y minúsculas.

    La UniqueConstraint de SQLite distingue mayúsculas, así que "Trabajo" y "trabajo"
    convivirían sin una verificación explícita en el servicio (spec.md → Edge Cases).
    """
    with app.app_context():
        user = _usuario("cat4@example.com")
        CategoryService.create_category(user_id=user.id, name="Trabajo")

        with pytest.raises(DuplicateCategoryNameError):
            CategoryService.create_category(user_id=user.id, name="trabajo")

        with pytest.raises(DuplicateCategoryNameError):
            CategoryService.create_category(user_id=user.id, name="  TRABAJO  ")


def test_different_users_can_share_category_name(app):
    """Dos usuarios distintos sí pueden tener categorías con el mismo nombre (FR-006)."""
    with app.app_context():
        uno = _usuario("cat5a@example.com")
        dos = _usuario("cat5b@example.com")

        primera = CategoryService.create_category(user_id=uno.id, name="Personal")
        segunda = CategoryService.create_category(user_id=dos.id, name="Personal")

        assert primera.id != segunda.id
        assert len(CategoryService.get_user_categories(uno.id)) == 1
        assert len(CategoryService.get_user_categories(dos.id)) == 1


# ---------------------------------------------------------------------------
# HU-08: Listado, edición y eliminación
# ---------------------------------------------------------------------------


def test_get_user_categories_includes_active_task_count(app):
    """El listado informa cuántas tareas activas tiene cada categoría."""
    with app.app_context():
        user = _usuario("cat6@example.com")
        categoria = CategoryService.create_category(user_id=user.id, name="Proyecto")

        for titulo in ("Uno", "Dos"):
            tarea = TaskService.create_task(user_id=user.id, title=titulo)
            TaskService.assign_category_to_task(
                task_id=tarea.id, user_id=user.id, category_id=categoria.id
            )

        eliminada = TaskService.create_task(user_id=user.id, title="Tres")
        TaskService.assign_category_to_task(
            task_id=eliminada.id, user_id=user.id, category_id=categoria.id
        )
        TaskService.delete_task(task_id=eliminada.id, user_id=user.id)

        listado = CategoryService.get_user_categories(user.id)
        assert listado[0]["task_count"] == 2  # la eliminada no cuenta


def test_update_category_success(app):
    """Editar una categoría cambia sus datos y lo registra en auditoría (FR-007)."""
    with app.app_context():
        user = _usuario("cat7@example.com")
        categoria = CategoryService.create_category(user_id=user.id, name="Viejo")

        actualizada = CategoryService.update_category(
            category_id=categoria.id, user_id=user.id, name="Nuevo", color="#FF0000"
        )

        assert actualizada.name == "Nuevo"
        assert actualizada.color == "#FF0000"
        assert AuditLog.query.filter_by(action=AuditLog.ACTION_CATEGORY_UPDATED).count() == 1


def test_cannot_update_category_of_another_user(app):
    """Nadie puede editar categorías ajenas (Principio VII)."""
    with app.app_context():
        dueno = _usuario("cat8a@example.com")
        intruso = _usuario("cat8b@example.com")
        categoria = CategoryService.create_category(user_id=dueno.id, name="Privada")

        with pytest.raises(CategoryNotFoundError):
            CategoryService.update_category(
                category_id=categoria.id, user_id=intruso.id, name="Secuestrada"
            )


def test_delete_category_unlinks_tasks_without_deleting_them(app):
    """Eliminar una categoría NUNCA borra sus tareas: las desvincula (FR-009, SC-003)."""
    with app.app_context():
        user = _usuario("cat9@example.com")
        categoria = CategoryService.create_category(user_id=user.id, name="Temporal")

        tareas = []
        for titulo in ("Primera", "Segunda", "Tercera"):
            tarea = TaskService.create_task(user_id=user.id, title=titulo)
            TaskService.assign_category_to_task(
                task_id=tarea.id, user_id=user.id, category_id=categoria.id
            )
            tareas.append(tarea.id)

        resultado = CategoryService.delete_category(category_id=categoria.id, user_id=user.id)
        assert resultado["tasks_unlinked_count"] == 3

        # Las tres tareas siguen existiendo, solo que sin categoría
        for task_id in tareas:
            tarea = db.session.get(Task, task_id)
            assert tarea is not None, "Eliminar la categoría no debe borrar la tarea"
            assert tarea.is_deleted is False
            assert tarea.category_id is None

        assert len(CategoryService.get_user_categories(user.id)) == 0


def test_cannot_delete_category_of_another_user(app):
    """Nadie puede eliminar categorías ajenas (Principio VII)."""
    with app.app_context():
        dueno = _usuario("cat10a@example.com")
        intruso = _usuario("cat10b@example.com")
        categoria = CategoryService.create_category(user_id=dueno.id, name="Ajena")

        with pytest.raises(CategoryNotFoundError):
            CategoryService.delete_category(category_id=categoria.id, user_id=intruso.id)


# ---------------------------------------------------------------------------
# HU-08: Asignación de categoría a tareas
# ---------------------------------------------------------------------------


def test_assign_category_to_task(app):
    """Una tarea puede asociarse a una categoría propia y desvincularse con None (FR-008)."""
    with app.app_context():
        user = _usuario("cat11@example.com")
        categoria = CategoryService.create_category(user_id=user.id, name="Casa")
        tarea = TaskService.create_task(user_id=user.id, title="Regar las plantas")

        TaskService.assign_category_to_task(
            task_id=tarea.id, user_id=user.id, category_id=categoria.id
        )
        assert tarea.category_id == categoria.id

        TaskService.assign_category_to_task(
            task_id=tarea.id, user_id=user.id, category_id=None
        )
        assert tarea.category_id is None


def test_cannot_assign_category_of_another_user(app):
    """No se puede asociar una tarea propia a una categoría ajena (FR-010, prevención de IDOR)."""
    with app.app_context():
        dueno = _usuario("cat12a@example.com")
        otro = _usuario("cat12b@example.com")
        categoria_ajena = CategoryService.create_category(user_id=otro.id, name="De otro")
        tarea = TaskService.create_task(user_id=dueno.id, title="Mi tarea")

        with pytest.raises(CategoryNotFoundError):
            TaskService.assign_category_to_task(
                task_id=tarea.id, user_id=dueno.id, category_id=categoria_ajena.id
            )

        assert tarea.category_id is None


def test_cannot_assign_category_to_deleted_task(app):
    """Una tarea eliminada no admite cambios de categoría."""
    with app.app_context():
        user = _usuario("cat13@example.com")
        categoria = CategoryService.create_category(user_id=user.id, name="Alguna")
        tarea = TaskService.create_task(user_id=user.id, title="Será borrada")
        TaskService.delete_task(task_id=tarea.id, user_id=user.id)

        with pytest.raises(TaskNotFoundError):
            TaskService.assign_category_to_task(
                task_id=tarea.id, user_id=user.id, category_id=categoria.id
            )
