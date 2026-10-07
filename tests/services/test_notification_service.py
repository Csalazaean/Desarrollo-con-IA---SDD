import pytest
from src.taskcontrol.extensions import db
from src.taskcontrol.services.user_service import UserService
from src.taskcontrol.services.task_service import TaskService
from src.taskcontrol.services.notification_service import (
    NotificationService,
    NotificationNotFoundError,
)
from src.taskcontrol.models.notification import Notification


@pytest.fixture
def sender_id(app):
    with app.app_context():
        user = UserService.register_user("notifsender@example.com", "Password123!")
        return user.id


@pytest.fixture
def recipient_id(app):
    with app.app_context():
        user = UserService.register_user("notifrecipient@example.com", "Password123!")
        return user.id


@pytest.fixture
def other_user_id(app):
    with app.app_context():
        user = UserService.register_user("notifother@example.com", "Password123!")
        return user.id


# --- US2 (Incremento 4): Notificaciones Internas de Asignación (HU-11) ---

def test_create_notification_persists_and_links_task(app, sender_id, recipient_id):
    """Verifica que la notificación se persista con mensaje denormalizado y referencia a la tarea."""
    with app.app_context():
        task = TaskService.create_task(user_id=sender_id, title="Tarea Notificada")
        notification = NotificationService.create_notification(
            recipient_id=recipient_id, sender_id=sender_id, task=task
        )
        assert notification.id is not None
        assert notification.task_id == task.id
        assert notification.is_read is False
        assert "Tarea Notificada" in notification.message


def test_notification_isolation_between_users(app, sender_id, recipient_id, other_user_id):
    """Verifica que un usuario no pueda ver ni marcar notificaciones de otro (Cero IDOR, BLOQUEANTE)."""
    with app.app_context():
        task = TaskService.create_task(user_id=sender_id, title="Tarea Aislada")
        notification = NotificationService.create_notification(
            recipient_id=recipient_id, sender_id=sender_id, task=task
        )

        other_notifications = NotificationService.list_user_notifications(user_id=other_user_id)
        assert notification.id not in [n.id for n in other_notifications]

        with pytest.raises(NotificationNotFoundError):
            NotificationService.mark_as_read(notification_id=notification.id, user_id=other_user_id)


def test_mark_notification_as_read_updates_is_read_and_read_at(app, sender_id, recipient_id):
    """Verifica que marcar como leída actualice is_read y read_at."""
    with app.app_context():
        task = TaskService.create_task(user_id=sender_id, title="Tarea X")
        notification = NotificationService.create_notification(
            recipient_id=recipient_id, sender_id=sender_id, task=task
        )

        updated = NotificationService.mark_as_read(notification_id=notification.id, user_id=recipient_id)
        assert updated.is_read is True
        assert updated.read_at is not None


def test_mark_notification_as_read_is_idempotent(app, sender_id, recipient_id):
    """Verifica que marcar dos veces la misma notificación no falle (Edge Case concurrencia)."""
    with app.app_context():
        task = TaskService.create_task(user_id=sender_id, title="Tarea Y")
        notification = NotificationService.create_notification(
            recipient_id=recipient_id, sender_id=sender_id, task=task
        )

        NotificationService.mark_as_read(notification_id=notification.id, user_id=recipient_id)
        first_read_at = db.session.get(Notification, notification.id).read_at

        NotificationService.mark_as_read(notification_id=notification.id, user_id=recipient_id)
        second_read_at = db.session.get(Notification, notification.id).read_at

        assert first_read_at == second_read_at


def test_mark_all_as_read_updates_all_pending_atomically(app, sender_id, recipient_id):
    """Verifica que marcar todas como leídas actualice únicamente las pendientes del usuario."""
    with app.app_context():
        task1 = TaskService.create_task(user_id=sender_id, title="Tarea 1")
        task2 = TaskService.create_task(user_id=sender_id, title="Tarea 2")
        NotificationService.create_notification(recipient_id=recipient_id, sender_id=sender_id, task=task1)
        NotificationService.create_notification(recipient_id=recipient_id, sender_id=sender_id, task=task2)

        updated_count = NotificationService.mark_all_as_read(user_id=recipient_id)
        assert updated_count == 2
        assert NotificationService.get_unread_count(user_id=recipient_id) == 0


def test_unread_count_reflects_pending_notifications(app, sender_id, recipient_id):
    """Verifica que el conteo de no leídas decremente al marcar una notificación."""
    with app.app_context():
        task1 = TaskService.create_task(user_id=sender_id, title="Tarea A")
        task2 = TaskService.create_task(user_id=sender_id, title="Tarea B")
        n1 = NotificationService.create_notification(recipient_id=recipient_id, sender_id=sender_id, task=task1)
        NotificationService.create_notification(recipient_id=recipient_id, sender_id=sender_id, task=task2)

        assert NotificationService.get_unread_count(user_id=recipient_id) == 2
        NotificationService.mark_as_read(notification_id=n1.id, user_id=recipient_id)
        assert NotificationService.get_unread_count(user_id=recipient_id) == 1


def test_read_notification_remains_in_history(app, sender_id, recipient_id):
    """Verifica que una notificación leída NO se descarte del historial (FR-013, hallazgo M1 de /speckit-analyze)."""
    with app.app_context():
        task = TaskService.create_task(user_id=sender_id, title="Tarea Historica")
        notification = NotificationService.create_notification(
            recipient_id=recipient_id, sender_id=sender_id, task=task
        )
        NotificationService.mark_as_read(notification_id=notification.id, user_id=recipient_id)

        history = NotificationService.list_user_notifications(user_id=recipient_id)
        assert notification.id in [n.id for n in history]


def test_notification_survives_soft_deleted_task(app, sender_id, recipient_id):
    """Verifica que la notificación conserve su mensaje aunque la tarea referenciada se elimine lógicamente
    (Edge Case 'Eliminación lógica de tarea asignada'; hallazgo M2 de /speckit-analyze)."""
    with app.app_context():
        task = TaskService.create_task(user_id=sender_id, title="Tarea que será eliminada")
        notification = NotificationService.create_notification(
            recipient_id=recipient_id, sender_id=sender_id, task=task
        )
        original_message = notification.message

        TaskService.delete_task(user_id=sender_id, task_id=task.id)

        history = NotificationService.list_user_notifications(user_id=recipient_id)
        preserved = next(n for n in history if n.id == notification.id)
        assert preserved.message == original_message
