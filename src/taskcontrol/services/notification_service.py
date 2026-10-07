from datetime import datetime, timezone
from src.taskcontrol.extensions import db
from src.taskcontrol.models.notification import Notification


class NotificationNotFoundError(Exception):
    """Notificación inexistente o perteneciente a otro usuario."""
    pass


class NotificationService:
    """Gestión de notificaciones internas del usuario (HU-11, Principio II).

    Todas las consultas filtran por `recipient_id`: el aislamiento entre usuarios
    no depende de que quien llame se acuerde de comprobarlo (FR-014).
    """

    MAX_MESSAGE_LENGTH = 255

    @classmethod
    def create_assignment_notification(cls, recipient_id: int, sender_id: int, task) -> Notification:
        """Crea la notificación de una asignación de tarea.

        No hace `commit`: se integra en la transacción de la asignación para que la
        tarea y su aviso se persistan juntos o no se persista ninguno (plan.md §4).
        """
        mensaje = f"{task.user.email} te asignó la tarea '{task.title}'"
        if len(mensaje) > cls.MAX_MESSAGE_LENGTH:
            mensaje = mensaje[: cls.MAX_MESSAGE_LENGTH - 3] + "..."

        notificacion = Notification(
            recipient_id=recipient_id,
            sender_id=sender_id,
            task_id=task.id,
            message=mensaje,
            is_read=False,
        )
        db.session.add(notificacion)
        db.session.flush()
        return notificacion

    @classmethod
    def get_user_notifications(cls, user_id: int) -> list:
        """Lista las notificaciones del usuario, de la más reciente a la más antigua."""
        return (
            Notification.query.filter_by(recipient_id=user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .all()
        )

    @classmethod
    def unread_count(cls, user_id: int) -> int:
        """Cuenta las notificaciones sin leer del usuario (FR-011)."""
        return Notification.query.filter_by(recipient_id=user_id, is_read=False).count()

    @classmethod
    def get_notification(cls, notification_id: int, user_id: int) -> Notification:
        """Obtiene una notificación propia; una ajena se trata como inexistente."""
        notificacion = Notification.query.filter_by(
            id=notification_id, recipient_id=user_id
        ).first()
        if not notificacion:
            raise NotificationNotFoundError("Notificación no encontrada")
        return notificacion

    @classmethod
    def mark_as_read(cls, notification_id: int, user_id: int) -> Notification:
        """Marca una notificación como leída (FR-012).

        Es idempotente: si ya estaba leída conserva su `read_at` original, de modo
        que dos pestañas marcándola a la vez no alteran el historial ni el contador.
        La notificación nunca se elimina (FR-013).
        """
        notificacion = cls.get_notification(notification_id, user_id)

        if not notificacion.is_read:
            notificacion.is_read = True
            notificacion.read_at = datetime.now(timezone.utc)
            db.session.commit()

        return notificacion

    @classmethod
    def mark_all_as_read(cls, user_id: int) -> int:
        """Marca de una sola vez todas las notificaciones pendientes del usuario."""
        ahora = datetime.now(timezone.utc)
        pendientes = Notification.query.filter_by(
            recipient_id=user_id, is_read=False
        ).all()

        for notificacion in pendientes:
            notificacion.is_read = True
            notificacion.read_at = ahora

        db.session.commit()
        return len(pendientes)
