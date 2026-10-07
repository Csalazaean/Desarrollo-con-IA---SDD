from datetime import datetime, timezone
from src.taskcontrol.extensions import db


class Notification(db.Model):
    """Aviso interno dirigido a un usuario ante un evento relevante (HU-11).

    Las notificaciones viven exclusivamente dentro de la aplicación y su base de
    datos: no hay correo ni push externo (FR-009).
    """

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recipient_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    task_id = db.Column(
        db.Integer, db.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    # El mensaje se persiste ya redactado: así la notificación sigue teniendo
    # sentido aunque la tarea se elimine después y `task_id` quede en NULL.
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    recipient = db.relationship("User", foreign_keys=[recipient_id])
    sender = db.relationship("User", foreign_keys=[sender_id])

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "task_id": self.task_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
