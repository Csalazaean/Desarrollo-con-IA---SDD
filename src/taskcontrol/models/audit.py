from datetime import datetime, timezone
from src.taskcontrol.extensions import db


class AuditLog(db.Model):
    """Modelo inmutable para auditoría y observabilidad (Principio VIII)."""

    __tablename__ = "audit_logs"

    # Acciones estándar de auditoría (Principio VIII)
    ACTION_TASK_CREATED = "TASK_CREATED"
    ACTION_STATUS_CHANGED = "STATUS_CHANGED"
    ACTION_TASK_UPDATED = "TASK_UPDATED"
    ACTION_TASK_DELETED = "TASK_DELETED"
    ACTION_TASK_REOPENED = "TASK_REOPENED"
    ACTION_USER_REGISTERED = "USER_REGISTERED"
    ACTION_USER_LOGIN = "USER_LOGIN"
    ACTION_PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    ACTION_PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"
    ACTION_CATEGORY_CREATED = "CATEGORY_CREATED"
    ACTION_CATEGORY_UPDATED = "CATEGORY_UPDATED"
    ACTION_CATEGORY_DELETED = "CATEGORY_DELETED"
    ACTION_TASK_ASSIGNED = "TASK_ASSIGNED"
    ACTION_TASK_UNASSIGNED = "TASK_UNASSIGNED"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    actor_id = db.Column(db.Integer, nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    timestamp = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    details = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "action": self.action,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": self.details,
        }
