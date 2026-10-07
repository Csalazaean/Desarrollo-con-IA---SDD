import pytest
from src.taskcontrol.models.notification import Notification
from src.taskcontrol.services.notification_service import (
    NotificationService,
    NotificationNotFoundError,
)
from src.taskcontrol.services.task_service import TaskService
from src.taskcontrol.services.user_service import UserService


def _usuario(email):
    return UserService.register_user(email, "Password123!")


def _asignar(creador, destinatario_email, titulo="Tarea delegada"):
    tarea = TaskService.create_task(user_id=creador.id, title=titulo)
    TaskService.assign_task_to_user(
        task_id=tarea.id, actor_id=creador.id, assignee_email=destinatario_email
    )
    return tarea


def test_assignment_creates_exactly_one_notification(app):
    """Cada asignación a un tercero genera exactamente una notificación (FR-008, SC-003)."""
    with app.app_context():
        creador = _usuario("not-a@example.com")
        destinatario = _usuario("not-b@example.com")
        tarea = _asignar(creador, "not-b@example.com", "Revisar documento")

        notificaciones = NotificationService.get_user_notifications(destinatario.id)
        assert len(notificaciones) == 1

        notificacion = notificaciones[0]
        assert notificacion.recipient_id == destinatario.id
        assert notificacion.sender_id == creador.id
        assert notificacion.task_id == tarea.id
        assert notificacion.is_read is False
        # El mensaje menciona a quien asignó y el título de la tarea
        assert "not-a@example.com" in notificacion.message
        assert "Revisar documento" in notificacion.message


def test_self_assignment_creates_no_notification(app):
    """Autoasignarse una tarea no genera ruido de notificación (Edge Case)."""
    with app.app_context():
        creador = _usuario("not-c@example.com")
        _asignar(creador, "not-c@example.com")

        assert NotificationService.get_user_notifications(creador.id) == []
        assert NotificationService.unread_count(creador.id) == 0


def test_unread_count_per_user(app):
    """El contador de no leídas es estrictamente por usuario (FR-011, FR-014)."""
    with app.app_context():
        creador = _usuario("not-d@example.com")
        destinatario = _usuario("not-e@example.com")
        ajeno = _usuario("not-f@example.com")

        _asignar(creador, "not-e@example.com", "Una")
        _asignar(creador, "not-e@example.com", "Dos")

        assert NotificationService.unread_count(destinatario.id) == 2
        assert NotificationService.unread_count(ajeno.id) == 0


def test_mark_as_read_is_idempotent_and_keeps_read_at(app):
    """Marcar como leída dos veces no altera el read_at original (Edge Case de concurrencia)."""
    with app.app_context():
        creador = _usuario("not-g@example.com")
        destinatario = _usuario("not-h@example.com")
        _asignar(creador, "not-h@example.com")

        notificacion = NotificationService.get_user_notifications(destinatario.id)[0]
        NotificationService.mark_as_read(notificacion.id, destinatario.id)
        primer_read_at = notificacion.read_at

        assert notificacion.is_read is True
        assert primer_read_at is not None

        NotificationService.mark_as_read(notificacion.id, destinatario.id)
        assert notificacion.read_at == primer_read_at
        assert NotificationService.unread_count(destinatario.id) == 0


def test_read_notification_is_not_deleted(app):
    """Una notificación leída permanece en el historial, no se descarta (FR-013, SC-004)."""
    with app.app_context():
        creador = _usuario("not-i@example.com")
        destinatario = _usuario("not-j@example.com")
        _asignar(creador, "not-j@example.com")

        notificacion = NotificationService.get_user_notifications(destinatario.id)[0]
        NotificationService.mark_as_read(notificacion.id, destinatario.id)

        assert Notification.query.filter_by(recipient_id=destinatario.id).count() == 1
        assert len(NotificationService.get_user_notifications(destinatario.id)) == 1


def test_mark_all_as_read(app):
    """Marcar todas como leídas actualiza el lote completo (FR-012)."""
    with app.app_context():
        creador = _usuario("not-k@example.com")
        destinatario = _usuario("not-l@example.com")
        for titulo in ("Uno", "Dos", "Tres"):
            _asignar(creador, "not-l@example.com", titulo)

        assert NotificationService.unread_count(destinatario.id) == 3

        marcadas = NotificationService.mark_all_as_read(destinatario.id)
        assert marcadas == 3
        assert NotificationService.unread_count(destinatario.id) == 0
        assert len(NotificationService.get_user_notifications(destinatario.id)) == 3


def test_cannot_read_notification_of_another_user(app):
    """Nadie puede marcar como leída una notificación ajena (FR-014)."""
    with app.app_context():
        creador = _usuario("not-m@example.com")
        destinatario = _usuario("not-n@example.com")
        intruso = _usuario("not-o@example.com")
        _asignar(creador, "not-n@example.com")

        notificacion = NotificationService.get_user_notifications(destinatario.id)[0]

        with pytest.raises(NotificationNotFoundError):
            NotificationService.mark_as_read(notificacion.id, intruso.id)

        assert notificacion.is_read is False


def test_notifications_are_sorted_newest_first(app):
    """El listado llega en orden cronológico descendente (FR-010)."""
    with app.app_context():
        creador = _usuario("not-p@example.com")
        destinatario = _usuario("not-q@example.com")
        for titulo in ("Primera", "Segunda", "Tercera"):
            _asignar(creador, "not-q@example.com", titulo)

        notificaciones = NotificationService.get_user_notifications(destinatario.id)
        assert "Tercera" in notificaciones[0].message
        assert "Primera" in notificaciones[-1].message
