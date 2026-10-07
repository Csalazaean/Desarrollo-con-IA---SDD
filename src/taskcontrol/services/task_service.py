from datetime import date, datetime, timezone
from sqlalchemy import case, or_
from src.taskcontrol.extensions import db
from src.taskcontrol.models.task import Task
from src.taskcontrol.models.user import User
from src.taskcontrol.services.audit_service import AuditService
from src.taskcontrol.services.category_service import CategoryService
from src.taskcontrol.services.notification_service import NotificationService


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


class InvalidPriorityError(Exception):
    """Valor de prioridad fuera del conjunto permitido (high, medium, low)."""
    pass


class AssigneeNotFoundError(Exception):
    """El correo indicado no corresponde a ningún usuario registrado."""
    pass


class TaskService:
    """Lógica de negocio del ciclo de vida y gestión de tareas (Principio II)."""

    VALID_TRANSITIONS = {
        "pending": {"in_progress", "completed"},
        "in_progress": {"pending", "completed"},
        "completed": set(),  # Bloqueada la reapertura en este incremento
    }

    VALID_PRIORITIES = {"high", "medium", "low"}

    @classmethod
    def backfill_manual_order(cls):
        """Asigna manual_order secuencial por usuario siguiendo created_at descendente
        (mismo orden que ya se lista por defecto), para tareas que aún no tienen uno
        asignado explícitamente. Invocado desde la migración (Principio VI) y reutilizable
        en pruebas (ver research.md §5)."""
        user_ids = [row[0] for row in db.session.query(Task.user_id).distinct().all()]
        for user_id in user_ids:
            tasks = (
                Task.query.filter_by(user_id=user_id)
                .order_by(Task.created_at.desc())
                .all()
            )
            for index, task in enumerate(tasks):
                task.manual_order = index
        db.session.commit()

    @classmethod
    def create_task(
        cls,
        user_id: int,
        title: str,
        description: str = None,
        due_date: date = None,
        priority: str = "medium",
    ) -> Task:
        """Crea una nueva tarea para el usuario y audita el evento."""
        if not title or not title.strip():
            raise TaskValidationError("El título de la tarea es obligatorio y no puede estar vacío")

        clean_title = title.strip()
        if len(clean_title) > 150:
            raise TaskValidationError("El título no puede exceder 150 caracteres")

        if priority not in cls.VALID_PRIORITIES:
            raise InvalidPriorityError(
                f"Prioridad inválida '{priority}'; valores permitidos: {sorted(cls.VALID_PRIORITIES)}"
            )

        task = Task(
            user_id=user_id,
            title=clean_title,
            description=description.strip() if description else None,
            due_date=due_date,
            status="pending",
            priority=priority,
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
    def get_user_tasks(
        cls, user_id: int, status: str = None, sort: str = None, category_id=None, view: str = "all"
    ):
        """Lista las tareas del usuario con filtrado por rol (creador/asignatario), estado, categoría y orden."""
        query = Task.query.filter_by(is_deleted=False)
        if view == "created":
            query = query.filter(Task.user_id == user_id)
        elif view == "assigned":
            query = query.filter(Task.assigned_to_id == user_id)
        else:  # 'all' (default): creador o asignatario
            query = query.filter(or_(Task.user_id == user_id, Task.assigned_to_id == user_id))

        if status in {"pending", "in_progress", "completed"}:
            query = query.filter_by(status=status)

        if category_id == "none":
            query = query.filter(Task.category_id.is_(None))
        elif category_id is not None:
            query = query.filter_by(category_id=int(category_id))

        if sort in {"priority_desc", "priority_asc"}:
            high_rank, low_rank = (1, 3) if sort == "priority_desc" else (3, 1)
            priority_order = case(
                (Task.priority == "high", high_rank),
                (Task.priority == "medium", 2),
                (Task.priority == "low", low_rank),
                else_=4,
            )
            # Desempate por due_date ascendente, nulos al final (ver spec Clarifications Q2)
            query = query.order_by(
                priority_order.asc(), Task.due_date.is_(None), Task.due_date.asc()
            )
        elif sort == "due_date":
            query = query.order_by(Task.due_date.is_(None), Task.due_date.asc())
        elif sort == "manual":
            query = query.order_by(Task.manual_order.asc())
        else:
            query = query.order_by(Task.created_at.desc())

        return query.all()

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
    def _get_task_for_creator_or_assignee(cls, user_id: int, task_id: int) -> Task:
        """Obtiene una tarea activa autorizando al creador O al asignatario (hallazgo E1 de /speckit-analyze:
        el asignatario únicamente puede cambiar el estado, nunca editar/eliminar/repriorizar/reasignar)."""
        task = Task.query.filter(
            Task.id == task_id,
            Task.is_deleted.is_(False),
            or_(Task.user_id == user_id, Task.assigned_to_id == user_id),
        ).first()
        if not task:
            raise TaskNotFoundError("Tarea no encontrada")
        return task

    @classmethod
    def update_task_status(cls, user_id: int, task_id: int, new_status: str) -> Task:
        """Aplica una transición de estado a la tarea; autoriza al creador o al asignatario (HU-10)."""
        task = cls._get_task_for_creator_or_assignee(user_id=user_id, task_id=task_id)

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
    def update_task_priority(cls, user_id: int, task_id: int, priority: str) -> Task:
        """Cambia la prioridad de una tarea propia (HU-07)."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)

        if priority not in cls.VALID_PRIORITIES:
            raise InvalidPriorityError(
                f"Prioridad inválida '{priority}'; valores permitidos: {sorted(cls.VALID_PRIORITIES)}"
            )

        old_priority = task.priority
        task.priority = priority
        db.session.commit()

        # Auditoría obligatoria (Principio VIII)
        AuditService.log_event(
            actor_id=user_id,
            action="TASK_UPDATED",
            entity_id=task.id,
            details={"previous_priority": old_priority, "current_priority": priority},
        )
        db.session.commit()

        return task

    @classmethod
    def assign_category(cls, user_id: int, task_id: int, category_id) -> Task:
        """Asigna (o desasigna con category_id=None) una categoría propia a una tarea (HU-08)."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)

        if category_id is not None:
            # Verifica propiedad de la categoría (Cero IDOR); CategoryNotFoundError se propaga.
            CategoryService.get_category_by_id(user_id=user_id, category_id=category_id)

        task.category_id = category_id
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action="TASK_UPDATED",
            entity_id=task.id,
            details={"category_id": category_id},
        )
        db.session.commit()

        return task

    @classmethod
    def assign_task(cls, task_id: int, user_id: int, assigned_to_email: str) -> Task:
        """Asigna (o reasigna) una tarea propia a otro usuario por correo (HU-10)."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)

        clean_email = (assigned_to_email or "").strip().lower()
        assignee = User.query.filter_by(email=clean_email).first()
        if not assignee:
            raise AssigneeNotFoundError(
                "No existe un usuario registrado con ese correo electrónico"
            )

        task.assigned_to_id = assignee.id
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action="TASK_ASSIGNED",
            entity_id=task.id,
            details={"assigned_to_email": assignee.email},
        )
        db.session.commit()

        # Autoasignación: nunca se notifica (Edge Case)
        if assignee.id != user_id:
            NotificationService.create_notification(
                recipient_id=assignee.id, sender_id=user_id, task=task
            )

        return task

    @classmethod
    def unassign_task(cls, task_id: int, user_id: int) -> Task:
        """Retira la asignación de una tarea propia; nunca notifica (spec Clarifications Q2)."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)

        task.assigned_to_id = None
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action="TASK_UNASSIGNED",
            entity_id=task.id,
            details={},
        )
        db.session.commit()

        return task

    @classmethod
    def reorder_tasks(cls, user_id: int, task_ids: list) -> int:
        """Persiste el nuevo orden visual completo tras arrastrar y soltar (HU-16).

        Autoriza cada task_id como creador O asignatario (spec Clarifications Q3: reordenar
        una tarea asignada es una preferencia de vista personal, no una edición de la tarea).
        Si algún task_id no es válido, la operación completa se aborta sin persistir ningún
        cambio parcial (ver plan.md §4)."""
        tasks = [
            cls._get_task_for_creator_or_assignee(user_id=user_id, task_id=task_id)
            for task_id in task_ids
        ]

        for index, task in enumerate(tasks):
            task.manual_order = index
        db.session.commit()

        return len(tasks)

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
