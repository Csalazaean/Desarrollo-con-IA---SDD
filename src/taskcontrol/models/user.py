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

    # Relación 1 a N con Task (tareas creadas).
    # `foreign_keys` es obligatorio desde el Incremento 4: Task apunta dos veces a
    # users (user_id como creador y assigned_to_id como asignado) y sin indicarlo
    # SQLAlchemy no puede decidir cuál de las dos define esta relación.
    tasks = db.relationship(
        "Task",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="Task.user_id",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
