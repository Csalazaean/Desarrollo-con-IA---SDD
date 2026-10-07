from src.taskcontrol.models.task import Task
from src.taskcontrol.services.task_service import TaskService
from src.taskcontrol.services.user_service import UserService


def _usuario(email):
    return UserService.register_user(email, "Password123!")


def _crear_tareas(user_id, titulos):
    return [TaskService.create_task(user_id=user_id, title=t) for t in titulos]


def test_reorder_persists_new_positions(app):
    """Reordenar reasigna las posiciones de todas las tareas afectadas (FR-007)."""
    with app.app_context():
        user = _usuario("ord-a@example.com")
        a, b, c = _crear_tareas(user.id, ["Primera", "Segunda", "Tercera"])

        TaskService.reorder_user_tasks(user_id=user.id, task_ids=[c.id, a.id, b.id])

        assert c.position == 0
        assert a.position == 1
        assert b.position == 2


def test_reorder_preserves_order_across_queries(app):
    """El orden definido se mantiene al volver a consultar el listado (FR-008, SC-003)."""
    with app.app_context():
        user = _usuario("ord-b@example.com")
        a, b, c = _crear_tareas(user.id, ["Alfa", "Beta", "Gamma"])

        TaskService.reorder_user_tasks(user_id=user.id, task_ids=[b.id, c.id, a.id])

        titulos = [t.title for t in TaskService.get_user_tasks(user.id)]
        assert titulos == ["Beta", "Gamma", "Alfa"]

        # Y sigue igual en una consulta posterior
        titulos_otra_vez = [t.title for t in TaskService.get_user_tasks(user.id)]
        assert titulos_otra_vez == ["Beta", "Gamma", "Alfa"]


def test_reorder_ignores_tasks_of_other_users(app):
    """Una petición manipulada no altera la posición de tareas ajenas (FR-010, SC-004)."""
    with app.app_context():
        propio = _usuario("ord-c@example.com")
        ajeno = _usuario("ord-d@example.com")

        mia, = _crear_tareas(propio.id, ["Mía"])
        suya, = _crear_tareas(ajeno.id, ["Suya"])
        posicion_ajena_antes = suya.position

        resultado = TaskService.reorder_user_tasks(
            user_id=propio.id, task_ids=[suya.id, mia.id]
        )

        assert suya.position == posicion_ajena_antes, "No debe tocarse una tarea ajena"
        assert suya.id in resultado["ignored_ids"]
        assert resultado["reordered_count"] == 1
        assert mia.position == 0


def test_reorder_ignores_nonexistent_and_deleted_ids(app):
    """Identificadores inexistentes o eliminados se ignoran sin romper la operación."""
    with app.app_context():
        user = _usuario("ord-e@example.com")
        viva, borrada = _crear_tareas(user.id, ["Viva", "Borrada"])
        TaskService.delete_task(task_id=borrada.id, user_id=user.id)

        resultado = TaskService.reorder_user_tasks(
            user_id=user.id, task_ids=[99999, borrada.id, viva.id]
        )

        assert resultado["reordered_count"] == 1
        assert set(resultado["ignored_ids"]) == {99999, borrada.id}
        assert viva.position == 0


def test_preexisting_tasks_keep_relative_order_by_default(app):
    """Sin reordenar, el listado conserva el orden de creación (FR-011, SC-005)."""
    with app.app_context():
        user = _usuario("ord-f@example.com")
        _crear_tareas(user.id, ["Vieja", "Media", "Nueva"])

        # Todas comparten position=0; el desempate created_at DESC deja la más
        # reciente arriba, igual que antes de este incremento.
        titulos = [t.title for t in TaskService.get_user_tasks(user.id)]
        assert titulos == ["Nueva", "Media", "Vieja"]
        assert all(t.position == 0 for t in Task.query.filter_by(user_id=user.id).all())


def test_explicit_sort_takes_precedence_over_personal_order(app):
    """Un ordenamiento explícito manda sobre el orden personal (plan.md §3.3)."""
    with app.app_context():
        user = _usuario("ord-g@example.com")
        baja = TaskService.create_task(user_id=user.id, title="Baja", priority="low")
        alta = TaskService.create_task(user_id=user.id, title="Alta", priority="high")

        # El orden personal pone la baja primero...
        TaskService.reorder_user_tasks(user_id=user.id, task_ids=[baja.id, alta.id])
        assert [t.title for t in TaskService.get_user_tasks(user.id)] == ["Baja", "Alta"]

        # ...pero pedir orden por prioridad tiene precedencia
        por_prioridad = TaskService.get_user_tasks(user.id, sort="priority_desc")
        assert [t.title for t in por_prioridad] == ["Alta", "Baja"]


def test_reorder_with_empty_list_changes_nothing(app):
    """Una lista vacía no altera ninguna posición."""
    with app.app_context():
        user = _usuario("ord-h@example.com")
        tarea, = _crear_tareas(user.id, ["Intacta"])

        resultado = TaskService.reorder_user_tasks(user_id=user.id, task_ids=[])

        assert resultado["reordered_count"] == 0
        assert tarea.position == 0
