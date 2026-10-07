from datetime import datetime, timezone
from src.taskcontrol.extensions import db


class User(db.Model):
    """Modelo de Usuario (HU-12, HU-13)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relación 1 a N con Task (como creador). foreign_keys explícito porque Task
    # también tiene assigned_to_id apuntando a users.id (ver research.md Incremento 4 §4).
    tasks = db.relationship(
        "Task",
        foreign_keys="Task.user_id",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
