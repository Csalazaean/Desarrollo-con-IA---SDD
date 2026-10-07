import pytest
from src.taskcontrol.services.user_service import UserService
from src.taskcontrol.services.task_service import TaskService, TaskNotFoundError
from src.taskcontrol.services.category_service import (
    CategoryService,
    DuplicateCategoryNameError,
    CategoryNotFoundError,
    InvalidCategoryColorError,
)
from src.taskcontrol.models.audit import AuditLog


@pytest.fixture
def test_user_id(app):
    with app.app_context():
        user = UserService.register_user("categoryowner@example.com", "Password123!")
        return user.id


@pytest.fixture
def second_user_id(app):
    with app.app_context():
        user = UserService.register_user("categoryintruder@example.com", "Password123!")
        return user.id


# --- US2 (Incremento 3): Agrupación por Categorías o Proyectos (HU-08) ---

def test_create_category_success(app, test_user_id):
    """Verifica creación exitosa de categoría y su registro de auditoría CATEGORY_CREATED."""
    with app.app_context():
        category = CategoryService.create_category(
            user_id=test_user_id, name="Trabajo", description="Proyectos", color="#2563EB"
        )
        assert category.id is not None
        assert category.name == "Trabajo"

        audit = AuditLog.query.filter_by(action="CATEGORY_CREATED", entity_id=category.id).first()
        assert audit is not None
        assert audit.actor_id == test_user_id


def test_create_category_unique_name_per_user(app, test_user_id):
    """Verifica que un usuario no pueda tener dos categorías con el mismo nombre (case-insensitive)."""
    with app.app_context():
        CategoryService.create_category(user_id=test_user_id, name="Trabajo")
        with pytest.raises(DuplicateCategoryNameError):
            CategoryService.create_category(user_id=test_user_id, name="trabajo")


def test_different_users_can_have_same_category_name(app, test_user_id, second_user_id):
    """Verifica que dos usuarios distintos puedan compartir el nombre de categoría sin colisión."""
    with app.app_context():
        c1 = CategoryService.create_category(user_id=test_user_id, name="Personal")
        c2 = CategoryService.create_category(user_id=second_user_id, name="Personal")
        assert c1.id != c2.id


def test_create_category_invalid_color_format_rejected(app, test_user_id):
    """Verifica que un color fuera del formato #RRGGBB sea rechazado (clarify Q3)."""
    with app.app_context():
        with pytest.raises(InvalidCategoryColorError):
            CategoryService.create_category(user_id=test_user_id, name="Azul", color="azul")


def test_update_category_success(app, test_user_id):
    """Verifica edición de categoría propia y su registro de auditoría CATEGORY_UPDATED."""
    with app.app_context():
        category = CategoryService.create_category(user_id=test_user_id, name="Original")
        updated = CategoryService.update_category(
            category_id=category.id,
            user_id=test_user_id,
            name="Renombrada",
            description="Nueva descripción",
            color="#10B981",
        )
        assert updated.name == "Renombrada"
        assert updated.color == "#10B981"

        audit = AuditLog.query.filter_by(action="CATEGORY_UPDATED", entity_id=category.id).first()
        assert audit is not None


def test_update_category_duplicate_name_rejected(app, test_user_id):
    """Verifica que editar una categoría a un nombre ya usado por otra propia sea rechazado."""
    with app.app_context():
        CategoryService.create_category(user_id=test_user_id, name="Trabajo")
        otra = CategoryService.create_category(user_id=test_user_id, name="Personal")
        with pytest.raises(DuplicateCategoryNameError):
            CategoryService.update_category(
                category_id=otra.id, user_id=test_user_id, name="Trabajo"
            )


def test_cannot_update_another_users_category(app, test_user_id, second_user_id):
    """Verifica aislamiento por usuario (Cero IDOR) al editar categorías."""
    with app.app_context():
        category = CategoryService.create_category(user_id=test_user_id, name="Privada")
        with pytest.raises(CategoryNotFoundError):
            CategoryService.update_category(
                category_id=category.id, user_id=second_user_id, name="Hackeada"
            )


def test_delete_category_sets_task_category_id_to_null_and_does_not_delete_tasks(app, test_user_id):
    """Verifica desvinculación SET NULL sin cascada al eliminar una categoría (BLOQUEANTE)."""
    with app.app_context():
        category = CategoryService.create_category(user_id=test_user_id, name="Proyecto X")
        t1 = TaskService.create_task(user_id=test_user_id, title="Tarea 1")
        t2 = TaskService.create_task(user_id=test_user_id, title="Tarea 2")
        t3 = TaskService.create_task(user_id=test_user_id, title="Tarea 3")
        for t in (t1, t2, t3):
            TaskService.assign_category(user_id=test_user_id, task_id=t.id, category_id=category.id)

        CategoryService.delete_category(category_id=category.id, user_id=test_user_id)

        for t in (t1, t2, t3):
            refreshed = TaskService.get_task_by_id(user_id=test_user_id, task_id=t.id)
            assert refreshed.category_id is None

        audit = AuditLog.query.filter_by(action="CATEGORY_DELETED", entity_id=category.id).first()
        assert audit is not None


def test_cannot_assign_task_to_another_users_category(app, test_user_id, second_user_id):
    """Verifica que no se pueda asignar una tarea propia a una categoría de otro usuario."""
    with app.app_context():
        foreign_category = CategoryService.create_category(user_id=second_user_id, name="Ajena")
        task = TaskService.create_task(user_id=test_user_id, title="Tarea propia")
        with pytest.raises(CategoryNotFoundError):
            TaskService.assign_category(
                user_id=test_user_id, task_id=task.id, category_id=foreign_category.id
            )


def test_assign_and_unassign_category_to_task(app, test_user_id):
    """Verifica asignación y desasignación (category_id=None) de categoría a una tarea."""
    with app.app_context():
        category = CategoryService.create_category(user_id=test_user_id, name="Estudio")
        task = TaskService.create_task(user_id=test_user_id, title="Leer capítulo")

        assigned = TaskService.assign_category(
            user_id=test_user_id, task_id=task.id, category_id=category.id
        )
        assert assigned.category_id == category.id

        unassigned = TaskService.assign_category(
            user_id=test_user_id, task_id=task.id, category_id=None
        )
        assert unassigned.category_id is None


def test_list_categories_includes_task_count(app, test_user_id):
    """Verifica que list_user_categories incluya el conteo de tareas activas por categoría."""
    with app.app_context():
        category = CategoryService.create_category(user_id=test_user_id, name="Con Tareas")
        t1 = TaskService.create_task(user_id=test_user_id, title="Tarea A")
        t2 = TaskService.create_task(user_id=test_user_id, title="Tarea B")
        TaskService.assign_category(user_id=test_user_id, task_id=t1.id, category_id=category.id)
        TaskService.assign_category(user_id=test_user_id, task_id=t2.id, category_id=category.id)
        TaskService.delete_task(user_id=test_user_id, task_id=t2.id)

        categories = CategoryService.list_user_categories(user_id=test_user_id)
        found = next(c for c in categories if c["id"] == category.id)
        assert found["task_count"] == 1
