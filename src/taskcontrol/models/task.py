from datetime import datetime, timezone
from src.taskcontrol.extensions import db


class Task(db.Model):
    """Modelo de Tarea (HU-01 a HU-04)."""

    __tablename__ = "tasks"

    # Prioridades permitidas (HU-07). El orden del diccionario define la jerarquía
    # usada al ordenar: alta > media > baja. Ordenar por la cadena sería alfabético
    # ("high" < "low" < "medium"), que no es la precedencia que pide FR-004.
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"
    DEFAULT_PRIORITY = PRIORITY_MEDIUM
    PRIORITY_RANK = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
    VALID_PRIORITIES = tuple(PRIORITY_RANK.keys())

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Creador (`user_id`) y asignado (`assigned_to_id`) son columnas distintas:
    # el creador es inmutable y conserva el control de la tarea, mientras que la
    # asignación puede cambiar o retirarse sin alterar la propiedad (plan.md §2.1).
    assigned_to_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    priority = db.Column(
        db.String(20), nullable=False, default=DEFAULT_PRIORITY, index=True
    )
    # Orden personal del listado (HU-16). Entero ascendente: a menor valor, más
    # arriba. Es por usuario, no global: las posiciones solo se comparan entre
    # tareas del mismo propietario.
    position = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    category = db.relationship("Category", back_populates="tasks")
    assignee = db.relationship("User", foreign_keys=[assigned_to_id])

    @property
    def creator_email(self):
        return self.user.email if self.user else None

    @property
    def assignee_email(self):
        return self.assignee.email if self.assignee else None

    @property
    def is_overdue(self) -> bool:
        """Indica si la tarea está vencida (HU-09).

        Se calcula aquí, en el backend y contra la fecha UTC, nunca en JavaScript:
        la hora del navegador haría que la misma tarea apareciera vencida o no según
        la zona horaria de quien la mire (FR-011, FR-013).

        Una tarea cuyo plazo es hoy todavía no está vencida: solo lo está cuando la
        fecha límite quedó atrás (FR-012).
        """
        if self.due_date is None:
            return False
        if self.status == "completed" or self.is_deleted:
            return False
        return self.due_date < datetime.now(timezone.utc).date()

    def to_dict(self, viewer_id: int = None):
        """Serializa la tarea.

        `viewer_id` permite que el backend resuelva la autoría respecto de quien
        consulta, para que la plantilla solo pinte el distintivo en vez de deducirla
        por su cuenta (FR-005).
        """
        datos = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "priority": self.priority,
            "is_overdue": self.is_overdue,
            "category": self.category.to_dict() if self.category else None,
            "category_id": self.category_id,
            "assigned_to_id": self.assigned_to_id,
            "assignee_email": self.assignee_email,
            "creator_email": self.creator_email,
            "position": self.position,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if viewer_id is not None:
            datos["is_mine"] = self.user_id == viewer_id
            datos["is_assigned_to_me"] = self.assigned_to_id == viewer_id

        return datos
