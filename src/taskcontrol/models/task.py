from datetime import datetime, timezone
from src.taskcontrol.extensions import db


class Task(db.Model):
    """Modelo de Tarea (HU-01 a HU-04)."""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default="medium", index=True)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    category = db.relationship(
        "Category", backref=db.backref("tasks", lazy="dynamic", passive_deletes=True)
    )

    @property
    def is_overdue(self) -> bool:
        """Indicador de vencimiento calculado en backend bajo UTC (HU-09)."""
        if not self.due_date or self.status == "completed" or self.is_deleted:
            return False
        current_date_utc = datetime.now(timezone.utc).date()
        return self.due_date < current_date_utc

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "priority": self.priority,
            "is_overdue": self.is_overdue,
            "category": (
                {"id": self.category.id, "name": self.category.name, "color": self.category.color}
                if self.category_id and self.category
                else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
