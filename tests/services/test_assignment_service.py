import pytest
from src.taskcontrol.extensions import db
from src.taskcontrol.models.audit import AuditLog
from src.taskcontrol.models.notification import Notification
from src.taskcontrol.models.task import Task
from src.taskcontrol.services.task_service import (
    TaskService,
    TaskNotFoundError,
    NotTaskOwnerError,
    AssigneeNotFoundError,
)
from src.taskcontrol.services.user_service import UserService


def _usuario(email):
    return UserService.register_user(email, "Password123!")


def test_assign_task_to_existing_user(app):
    """Asignar vincula la tarea, audita el evento y notifica al destinatario (FR-001, FR-007)."""
    with app.app_context():
        creador = _usuario("asig-a@example.com")
        destinatario = _usuario("asig-b@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="Preparar informe")

        TaskService.assign_task_to_user(
            task_id=tarea.id, actor_id=creador.id, assignee_email="asig-b@example.com"
        )

        assert tarea.assigned_to_id == destinatario.id
        assert AuditLog.query.filter_by(action=AuditLog.ACTION_TASK_ASSIGNED).count() == 1
        assert Notification.query.filter_by(recipient_id=destinatario.id).count() == 1


def test_assign_to_unregistered_email_is_rejected_and_task_unchanged(app):
    """Asignar a un correo no registrado se rechaza sin tocar la tarea (FR-002, SC-001)."""
    with app.app_context():
        creador = _usuario("asig-c@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="No se asignará")

        with pytest.raises(AssigneeNotFoundError):
            TaskService.assign_task_to_user(
                task_id=tarea.id, actor_id=creador.id, assignee_email="fantasma@example.com"
            )

        assert tarea.assigned_to_id is None
        assert AuditLog.query.filter_by(action=AuditLog.ACTION_TASK_ASSIGNED).count() == 0
        assert Notification.query.count() == 0


def test_only_creator_can_assign(app):
    """Un tercero no puede reasignar una tarea ajena (Escenario 5, Principio VII)."""
    with app.app_context():
        creador = _usuario("asig-d@example.com")
        intruso = _usuario("asig-e@example.com")
        _usuario("asig-f@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="Tarea del creador")

        with pytest.raises(NotTaskOwnerError):
            TaskService.assign_task_to_user(
                task_id=tarea.id, actor_id=intruso.id, assignee_email="asig-f@example.com"
            )

        assert tarea.assigned_to_id is None


def test_unassign_task_sets_null_and_audits(app):
    """Retirar la asignación deja la tarea sin asignatario y lo audita (FR-003)."""
    with app.app_context():
        creador = _usuario("asig-g@example.com")
        _usuario("asig-h@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="Se desasignará")

        TaskService.assign_task_to_user(
            task_id=tarea.id, actor_id=creador.id, assignee_email="asig-h@example.com"
        )
        TaskService.assign_task_to_user(
            task_id=tarea.id, actor_id=creador.id, assignee_email=""
        )

        assert tarea.assigned_to_id is None
        assert AuditLog.query.filter_by(action=AuditLog.ACTION_TASK_UNASSIGNED).count() == 1


def test_reassignment_moves_task_between_assignees(app):
    """Reasignar notifica al nuevo y retira la tarea del listado del anterior (Edge Case)."""
    with app.app_context():
        creador = _usuario("asig-i@example.com")
        primero = _usuario("asig-j@example.com")
        segundo = _usuario("asig-k@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="Cambia de manos")

        TaskService.assign_task_to_user(
            task_id=tarea.id, actor_id=creador.id, assignee_email="asig-j@example.com"
        )
        TaskService.assign_task_to_user(
            task_id=tarea.id, actor_id=creador.id, assignee_email="asig-k@example.com"
        )

        assert tarea.assigned_to_id == segundo.id
        assert Notification.query.filter_by(recipient_id=segundo.id).count() == 1

        # El primer destinatario ya no la ve entre las asignadas a él
        assert TaskService.get_user_tasks(primero.id, scope="assigned") == []
        asignadas_segundo = TaskService.get_user_tasks(segundo.id, scope="assigned")
        assert [t.id for t in asignadas_segundo] == [tarea.id]


def test_assignee_sees_task_in_their_listing(app):
    """El destinatario ve la tarea asignada en su listado principal (FR-004, SC-002)."""
    with app.app_context():
        creador = _usuario("asig-l@example.com")
        destinatario = _usuario("asig-m@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="Delegada")
        TaskService.assign_task_to_user(
            task_id=tarea.id, actor_id=creador.id, assignee_email="asig-m@example.com"
        )

        todas = TaskService.get_user_tasks(destinatario.id)
        assert [t.id for t in todas] == [tarea.id]

        # Pero no figura entre las que él creó
        assert TaskService.get_user_tasks(destinatario.id, scope="created") == []


def test_scope_filters_separate_created_and_assigned(app):
    """Los tres ámbitos del listado se comportan según FR-006."""
    with app.app_context():
        creador = _usuario("asig-n@example.com")
        destinatario = _usuario("asig-o@example.com")

        propia = TaskService.create_task(user_id=destinatario.id, title="Mía")
        delegada = TaskService.create_task(user_id=creador.id, title="Delegada a mí")
        TaskService.assign_task_to_user(
            task_id=delegada.id, actor_id=creador.id, assignee_email="asig-o@example.com"
        )

        todas = {t.id for t in TaskService.get_user_tasks(destinatario.id, scope="all")}
        creadas = {t.id for t in TaskService.get_user_tasks(destinatario.id, scope="created")}
        asignadas = {t.id for t in TaskService.get_user_tasks(destinatario.id, scope="assigned")}

        assert todas == {propia.id, delegada.id}
        assert creadas == {propia.id}
        assert asignadas == {delegada.id}


def test_cannot_assign_deleted_task(app):
    """Una tarea eliminada lógicamente no admite asignación."""
    with app.app_context():
        creador = _usuario("asig-p@example.com")
        _usuario("asig-q@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="Será borrada")
        TaskService.delete_task(task_id=tarea.id, user_id=creador.id)

        with pytest.raises(TaskNotFoundError):
            TaskService.assign_task_to_user(
                task_id=tarea.id, actor_id=creador.id, assignee_email="asig-q@example.com"
            )


def test_deleted_task_disappears_from_both_listings(app):
    """Al eliminar una tarea asignada deja de verse para creador y destinatario (Edge Case)."""
    with app.app_context():
        creador = _usuario("asig-r@example.com")
        destinatario = _usuario("asig-s@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="Desaparecerá")
        TaskService.assign_task_to_user(
            task_id=tarea.id, actor_id=creador.id, assignee_email="asig-s@example.com"
        )

        TaskService.delete_task(task_id=tarea.id, user_id=creador.id)

        assert TaskService.get_user_tasks(creador.id) == []
        assert TaskService.get_user_tasks(destinatario.id) == []

        # La notificación histórica sobrevive al borrado de la tarea
        assert Notification.query.filter_by(recipient_id=destinatario.id).count() == 1


def test_self_assignment_is_allowed(app):
    """Un creador puede asignarse su propia tarea (Edge Case de autoasignación)."""
    with app.app_context():
        creador = _usuario("asig-t@example.com")
        tarea = TaskService.create_task(user_id=creador.id, title="Para mí mismo")

        TaskService.assign_task_to_user(
            task_id=tarea.id, actor_id=creador.id, assignee_email="asig-t@example.com"
        )

        assert tarea.assigned_to_id == creador.id
