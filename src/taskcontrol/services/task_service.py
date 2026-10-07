from datetime import date, datetime, timezone
from src.taskcontrol.extensions import db
from src.taskcontrol.models.audit import AuditLog
from src.taskcontrol.models.task import Task
from src.taskcontrol.models.user import User
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
    """Operación rechazada porque la tarea ya fue eliminada lógicamente."""
    pass


class NotTaskOwnerError(Exception):
    """El usuario existe y la tarea también, pero no es su creador.

    Se distingue de TaskNotFoundError porque el contrato exige 403 y no 404:
    lo que falta es permiso, no la tarea.
    """
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

    @classmethod
    def _validar_prioridad(cls, priority: str) -> str:
        """Valida el nivel de prioridad contra los valores permitidos (FR-001)."""
        if priority is None:
            return Task.DEFAULT_PRIORITY
        if priority not in Task.VALID_PRIORITIES:
            raise TaskValidationError(
                f"La prioridad debe ser una de: {', '.join(Task.VALID_PRIORITIES)}"
            )
        return priority

    @classmethod
    def create_task(
        cls,
        user_id: int,
        title: str,
        description: str = None,
        due_date: date = None,
        priority: str = None,
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
            priority=cls._validar_prioridad(priority),
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
        cls,
        user_id: int,
        status: str = None,
        include_deleted: bool = False,
        category_id=None,
        sort: str = None,
        scope: str = None,
    ):
        """Lista las tareas visibles para el usuario con filtros y orden opcionales.

        Desde el Incremento 4 el listado incluye tanto las tareas creadas por el
        usuario como las que le fueron asignadas (`scope='all'`, por defecto).
        Los filtros se aplican antes del orden, de modo que filtrar por estado y
        ordenar por prioridad se combinan sin pisarse.
        """
        if scope == "created":
            query = Task.query.filter(Task.user_id == user_id)
        elif scope == "assigned":
            query = Task.query.filter(Task.assigned_to_id == user_id)
        else:
            query = Task.query.filter(
                db.or_(Task.user_id == user_id, Task.assigned_to_id == user_id)
            )
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        if status in {"pending", "in_progress", "completed"}:
            query = query.filter_by(status=status)

        # `none` filtra las tareas sin categoría; un id filtra por esa categoría.
        if category_id == "none":
            query = query.filter(Task.category_id.is_(None))
        elif category_id is not None:
            try:
                query = query.filter(Task.category_id == int(category_id))
            except (TypeError, ValueError):
                pass

        # Ordenar por la columna de texto daría un orden alfabético ("high" < "low" <
        # "medium"), que no es la jerarquía pedida. Se traduce a su rango numérico.
        rank = db.case(Task.PRIORITY_RANK, value=Task.priority, else_=len(Task.PRIORITY_RANK))

        if sort == "priority_desc":
            return query.order_by(rank.asc(), Task.created_at.desc()).all()
        if sort == "priority_asc":
            return query.order_by(rank.desc(), Task.created_at.desc()).all()
        if sort == "due_date":
            return query.order_by(Task.due_date.is_(None), Task.due_date.asc()).all()

        # Orden por defecto: el orden personal del usuario (HU-16). El desempate por
        # created_at descendente mantiene el comportamiento anterior en las tareas
        # que aún comparten la posición 0, es decir, todas hasta que se arrastre una.
        return query.order_by(Task.position.asc(), Task.created_at.desc()).all()

    @classmethod
    def reorder_user_tasks(cls, user_id: int, task_ids: list) -> dict:
        """Persiste el orden personal del listado del usuario (HU-16).

        Los identificadores recibidos se filtran contra las tareas vigentes del
        usuario **antes** de escribir nada: una petición manipulada con tareas
        ajenas no altera ninguna de ellas, solo las reporta como ignoradas
        (FR-010, Principio VII).

        Los identificadores inexistentes o de tareas eliminadas se descartan en
        lugar de hacer fallar toda la operación.
        """
        ids_solicitados = [int(i) for i in task_ids]

        propias = {
            tarea.id: tarea
            for tarea in Task.query.filter(
                Task.user_id == user_id,
                Task.is_deleted.is_(False),
                Task.id.in_(ids_solicitados) if ids_solicitados else False,
            ).all()
        }

        posicion = 0
        ignorados = []
        for task_id in ids_solicitados:
            tarea = propias.get(task_id)
            if tarea is None:
                ignorados.append(task_id)
                continue
            tarea.position = posicion
            posicion += 1

        db.session.commit()

        return {"reordered_count": posicion, "ignored_ids": ignorados}

    @classmethod
    def get_task_by_id(cls, user_id: int, task_id: int, include_deleted: bool = False) -> Task:
        """Obtiene una tarea verificando la propiedad del usuario autenticado."""
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            raise TaskNotFoundError("Tarea no encontrada")
        if task.is_deleted and not include_deleted:
            raise TaskNotFoundError("Tarea no encontrada o eliminada")
        return task

    @classmethod
    def delete_task(cls, task_id: int, user_id: int) -> Task:
        """Elimina lógicamente una tarea del usuario (soft delete, Principio VI y VIII)."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id, include_deleted=True)
        if task.is_deleted:
            raise TaskAlreadyDeletedError("La tarea ya fue eliminada previamente")

        now_utc = datetime.now(timezone.utc)
        task.is_deleted = True
        task.deleted_at = now_utc
        db.session.commit()

        # Auditoría obligatoria (Principio VIII)
        AuditService.log_event(
            actor_id=user_id,
            action="TASK_DELETED",
            entity_id=task.id,
            details={"title": task.title, "deleted_at": now_utc.isoformat()},
        )
        db.session.commit()

        return task

    @classmethod
    def reopen_task(cls, task_id: int, user_id: int) -> Task:
        """Reabre una tarea completada devolviéndola al estado pending (HU-06)."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id, include_deleted=True)
        if task.is_deleted:
            raise TaskAlreadyDeletedError("No se puede reabrir una tarea eliminada")

        if task.status != "completed":
            raise InvalidStateTransitionError(
                "Solo se pueden reabrir tareas que se encuentren en estado 'completada'"
            )

        old_status = task.status
        task.status = "pending"
        db.session.commit()

        # Auditoría específica de reapertura (Principio VIII)
        AuditService.log_event(
            actor_id=user_id,
            action="TASK_REOPENED",
            entity_id=task.id,
            details={
                "previous_status": old_status,
                "new_status": "pending",
                "trigger": "user_reopen",
            },
        )
        db.session.commit()

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
    def assign_task_to_user(cls, task_id: int, actor_id: int, assignee_email: str) -> Task:
        """Asigna, reasigna o desasigna una tarea (HU-10).

        Todo ocurre en una sola transacción —validación, asignación, notificación y
        auditoría— para que no pueda quedar una tarea asignada de la que el
        destinatario nunca se entera (plan.md §4, FR-008).

        Un correo vacío retira la asignación (FR-003).
        """
        from src.taskcontrol.services.notification_service import NotificationService

        task = Task.query.filter_by(id=task_id).first()
        if not task or task.is_deleted:
            raise TaskNotFoundError("Tarea no encontrada")

        # Solo el creador decide quién ejecuta su tarea; un tercero recibe 403.
        if task.user_id != actor_id:
            raise NotTaskOwnerError("Solo el creador de la tarea puede asignarla")

        anterior = task.assigned_to_id

        if not assignee_email or not str(assignee_email).strip():
            task.assigned_to_id = None
            AuditService.log_event(
                actor_id=actor_id,
                action=AuditLog.ACTION_TASK_UNASSIGNED,
                entity_id=task.id,
                details={"previous_assignee_id": anterior},
            )
            db.session.commit()
            return task

        # El destinatario se resuelve contra la base de datos: un selector del
        # frontend no prueba nada, la petición puede fabricarse a mano (FR-002).
        email_limpio = str(assignee_email).strip().lower()
        destinatario = User.query.filter_by(email=email_limpio).first()
        if not destinatario:
            raise AssigneeNotFoundError(
                f"No existe un usuario registrado con el correo '{email_limpio}'"
            )

        task.assigned_to_id = destinatario.id

        # Autoasignarse no genera notificación: sería ruido para el propio actor.
        notificada = destinatario.id != actor_id
        if notificada:
            NotificationService.create_assignment_notification(
                recipient_id=destinatario.id, sender_id=actor_id, task=task
            )

        AuditService.log_event(
            actor_id=actor_id,
            action=AuditLog.ACTION_TASK_ASSIGNED,
            entity_id=task.id,
            details={
                "previous_assignee_id": anterior,
                "assigned_to_id": destinatario.id,
                "assignee_email": destinatario.email,
                "notification_created": notificada,
            },
        )
        db.session.commit()

        return task

    @classmethod
    def update_task_priority(cls, task_id: int, user_id: int, priority: str) -> Task:
        """Cambia el nivel de prioridad de una tarea activa propia (HU-07, FR-003)."""
        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)
        nueva = cls._validar_prioridad(priority)

        anterior = task.priority
        task.priority = nueva
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action="TASK_UPDATED",
            entity_id=task.id,
            details={"previous_priority": anterior, "current_priority": nueva},
        )
        db.session.commit()

        return task

    @classmethod
    def assign_category_to_task(cls, task_id: int, user_id: int, category_id) -> Task:
        """Asocia o desvincula una categoría de una tarea propia (HU-08, FR-008).

        Verifica en el backend que tanto la tarea como la categoría pertenezcan al
        usuario autenticado: sin esta comprobación bastaría con manipular el id del
        formulario para enlazar la tarea a una categoría ajena (FR-010, Principio VII).
        """
        # Importación local: category_service importa este módulo, y a nivel superior
        # el ciclo rompería la carga.
        from src.taskcontrol.services.category_service import CategoryService

        task = cls.get_task_by_id(user_id=user_id, task_id=task_id)

        if category_id is None or category_id == "":
            task.category_id = None
        else:
            categoria = CategoryService.get_category_by_id(
                category_id=int(category_id), user_id=user_id
            )
            task.category_id = categoria.id

        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action="TASK_UPDATED",
            entity_id=task.id,
            details={"category_id": task.category_id},
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
