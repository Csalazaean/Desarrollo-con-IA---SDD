from datetime import datetime, timezone
from src.taskcontrol.extensions import db


class Category(db.Model):
    """Categoría o proyecto para agrupar tareas de un usuario (HU-08)."""

    __tablename__ = "categories"
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_user_category_name"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Las tareas se desvinculan al borrar la categoría; nunca se eliminan en cascada (FR-009).
    tasks = db.relationship("Task", back_populates="category")

    def to_dict(self, task_count=None):
        datos = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if task_count is not None:
            datos["task_count"] = task_count
        return datos
