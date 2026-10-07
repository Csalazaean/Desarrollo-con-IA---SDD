from datetime import datetime, timezone
from src.taskcontrol.extensions import db
from src.taskcontrol.models.notification import Notification


class NotificationNotFoundError(Exception):
    """Notificación no encontrada o no perteneciente al usuario."""
    pass


class NotificationService:
    """Lógica de negocio para notificaciones internas de colaboración (HU-11)."""

    @classmethod
    def create_notification(cls, recipient_id: int, sender_id: int, task) -> Notification:
        """Crea y persiste una notificación con mensaje denormalizado (ver research.md §5)."""
        from src.taskcontrol.models.user import User

        sender = db.session.get(User, sender_id)
        message = f"{sender.email} te asignó la tarea '{task.title}'"[:255]

        notification = Notification(
            recipient_id=recipient_id,
            sender_id=sender_id,
            task_id=task.id,
            message=message,
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @classmethod
    def list_user_notifications(cls, user_id: int) -> list:
        """Lista las notificaciones del usuario, cronológicamente descendente (FR-010)."""
        return (
            Notification.query.filter_by(recipient_id=user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    @classmethod
    def get_unread_count(cls, user_id: int) -> int:
        """Conteo de notificaciones no leídas (FR-011)."""
        return Notification.query.filter_by(recipient_id=user_id, is_read=False).count()

    @classmethod
    def mark_as_read(cls, notification_id: int, user_id: int) -> Notification:
        """Marca una notificación propia como leída; idempotente (Edge Case concurrencia)."""
        notification = Notification.query.filter_by(
            id=notification_id, recipient_id=user_id
        ).first()
        if not notification:
            raise NotificationNotFoundError("Notificación no encontrada")

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            db.session.commit()

        return notification

    @classmethod
    def mark_all_as_read(cls, user_id: int) -> int:
        """Marca todas las notificaciones pendientes del usuario como leídas, atómicamente (FR-012)."""
        now = datetime.now(timezone.utc)
        updated = Notification.query.filter_by(recipient_id=user_id, is_read=False).update(
            {Notification.is_read: True, Notification.read_at: now}
        )
        db.session.commit()
        return updated
