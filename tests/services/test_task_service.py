from datetime import date
import pytest
from src.taskcontrol.services.user_service import UserService
from src.taskcontrol.services.task_service import (
    TaskService,
    TaskValidationError,
    TaskNotFoundError,
    InvalidStateTransitionError,
    TaskAlreadyDeletedError,
)
from src.taskcontrol.models.audit import AuditLog
from src.taskcontrol.models.task import Task


@pytest.fixture
def test_user_id(app):
    with app.app_context():
        user = UserService.register_user("taskowner@example.com", "Password123!")
        return user.id


@pytest.fixture
def second_user_id(app):
    with app.app_context():
        user = UserService.register_user("seconduser@example.com", "Password123!")
        return user.id


# --- US3: Creación de Tareas (HU-01) ---

def test_create_task_success(app, test_user_id):
    """Verifica la creación exitosa de una tarea con estado pending y log de auditoría."""
    with app.app_context():
        task = TaskService.create_task(
            user_id=test_user_id,
            title="Mi primera tarea",
            description="Descripción opcional",
            due_date=date(2026, 10, 15),
        )
        assert task.id is not None
        assert task.title == "Mi primera tarea"
        assert task.description == "Descripción opcional"
        assert task.status == "pending"
        assert task.user_id == test_user_id

        # Verificar generación de auditoría (Principio VIII)
        audit = AuditLog.query.filter_by(
            action="TASK_CREATED", entity_id=task.id
        ).first()
        assert audit is not None
        assert audit.actor_id == test_user_id


def test_create_task_empty_title_fails(app, test_user_id):
    """Verifica que se rechace un título vacío o con solo espacios."""
    with app.app_context():
        with pytest.raises(TaskValidationError):
            TaskService.create_task(user_id=test_user_id, title="   ")


def test_create_task_title_too_long(app, test_user_id):
    """Verifica que se rechace un título que exceda 150 caracteres."""
    with app.app_context():
        with pytest.raises(TaskValidationError):
            TaskService.create_task(user_id=test_user_id, title="A" * 151)


# --- US4: Listado y Filtrado de Tareas (HU-02) ---

def test_get_user_tasks_isolation(app, test_user_id, second_user_id):
    """Verifica aislamiento estricto entre usuarios (Principio VII / Cero IDOR)."""
    with app.app_context():
        TaskService.create_task(user_id=test_user_id, title="Tarea de Usuario 1")
        TaskService.create_task(user_id=second_user_id, title="Tarea de Usuario 2")

        tasks_user1 = TaskService.get_user_tasks(user_id=test_user_id)
        assert len(tasks_user1) == 1
        assert tasks_user1[0].title == "Tarea de Usuario 1"

        tasks_user2 = TaskService.get_user_tasks(user_id=second_user_id)
        assert len(tasks_user2) == 1
        assert tasks_user2[0].title == "Tarea de Usuario 2"


def test_filter_tasks_by_status(app, test_user_id):
    """Verifica que el filtrado por estado retorne únicamente las tareas coincidentes."""
    with app.app_context():
        t1 = TaskService.create_task(user_id=test_user_id, title="Tarea 1")
        t2 = TaskService.create_task(user_id=test_user_id, title="Tarea 2")
        TaskService.update_task_status(
            user_id=test_user_id, task_id=t2.id, new_status="completed"
        )

        pending = TaskService.get_user_tasks(user_id=test_user_id, status="pending")
        completed = TaskService.get_user_tasks(user_id=test_user_id, status="completed")

        assert len(pending) == 1
        assert pending[0].id == t1.id
        assert len(completed) == 1
        assert completed[0].id == t2.id


# --- US5: Cambio de Estado de Tareas (HU-03) ---

def test_task_state_transitions(app, test_user_id):
    """Verifica transiciones válidas y emisión de log de auditoría STATUS_CHANGED."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Flujo")

        # pending -> in_progress
        task = TaskService.update_task_status(
            user_id=test_user_id, task_id=task.id, new_status="in_progress"
        )
        assert task.status == "in_progress"

        # in_progress -> completed
        task = TaskService.update_task_status(
            user_id=test_user_id, task_id=task.id, new_status="completed"
        )
        assert task.status == "completed"

        # Verificar auditoría
        audits = AuditLog.query.filter_by(
            action="STATUS_CHANGED", entity_id=task.id
        ).all()
        assert len(audits) == 2


def test_reopening_completed_task_fails(app, test_user_id):
    """Verifica que la reapertura (completed -> pending) esté explícitamente bloqueada en este incremento."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Finalizada")
        TaskService.update_task_status(
            user_id=test_user_id, task_id=task.id, new_status="completed"
        )

        with pytest.raises(InvalidStateTransitionError):
            TaskService.update_task_status(
                user_id=test_user_id, task_id=task.id, new_status="pending"
            )


# --- US6: Edición de Tareas (HU-04) ---

def test_update_task_details_success(app, test_user_id):
    """Verifica edición de campos informativos y registro en auditoría."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Título Inicial")
        updated = TaskService.update_task_details(
            user_id=test_user_id,
            task_id=task.id,
            title="Título Modificado",
            description="Nueva descripción",
            due_date=date(2026, 11, 1),
        )
        assert updated.title == "Título Modificado"
        assert updated.description == "Nueva descripción"
        assert updated.due_date == date(2026, 11, 1)

        audit = AuditLog.query.filter_by(
            action="TASK_UPDATED", entity_id=task.id
        ).first()
        assert audit is not None


def test_update_task_empty_title_fails(app, test_user_id):
    """Verifica que editar con título vacío sea rechazado."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Título Válido")
        with pytest.raises(TaskValidationError):
            TaskService.update_task_details(
                user_id=test_user_id, task_id=task.id, title=""
            )


def test_update_task_unauthorized_user(app, test_user_id, second_user_id):
    """Verifica que un usuario no pueda editar tareas de otro usuario (Cero IDOR)."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea de User 1")
        with pytest.raises(TaskNotFoundError):
            TaskService.update_task_details(
                user_id=second_user_id, task_id=task.id, title="Hack intento"
            )


# --- US1 (HU-05): Eliminación Lógica de Tareas (Soft Delete) ---

def test_soft_delete_task_marks_deleted_and_sets_timestamp(app, test_user_id):
    """Verifica que soft delete marque is_deleted=True, fije deleted_at y genere TASK_DELETED."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea a borrar")
        deleted_task = TaskService.delete_task(task_id=task.id, user_id=test_user_id)

        assert deleted_task.is_deleted is True
        assert deleted_task.deleted_at is not None

        # Auditoría de eliminación (Principio VIII)
        audit = AuditLog.query.filter_by(
            action="TASK_DELETED", entity_id=task.id
        ).first()
        assert audit is not None
        assert audit.actor_id == test_user_id


def test_soft_delete_preserves_task_in_database_and_audit_history(app, test_user_id):
    """Verifica que la tarea no se elimine físicamente y mantenga su historial de auditoría."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea conservada en BD")
        TaskService.delete_task(task_id=task.id, user_id=test_user_id)

        # La fila continúa existiendo físicamente en la BD
        persisted = Task.query.filter_by(id=task.id).first()
        assert persisted is not None
        assert persisted.is_deleted is True

        # Historial de auditoría completo preservado (Principio VI y VIII)
        audits = AuditLog.query.filter_by(entity_id=task.id).order_by(AuditLog.id.asc()).all()
        actions = [a.action for a in audits]
        assert "TASK_CREATED" in actions
        assert "TASK_DELETED" in actions


def test_deleted_task_excluded_from_default_listing(app, test_user_id):
    """Verifica que las tareas eliminadas no se incluyan en el listado por defecto."""
    with app.app_context():
        t1 = TaskService.create_task(user_id=test_user_id, title="Tarea Activa 1")
        t2 = TaskService.create_task(user_id=test_user_id, title="Tarea Activa 2")
        t3 = TaskService.create_task(user_id=test_user_id, title="Tarea para eliminar")

        TaskService.delete_task(task_id=t3.id, user_id=test_user_id)

        active_tasks = TaskService.get_user_tasks(user_id=test_user_id)
        active_ids = [t.id for t in active_tasks]
        assert t1.id in active_ids
        assert t2.id in active_ids
        assert t3.id not in active_ids
        assert len(active_tasks) == 2


def test_cannot_delete_already_deleted_task(app, test_user_id):
    """Verifica que intentar eliminar una tarea ya eliminada arroje TaskAlreadyDeletedError."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea doble borrado")
        TaskService.delete_task(task_id=task.id, user_id=test_user_id)

        with pytest.raises(TaskAlreadyDeletedError):
            TaskService.delete_task(task_id=task.id, user_id=test_user_id)


def test_cannot_edit_deleted_task(app, test_user_id):
    """Verifica que no se permita modificar los detalles ni el estado de una tarea eliminada."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea a eliminar y editar")
        TaskService.delete_task(task_id=task.id, user_id=test_user_id)

        with pytest.raises((TaskNotFoundError, TaskAlreadyDeletedError)):
            TaskService.update_task_details(
                user_id=test_user_id, task_id=task.id, title="Nuevo Título"
            )

        with pytest.raises((TaskNotFoundError, TaskAlreadyDeletedError, InvalidStateTransitionError)):
            TaskService.update_task_status(
                user_id=test_user_id, task_id=task.id, new_status="completed"
            )


def test_delete_task_unauthorized_or_not_found(app, test_user_id, second_user_id):
    """Verifica que un usuario no pueda eliminar tareas ajenas ni inexistentes."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea ajena")
        with pytest.raises(TaskNotFoundError):
            TaskService.delete_task(task_id=task.id, user_id=second_user_id)

        with pytest.raises(TaskNotFoundError):
            TaskService.delete_task(task_id=99999, user_id=test_user_id)


# --- US2 (HU-06): Reapertura de Tareas Completadas ---

def test_reopen_completed_task_success(app, test_user_id):
    """Verifica que reabrir una tarea completada cambie su estado a pending."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea para completar y reabrir")
        TaskService.update_task_status(user_id=test_user_id, task_id=task.id, new_status="completed")

        reopened = TaskService.reopen_task(task_id=task.id, user_id=test_user_id)
        assert reopened.status == "pending"


def test_reopen_task_generates_specific_task_reopened_audit_log(app, test_user_id):
    """Verifica que se registre el evento TASK_REOPENED diferenciado de STATUS_CHANGED."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea para auditar reapertura")
        TaskService.update_task_status(user_id=test_user_id, task_id=task.id, new_status="completed")
        TaskService.reopen_task(task_id=task.id, user_id=test_user_id)

        audit = AuditLog.query.filter_by(
            action="TASK_REOPENED", entity_id=task.id
        ).first()
        assert audit is not None
        assert audit.actor_id == test_user_id
        assert "completed" in audit.details
        assert "pending" in audit.details


def test_cannot_reopen_non_completed_task(app, test_user_id):
    """Verifica que reabrir tareas en pending o in_progress sea rechazado."""
    with app.app_context():
        task_pending = TaskService.create_task(user_id=test_user_id, title="Tarea pendiente")
        with pytest.raises(InvalidStateTransitionError):
            TaskService.reopen_task(task_id=task_pending.id, user_id=test_user_id)

        task_in_progress = TaskService.create_task(user_id=test_user_id, title="Tarea en progreso")
        TaskService.update_task_status(user_id=test_user_id, task_id=task_in_progress.id, new_status="in_progress")
        with pytest.raises(InvalidStateTransitionError):
            TaskService.reopen_task(task_id=task_in_progress.id, user_id=test_user_id)


def test_cannot_reopen_deleted_task(app, test_user_id):
    """Verifica que no se pueda reabrir una tarea eliminada lógicamente."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea completada luego borrada")
        TaskService.update_task_status(user_id=test_user_id, task_id=task.id, new_status="completed")
        TaskService.delete_task(task_id=task.id, user_id=test_user_id)

        with pytest.raises((TaskNotFoundError, TaskAlreadyDeletedError, InvalidStateTransitionError)):
            TaskService.reopen_task(task_id=task.id, user_id=test_user_id)
