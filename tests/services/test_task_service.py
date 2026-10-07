from datetime import date
import pytest
from src.taskcontrol.extensions import db
from src.taskcontrol.services.user_service import UserService
from src.taskcontrol.services.task_service import (
    TaskService,
    TaskValidationError,
    TaskNotFoundError,
    InvalidStateTransitionError,
    TaskAlreadyDeletedError,
    InvalidTaskStateTransitionError,
    InvalidPriorityError,
    AssigneeNotFoundError,
)
from src.taskcontrol.models.audit import AuditLog


@pytest.fixture
def test_user_id(app):
    with app.app_context():
        user = UserService.register_user("taskowner@example.com", "Password123!")
        return user.id


@pytest.fixture
def second_user_id(app):
    with app.app_context():
        user = UserService.register_user("seconduser@example.com", "Password123!")
        return user.id


# --- US3: Creación de Tareas (HU-01) ---

def test_create_task_success(app, test_user_id):
    """Verifica la creación exitosa de una tarea con estado pending y log de auditoría."""
    with app.app_context():
        task = TaskService.create_task(
            user_id=test_user_id,
            title="Mi primera tarea",
            description="Descripción opcional",
            due_date=date(2026, 10, 15),
        )
        assert task.id is not None
        assert task.title == "Mi primera tarea"
        assert task.description == "Descripción opcional"
        assert task.status == "pending"
        assert task.user_id == test_user_id

        # Verificar generación de auditoría (Principio VIII)
        audit = AuditLog.query.filter_by(
            action="TASK_CREATED", entity_id=task.id
        ).first()
        assert audit is not None
        assert audit.actor_id == test_user_id


def test_create_task_empty_title_fails(app, test_user_id):
    """Verifica que se rechace un título vacío o con solo espacios."""
    with app.app_context():
        with pytest.raises(TaskValidationError):
            TaskService.create_task(user_id=test_user_id, title="   ")


def test_create_task_title_too_long(app, test_user_id):
    """Verifica que se rechace un título que exceda 150 caracteres."""
    with app.app_context():
        with pytest.raises(TaskValidationError):
            TaskService.create_task(user_id=test_user_id, title="A" * 151)


# --- US4: Listado y Filtrado de Tareas (HU-02) ---

def test_get_user_tasks_isolation(app, test_user_id, second_user_id):
    """Verifica aislamiento estricto entre usuarios (Principio VII / Cero IDOR)."""
    with app.app_context():
        TaskService.create_task(user_id=test_user_id, title="Tarea de Usuario 1")
        TaskService.create_task(user_id=second_user_id, title="Tarea de Usuario 2")

        tasks_user1 = TaskService.get_user_tasks(user_id=test_user_id)
        assert len(tasks_user1) == 1
        assert tasks_user1[0].title == "Tarea de Usuario 1"

        tasks_user2 = TaskService.get_user_tasks(user_id=second_user_id)
        assert len(tasks_user2) == 1
        assert tasks_user2[0].title == "Tarea de Usuario 2"


def test_filter_tasks_by_status(app, test_user_id):
    """Verifica que el filtrado por estado retorne únicamente las tareas coincidentes."""
    with app.app_context():
        t1 = TaskService.create_task(user_id=test_user_id, title="Tarea 1")
        t2 = TaskService.create_task(user_id=test_user_id, title="Tarea 2")
        TaskService.update_task_status(
            user_id=test_user_id, task_id=t2.id, new_status="completed"
        )

        pending = TaskService.get_user_tasks(user_id=test_user_id, status="pending")
        completed = TaskService.get_user_tasks(user_id=test_user_id, status="completed")

        assert len(pending) == 1
        assert pending[0].id == t1.id
        assert len(completed) == 1
        assert completed[0].id == t2.id


# --- US5: Cambio de Estado de Tareas (HU-03) ---

def test_task_state_transitions(app, test_user_id):
    """Verifica transiciones válidas y emisión de log de auditoría STATUS_CHANGED."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Flujo")

        # pending -> in_progress
        task = TaskService.update_task_status(
            user_id=test_user_id, task_id=task.id, new_status="in_progress"
        )
        assert task.status == "in_progress"

        # in_progress -> completed
        task = TaskService.update_task_status(
            user_id=test_user_id, task_id=task.id, new_status="completed"
        )
        assert task.status == "completed"

        # Verificar auditoría
        audits = AuditLog.query.filter_by(
            action="STATUS_CHANGED", entity_id=task.id
        ).all()
        assert len(audits) == 2


def test_reopening_completed_task_fails(app, test_user_id):
    """Verifica que la reapertura (completed -> pending) esté explícitamente bloqueada en este incremento."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Finalizada")
        TaskService.update_task_status(
            user_id=test_user_id, task_id=task.id, new_status="completed"
        )

        with pytest.raises(InvalidStateTransitionError):
            TaskService.update_task_status(
                user_id=test_user_id, task_id=task.id, new_status="pending"
            )


# --- US6: Edición de Tareas (HU-04) ---

def test_update_task_details_success(app, test_user_id):
    """Verifica edición de campos informativos y registro en auditoría."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Título Inicial")
        updated = TaskService.update_task_details(
            user_id=test_user_id,
            task_id=task.id,
            title="Título Modificado",
            description="Nueva descripción",
            due_date=date(2026, 11, 1),
        )
        assert updated.title == "Título Modificado"
        assert updated.description == "Nueva descripción"
        assert updated.due_date == date(2026, 11, 1)

        audit = AuditLog.query.filter_by(
            action="TASK_UPDATED", entity_id=task.id
        ).first()
        assert audit is not None


def test_update_task_empty_title_fails(app, test_user_id):
    """Verifica que editar con título vacío sea rechazado."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Título Válido")
        with pytest.raises(TaskValidationError):
            TaskService.update_task_details(
                user_id=test_user_id, task_id=task.id, title=""
            )


def test_update_task_unauthorized_user(app, test_user_id, second_user_id):
    """Verifica que un usuario no pueda editar tareas de otro usuario (Cero IDOR)."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea de User 1")
        with pytest.raises(TaskNotFoundError):
            TaskService.update_task_details(
                user_id=second_user_id, task_id=task.id, title="Hack intento"
            )


# --- US1 (Incremento 2): Eliminación Lógica de Tareas (HU-05) ---

def test_soft_delete_task_marks_deleted_and_sets_timestamp(app, test_user_id):
    """Verifica que delete_task marque is_deleted=True y registre deleted_at."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea a eliminar")
        deleted = TaskService.delete_task(user_id=test_user_id, task_id=task.id)

        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None


def test_soft_delete_preserves_task_in_database_and_audit_history(app, test_user_id):
    """Verifica que la tarea siga existiendo en la tabla y que se registre el evento TASK_DELETED."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea con historial")
        TaskService.delete_task(user_id=test_user_id, task_id=task.id)

        from src.taskcontrol.extensions import db
        from src.taskcontrol.models.task import Task

        persisted = db.session.get(Task, task.id)
        assert persisted is not None
        assert persisted.is_deleted is True

        audit = AuditLog.query.filter_by(action="TASK_DELETED", entity_id=task.id).first()
        assert audit is not None
        assert audit.actor_id == test_user_id


def test_deleted_task_excluded_from_default_listing(app, test_user_id):
    """Verifica que una tarea eliminada no aparezca en el listado por defecto."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Visible")
        to_delete = TaskService.create_task(user_id=test_user_id, title="Tarea Oculta")
        TaskService.delete_task(user_id=test_user_id, task_id=to_delete.id)

        tasks = TaskService.get_user_tasks(user_id=test_user_id)
        titles = [t.title for t in tasks]
        assert "Tarea Visible" in titles
        assert "Tarea Oculta" not in titles


def test_cannot_delete_already_deleted_task(app, test_user_id):
    """Verifica que no se permita eliminar dos veces la misma tarea."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Doble Borrado")
        TaskService.delete_task(user_id=test_user_id, task_id=task.id)

        with pytest.raises(TaskAlreadyDeletedError):
            TaskService.delete_task(user_id=test_user_id, task_id=task.id)


def test_cannot_edit_deleted_task(app, test_user_id):
    """Verifica que una tarea eliminada no pueda editarse."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea a Proteger")
        TaskService.delete_task(user_id=test_user_id, task_id=task.id)

        with pytest.raises(TaskNotFoundError):
            TaskService.update_task_details(
                user_id=test_user_id, task_id=task.id, title="Intento de edición"
            )


# --- US2 (Incremento 2): Reapertura de Tareas Completadas (HU-06) ---

def test_reopen_completed_task_success(app, test_user_id):
    """Verifica que una tarea completada vuelva al estado pending al reabrirla."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea a Reabrir")
        TaskService.update_task_status(
            user_id=test_user_id, task_id=task.id, new_status="completed"
        )

        reopened = TaskService.reopen_task(user_id=test_user_id, task_id=task.id)
        assert reopened.status == "pending"


def test_reopen_task_generates_specific_task_reopened_audit_log(app, test_user_id):
    """Verifica que la reapertura registre el evento TASK_REOPENED (distinto de STATUS_CHANGED)."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Auditada")
        TaskService.update_task_status(
            user_id=test_user_id, task_id=task.id, new_status="completed"
        )
        TaskService.reopen_task(user_id=test_user_id, task_id=task.id)

        audit = AuditLog.query.filter_by(action="TASK_REOPENED", entity_id=task.id).first()
        assert audit is not None
        assert audit.actor_id == test_user_id


def test_cannot_reopen_non_completed_or_deleted_task(app, test_user_id):
    """Verifica que no se pueda reabrir una tarea pendiente, en progreso o eliminada."""
    with app.app_context():
        pending_task = TaskService.create_task(user_id=test_user_id, title="Tarea Pendiente")
        with pytest.raises(InvalidTaskStateTransitionError):
            TaskService.reopen_task(user_id=test_user_id, task_id=pending_task.id)

        deleted_task = TaskService.create_task(user_id=test_user_id, title="Tarea Eliminada")
        TaskService.update_task_status(
            user_id=test_user_id, task_id=deleted_task.id, new_status="completed"
        )
        TaskService.delete_task(user_id=test_user_id, task_id=deleted_task.id)
        with pytest.raises(TaskNotFoundError):
            TaskService.reopen_task(user_id=test_user_id, task_id=deleted_task.id)


# --- US1 (Incremento 3): Prioridad de Tareas y Ordenamiento (HU-07) ---

def test_task_priority_default_is_medium(app, test_user_id):
    """Verifica que una tarea creada sin prioridad explícita quede en 'medium'."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Sin Prioridad")
        assert task.priority == "medium"


def test_create_task_with_explicit_priority(app, test_user_id):
    """Verifica que se pueda fijar la prioridad en el mismo paso de creación."""
    with app.app_context():
        task = TaskService.create_task(
            user_id=test_user_id, title="Tarea Urgente", priority="high"
        )
        assert task.priority == "high"


def test_create_task_invalid_priority_rejected(app, test_user_id):
    """Verifica que un valor de prioridad fuera del conjunto permitido sea rechazado."""
    with app.app_context():
        with pytest.raises(InvalidPriorityError):
            TaskService.create_task(
                user_id=test_user_id, title="Tarea Inválida", priority="urgente"
            )


def test_update_task_priority_success(app, test_user_id):
    """Verifica que se pueda cambiar la prioridad de una tarea propia y que quede auditado."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea a Repriorizar")
        updated = TaskService.update_task_priority(
            user_id=test_user_id, task_id=task.id, priority="low"
        )
        assert updated.priority == "low"

        audit = AuditLog.query.filter_by(action="TASK_UPDATED", entity_id=task.id).first()
        assert audit is not None


def test_update_task_priority_invalid_value_rejected(app, test_user_id):
    """Verifica que update_task_priority rechace valores fuera del conjunto permitido."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Protegida")
        with pytest.raises(InvalidPriorityError):
            TaskService.update_task_priority(
                user_id=test_user_id, task_id=task.id, priority="critica"
            )


def test_cannot_update_priority_of_other_users_task(app, test_user_id, second_user_id):
    """Verifica aislamiento por usuario (Cero IDOR) al cambiar prioridad."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea de User 1")
        with pytest.raises(TaskNotFoundError):
            TaskService.update_task_priority(
                user_id=second_user_id, task_id=task.id, priority="high"
            )


def test_tasks_sorted_by_priority_descending_high_medium_low(app, test_user_id):
    """Verifica el orden jerárquico alta -> media -> baja al pedir sort='priority_desc'."""
    with app.app_context():
        TaskService.create_task(user_id=test_user_id, title="Baja", priority="low")
        TaskService.create_task(user_id=test_user_id, title="Alta", priority="high")
        TaskService.create_task(user_id=test_user_id, title="Media", priority="medium")

        tasks = TaskService.get_user_tasks(user_id=test_user_id, sort="priority_desc")
        assert [t.priority for t in tasks] == ["high", "medium", "low"]


def test_same_priority_tasks_sorted_by_due_date_ascending_nulls_last(app, test_user_id):
    """Verifica el desempate por due_date ascendente, con nulos al final del grupo (clarify Q2)."""
    with app.app_context():
        from datetime import date as date_cls

        t_no_date = TaskService.create_task(
            user_id=test_user_id, title="Alta Sin Fecha", priority="high"
        )
        t_later = TaskService.create_task(
            user_id=test_user_id,
            title="Alta Fecha Lejana",
            priority="high",
            due_date=date_cls(2026, 12, 31),
        )
        t_sooner = TaskService.create_task(
            user_id=test_user_id,
            title="Alta Fecha Próxima",
            priority="high",
            due_date=date_cls(2026, 11, 1),
        )

        tasks = TaskService.get_user_tasks(user_id=test_user_id, sort="priority_desc")
        assert [t.id for t in tasks] == [t_sooner.id, t_later.id, t_no_date.id]


def test_tasks_sorted_by_priority_respects_status_filters(app, test_user_id):
    """Verifica que el filtro por estado se aplique junto con el ordenamiento por prioridad."""
    with app.app_context():
        t1 = TaskService.create_task(user_id=test_user_id, title="Pendiente Alta", priority="high")
        t2 = TaskService.create_task(user_id=test_user_id, title="Completada Alta", priority="high")
        TaskService.update_task_status(user_id=test_user_id, task_id=t2.id, new_status="completed")

        tasks = TaskService.get_user_tasks(
            user_id=test_user_id, status="pending", sort="priority_desc"
        )
        assert [t.id for t in tasks] == [t1.id]


# --- US3 (Incremento 3): Indicación Confiable de Tareas Vencidas (HU-09) ---

def test_task_overdue_when_due_date_past_and_not_completed(app, test_user_id):
    """Verifica que una tarea pendiente con fecha límite pasada se marque is_overdue=True."""
    with app.app_context():
        from datetime import date, timedelta

        yesterday = date.today() - timedelta(days=1)
        task = TaskService.create_task(
            user_id=test_user_id, title="Tarea Vencida", due_date=yesterday
        )
        assert task.is_overdue is True


def test_completed_task_never_marked_overdue_even_if_due_date_past(app, test_user_id):
    """Verifica que una tarea completada NUNCA se marque como vencida, pase lo que pase con due_date."""
    with app.app_context():
        from datetime import date, timedelta

        yesterday = date.today() - timedelta(days=1)
        task = TaskService.create_task(
            user_id=test_user_id, title="Tarea Completada Vencida", due_date=yesterday
        )
        TaskService.update_task_status(user_id=test_user_id, task_id=task.id, new_status="completed")
        assert task.is_overdue is False


def test_deleted_task_never_marked_overdue(app, test_user_id):
    """Verifica que una tarea eliminada lógicamente NUNCA se marque como vencida."""
    with app.app_context():
        from datetime import date, timedelta

        yesterday = date.today() - timedelta(days=1)
        task = TaskService.create_task(
            user_id=test_user_id, title="Tarea Eliminada Vencida", due_date=yesterday
        )
        TaskService.delete_task(user_id=test_user_id, task_id=task.id)
        assert task.is_overdue is False


def test_task_without_due_date_never_overdue(app, test_user_id):
    """Verifica que una tarea sin fecha límite nunca se marque como vencida."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Sin Fecha")
        assert task.is_overdue is False


def test_task_due_today_not_overdue_until_day_ends(app, test_user_id):
    """Verifica que una tarea con fecha límite hoy (UTC) no se marque como vencida durante el día en curso."""
    with app.app_context():
        from datetime import datetime, timezone

        today_utc = datetime.now(timezone.utc).date()
        task = TaskService.create_task(
            user_id=test_user_id, title="Tarea Hoy", due_date=today_utc
        )
        assert task.is_overdue is False


# --- US1 (Incremento 4): Asignación Segura de Tareas entre Usuarios (HU-10) ---

def test_assign_task_success_creates_notification_and_audit_log(app, test_user_id, second_user_id):
    """Verifica asignación exitosa: audita TASK_ASSIGNED y genera una notificación para el asignatario."""
    with app.app_context():
        from src.taskcontrol.models.notification import Notification
        from src.taskcontrol.models.user import User

        second_user = db.session.get(User, second_user_id)
        task = TaskService.create_task(user_id=test_user_id, title="Tarea a Delegar")

        assigned = TaskService.assign_task(
            task_id=task.id, user_id=test_user_id, assigned_to_email=second_user.email
        )
        assert assigned.assigned_to_id == second_user_id

        audit = AuditLog.query.filter_by(action="TASK_ASSIGNED", entity_id=task.id).first()
        assert audit is not None
        assert audit.actor_id == test_user_id

        notification = Notification.query.filter_by(recipient_id=second_user_id).first()
        assert notification is not None
        assert notification.sender_id == test_user_id
        assert notification.task_id == task.id


def test_assign_task_to_nonexistent_email_rejected(app, test_user_id):
    """Verifica que asignar a un correo no registrado se rechace (FR-002)."""
    with app.app_context():
        task = TaskService.create_task(user_id=test_user_id, title="Tarea")
        with pytest.raises(AssigneeNotFoundError):
            TaskService.assign_task(
                task_id=task.id, user_id=test_user_id, assigned_to_email="noexiste@example.com"
            )


def test_only_creator_can_assign_task(app, test_user_id, second_user_id):
    """Verifica que un usuario no creador no pueda asignar la tarea de otro (Cero IDOR)."""
    with app.app_context():
        from src.taskcontrol.models.user import User

        second_user = db.session.get(User, second_user_id)
        task = TaskService.create_task(user_id=test_user_id, title="Tarea de User 1")
        with pytest.raises(TaskNotFoundError):
            TaskService.assign_task(
                task_id=task.id, user_id=second_user_id, assigned_to_email=second_user.email
            )


def test_self_assignment_succeeds_without_notification(app, test_user_id):
    """Verifica que la autoasignación funcione pero no genere notificación (Edge Case)."""
    with app.app_context():
        from src.taskcontrol.models.notification import Notification
        from src.taskcontrol.models.user import User

        owner = db.session.get(User, test_user_id)
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Propia")

        assigned = TaskService.assign_task(
            task_id=task.id, user_id=test_user_id, assigned_to_email=owner.email
        )
        assert assigned.assigned_to_id == test_user_id
        assert Notification.query.filter_by(recipient_id=test_user_id).count() == 0


def test_unassign_task_success_no_notification_generated(app, test_user_id, second_user_id):
    """Verifica que desasignar retire assigned_to_id, audite TASK_UNASSIGNED, y nunca notifique (clarify Q2)."""
    with app.app_context():
        from src.taskcontrol.models.notification import Notification
        from src.taskcontrol.models.user import User

        second_user = db.session.get(User, second_user_id)
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Asignada")
        TaskService.assign_task(task_id=task.id, user_id=test_user_id, assigned_to_email=second_user.email)
        Notification.query.delete()  # limpiar la notificación de la asignación inicial

        unassigned = TaskService.unassign_task(task_id=task.id, user_id=test_user_id)
        assert unassigned.assigned_to_id is None

        audit = AuditLog.query.filter_by(action="TASK_UNASSIGNED", entity_id=task.id).first()
        assert audit is not None
        assert Notification.query.count() == 0


def test_assigned_task_visible_in_assignee_task_list(app, test_user_id, second_user_id):
    """Verifica que la tarea asignada aparezca en el listado del asignatario (SC-002)."""
    with app.app_context():
        from src.taskcontrol.models.user import User

        second_user = db.session.get(User, second_user_id)
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Visible para B")
        TaskService.assign_task(task_id=task.id, user_id=test_user_id, assigned_to_email=second_user.email)

        tasks_b = TaskService.get_user_tasks(user_id=second_user_id)
        assert any(t.id == task.id for t in tasks_b)


def test_get_user_tasks_view_created_vs_assigned_vs_all(app, test_user_id, second_user_id):
    """Verifica el filtro view='created'/'assigned'/'all' del listado."""
    with app.app_context():
        from src.taskcontrol.models.user import User

        second_user = db.session.get(User, second_user_id)
        created_task = TaskService.create_task(user_id=test_user_id, title="Creada por mí")
        assigned_task = TaskService.create_task(user_id=second_user_id, title="Asignada a mí")
        TaskService.assign_task(
            task_id=assigned_task.id, user_id=second_user_id, assigned_to_email=(
                db.session.get(User, test_user_id).email
            )
        )

        created = TaskService.get_user_tasks(user_id=test_user_id, view="created")
        assigned = TaskService.get_user_tasks(user_id=test_user_id, view="assigned")
        all_tasks = TaskService.get_user_tasks(user_id=test_user_id, view="all")

        assert [t.id for t in created] == [created_task.id]
        assert [t.id for t in assigned] == [assigned_task.id]
        assert {t.id for t in all_tasks} == {created_task.id, assigned_task.id}


def test_reassignment_notifies_new_assignee_and_old_assignee_loses_access(app, test_user_id, second_user_id):
    """Verifica reasignación sucesiva: nueva notificación, y el asignatario anterior deja de verla (Edge Case)."""
    with app.app_context():
        from src.taskcontrol.models.notification import Notification
        from src.taskcontrol.models.user import User

        third_user = UserService.register_user("thirduser@example.com", "Password123!")
        second_user = db.session.get(User, second_user_id)

        task = TaskService.create_task(user_id=test_user_id, title="Tarea Reasignada")
        TaskService.assign_task(task_id=task.id, user_id=test_user_id, assigned_to_email=second_user.email)
        TaskService.assign_task(task_id=task.id, user_id=test_user_id, assigned_to_email=third_user.email)

        assert Notification.query.filter_by(recipient_id=third_user.id).count() == 1

        tasks_b = TaskService.get_user_tasks(user_id=second_user_id, view="assigned")
        assert task.id not in [t.id for t in tasks_b]


def test_assignee_can_update_task_status(app, test_user_id, second_user_id):
    """Verifica que el asignatario pueda cambiar el estado de la tarea delegada (hallazgo E1 de /speckit-analyze)."""
    with app.app_context():
        from src.taskcontrol.models.user import User

        second_user = db.session.get(User, second_user_id)
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Delegada")
        TaskService.assign_task(task_id=task.id, user_id=test_user_id, assigned_to_email=second_user.email)

        updated = TaskService.update_task_status(
            user_id=second_user_id, task_id=task.id, new_status="in_progress"
        )
        assert updated.status == "in_progress"


def test_assignee_cannot_edit_delete_priority_category_or_reassign_task(app, test_user_id, second_user_id):
    """Verifica que el asignatario NO pueda editar, eliminar, repriorizar, recategorizar ni reasignar (hallazgo E1)."""
    with app.app_context():
        from src.taskcontrol.models.user import User

        second_user = db.session.get(User, second_user_id)
        task = TaskService.create_task(user_id=test_user_id, title="Tarea Protegida")
        TaskService.assign_task(task_id=task.id, user_id=test_user_id, assigned_to_email=second_user.email)

        with pytest.raises(TaskNotFoundError):
            TaskService.update_task_details(user_id=second_user_id, task_id=task.id, title="Hackeada")
        with pytest.raises(TaskNotFoundError):
            TaskService.update_task_priority(user_id=second_user_id, task_id=task.id, priority="high")
        with pytest.raises(TaskNotFoundError):
            TaskService.delete_task(user_id=second_user_id, task_id=task.id)
        with pytest.raises(TaskNotFoundError):
            TaskService.assign_task(
                task_id=task.id, user_id=second_user_id, assigned_to_email=second_user.email
            )


# --- US2 (Incremento 5): Reordenar Tareas Arrastrándolas (HU-16) ---

def test_reorder_tasks_persists_new_order_for_all_affected_tasks(app, test_user_id):
    """Verifica que reorder_tasks asigne manual_order secuencial según la posición enviada."""
    with app.app_context():
        t1 = TaskService.create_task(user_id=test_user_id, title="Tarea 1")
        t2 = TaskService.create_task(user_id=test_user_id, title="Tarea 2")
        t3 = TaskService.create_task(user_id=test_user_id, title="Tarea 3")

        TaskService.reorder_tasks(user_id=test_user_id, task_ids=[t3.id, t1.id, t2.id])

        assert t3.manual_order == 0
        assert t1.manual_order == 1
        assert t2.manual_order == 2


def test_reorder_rejects_task_not_owned_or_assigned(app, test_user_id, second_user_id):
    """Verifica que reordenar una tarea ajena (ni creada ni asignada) sea rechazado (BLOQUEANTE)."""
    with app.app_context():
        own_task = TaskService.create_task(user_id=test_user_id, title="Propia")
        foreign_task = TaskService.create_task(user_id=second_user_id, title="Ajena")

        with pytest.raises(TaskNotFoundError):
            TaskService.reorder_tasks(
                user_id=test_user_id, task_ids=[own_task.id, foreign_task.id]
            )


def test_reorder_is_atomic_all_or_nothing(app, test_user_id, second_user_id):
    """Verifica que un task_id inválido en el lote no aplique ningún cambio parcial (BLOQUEANTE)."""
    with app.app_context():
        t1 = TaskService.create_task(user_id=test_user_id, title="Tarea 1")
        t2 = TaskService.create_task(user_id=test_user_id, title="Tarea 2")
        foreign_task = TaskService.create_task(user_id=second_user_id, title="Ajena")
        original_order_t1, original_order_t2 = t1.manual_order, t2.manual_order

        with pytest.raises(TaskNotFoundError):
            TaskService.reorder_tasks(
                user_id=test_user_id, task_ids=[t2.id, foreign_task.id, t1.id]
            )

        assert t1.manual_order == original_order_t1
        assert t2.manual_order == original_order_t2


def test_get_user_tasks_sort_manual_respects_persisted_order(app, test_user_id):
    """Verifica que sort='manual' ordene por manual_order ascendente."""
    with app.app_context():
        t1 = TaskService.create_task(user_id=test_user_id, title="Tarea 1")
        t2 = TaskService.create_task(user_id=test_user_id, title="Tarea 2")
        t3 = TaskService.create_task(user_id=test_user_id, title="Tarea 3")

        TaskService.reorder_tasks(user_id=test_user_id, task_ids=[t2.id, t3.id, t1.id])

        tasks = TaskService.get_user_tasks(user_id=test_user_id, sort="manual")
        assert [t.id for t in tasks] == [t2.id, t3.id, t1.id]


def test_assignee_can_reorder_assigned_task(app, test_user_id, second_user_id):
    """Verifica que el asignatario pueda reordenar una tarea asignada (no creada por él) (clarify Q3)."""
    with app.app_context():
        from src.taskcontrol.models.user import User

        second_user = db.session.get(User, second_user_id)
        task = TaskService.create_task(user_id=test_user_id, title="Delegada")
        TaskService.assign_task(task_id=task.id, user_id=test_user_id, assigned_to_email=second_user.email)

        # No debe lanzar: el asignatario reordena una tarea que no creó
        TaskService.reorder_tasks(user_id=second_user_id, task_ids=[task.id])
        assert task.manual_order == 0


def test_backfill_manual_order_follows_created_at_per_user(app, test_user_id, second_user_id):
    """Verifica que el backfill asigne manual_order secuencial por usuario según created_at descendente."""
    with app.app_context():
        older = TaskService.create_task(user_id=test_user_id, title="Más antigua")
        newer = TaskService.create_task(user_id=test_user_id, title="Más reciente")
        other_user_task = TaskService.create_task(user_id=second_user_id, title="De otro usuario")

        TaskService.backfill_manual_order()

        assert newer.manual_order == 0
        assert older.manual_order == 1
        assert other_user_task.manual_order == 0
