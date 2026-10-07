from datetime import date, datetime, timezone
from src.taskcontrol.extensions import db
from src.taskcontrol.models.task import Task
from src.taskcontrol.services.audit_service import AuditService


class TaskValidationError(Exception):
    """Error de validación para tareas."""
    pass


class TaskNotFoundError(Exception):
    """Tarea no encontrada o no perteneciente al usuario."""
    pass


class InvalidStateTransitionError(Exception):
    """Transición de estado no permitida por la máquina de estados."""
    pass


class TaskAlreadyDeletedError(Exception):
    """La tarea ya se encuentra eliminada lógicamente."""
    pass


class InvalidTaskStateTransitionError(Exception):
    """Transición no permitida en el ciclo de cierre/reapertura de tareas (Incremento 2)."""
    pass


class TaskService:
    """Lógica de negocio del ciclo de vida y gestión de tareas (Principio II)."""

    VALID_TRANSITIONS = {
        "pending": {"in_progress", "completed"},
        "in_progress": {"pending", "completed"},
        "completed": set(),  # Bloqueada la reapertura en este incremento
    }

    @classmethod
    def create_task(
        cls,
        user_id: int,
        title: str,
        description: str = None,
        due_date: date = None,
    ) -> Task:
        """Crea una nueva tarea para el usuario y audita el evento."""
        if not title or not title.strip():
            raise TaskValidationError("El título de la tarea es obligatorio y no puede estar vacío")

        clean_title = title.strip()
        if len(clean_title) > 150:
            raise TaskValidationError("El título no puede exceder 150 caracteres")

        task = Task(
            user_id=user_id,
            title=clean_title,
            description=description.strip() if description else None,
            due_date=due_date,
            status="pending",
        )
        db.session.add(task)
        db.session.commit()

        # Auditoría obligatoria (Principio VIII)
        AuditService.log_event(
            actor_id=user_id,
            action="TASK_CREATED",
            entity_id=task.id,
            details={"title": clean_title, "status": "pending"},
        )
        db.session.commit()

        return task

    @classmethod
    def get_user_tasks(cls, user_id: int, status: str = None):
        """Lista las tareas activas (no eliminadas) del usuario autenticado con filtrado opcional."""
        query = Task.query.filter_by(user_id=user_id, is_deleted=False)
        if status in {"pending", "in_progress", "completed"}:
            query = query.filter_by(status=status)
        return query.order_by(Task.created_at.desc()).all()

    @classmethod
    def get_task_by_id(cls, user_id: int, task_id: int) -> Task:
        """Obtiene una tarea activa verificando la propiedad del usuario autenticado."""
        task = Task.query.filter_by(
            id=task_id, user_id=user_id, is_deleted=False
        ).first()
        if not task:
            raise TaskNotFoundError("Tarea no encontrada")
        return task

    @classmethod
    def update_task_status(cls, user_id: int, task_id: int, new_status: str) -> Task:
        """Aplica una transición de estado a la tarea del usuario."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)

        if new_status not in cls.VALID_TRANSITIONS.get(task.status, set()):
            raise InvalidStateTransitionError(
                f"No se permite la transición desde '{task.status}' hacia '{new_status}' en este incremento"
            )

        old_status = task.status
        task.status = new_status
        db.session.commit()

        # Auditoría obligatoria (Principio VIII)
        AuditService.log_event(
            actor_id=user_id,
            action="STATUS_CHANGED",
            entity_id=task.id,
            details={"previous_status": old_status, "current_status": new_status},
        )
        db.session.commit()

        return task

    @classmethod
    def update_task_details(
        cls,
        user_id: int,
        task_id: int,
        title: str,
        description: str = None,
        due_date: date = None,
    ) -> Task:
        """Actualiza los campos informativos de una tarea existente propia."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)

        if not title or not title.strip():
            raise TaskValidationError("El título de la tarea es obligatorio y no puede estar vacío")

        clean_title = title.strip()
        if len(clean_title) > 150:
            raise TaskValidationError("El título no puede exceder 150 caracteres")

        task.title = clean_title
        task.description = description.strip() if description else None
        task.due_date = due_date
        db.session.commit()

        # Auditoría obligatoria (Principio VIII)
        AuditService.log_event(
            actor_id=user_id,
            action="TASK_UPDATED",
            entity_id=task.id,
            details={"title": clean_title},
        )
        db.session.commit()

        return task

    @classmethod
    def delete_task(cls, user_id: int, task_id: int) -> Task:
        """Elimina lógicamente (soft delete) una tarea propia, preservando su historial."""
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            raise TaskNotFoundError("Tarea no encontrada")

        if task.is_deleted:
            raise TaskAlreadyDeletedError("La tarea ya fue eliminada previamente")

        task.is_deleted = True
        task.deleted_at = datetime.now(timezone.utc)
        db.session.commit()

        # Auditoría obligatoria (Principio VIII)
        AuditService.log_event(
            actor_id=user_id,
            action="TASK_DELETED",
            entity_id=task.id,
            details={"title": task.title},
        )
        db.session.commit()

        return task

    @classmethod
    def reopen_task(cls, user_id: int, task_id: int) -> Task:
        """Reabre una tarea completada, devolviéndola al estado 'pending' (HU-06)."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)

        if task.status != "completed":
            raise InvalidTaskStateTransitionError(
                "Solo se pueden reabrir tareas que se encuentren en estado 'completada'"
            )

        previous_status = task.status
        task.status = "pending"
        db.session.commit()

        # Auditoría obligatoria (Principio VIII) con evento diferenciado de STATUS_CHANGED
        AuditService.log_event(
            actor_id=user_id,
            action="TASK_REOPENED",
            entity_id=task.id,
            details={"previous_status": previous_status, "current_status": "pending"},
        )
        db.session.commit()

        return task
