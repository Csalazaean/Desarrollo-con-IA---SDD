from datetime import date
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from src.taskcontrol.models.task import Task
from src.taskcontrol.routes.auth_helpers import login_required
from src.taskcontrol.services.category_service import (
    CategoryService,
    CategoryNotFoundError,
)
from src.taskcontrol.services.task_service import (
    TaskService,
    TaskValidationError,
    TaskNotFoundError,
    InvalidStateTransitionError,
    TaskAlreadyDeletedError,
    NotTaskOwnerError,
    AssigneeNotFoundError,
)

tasks_bp = Blueprint("tasks", __name__)


def _is_json_request():
    return (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )


def _parse_due_date(val):
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val).strip())
    except (ValueError, TypeError):
        return None


@tasks_bp.route("", methods=["GET"])
@login_required
def list_tasks():
    """Listado y filtrado de tareas del usuario autenticado (HU-02)."""
    user_id = session["user_id"]
    status_filter = request.args.get("status")
    category_filter = request.args.get("category_id")
    sort = request.args.get("sort")
    scope = request.args.get("scope")

    tasks = TaskService.get_user_tasks(
        user_id=user_id,
        status=status_filter,
        category_id=category_filter,
        sort=sort,
        scope=scope,
    )

    if _is_json_request():
        return (
            jsonify(
                {
                    "status": "success",
                    "data": {
                        "tasks": [t.to_dict(viewer_id=user_id) for t in tasks],
                        "count": len(tasks),
                        "filter": status_filter,
                        "applied_filters": {
                            "status": status_filter,
                            "category_id": category_filter,
                            "sort": sort,
                            "scope": scope or "all",
                        },
                    },
                }
            ),
            200,
        )

    return render_template(
        "tasks/index.html",
        tasks=tasks,
        current_status=status_filter,
        current_category=category_filter,
        current_sort=sort,
        current_scope=scope,
        current_user_id=user_id,
        categories=CategoryService.get_user_categories(user_id),
        priorities=Task.VALID_PRIORITIES,
    )


@tasks_bp.route("", methods=["POST"])
@login_required
def create_task_route():
    """Creación de tareas (HU-01)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form

    title = data.get("title", "")
    description = data.get("description")
    due_date_str = data.get("due_date")
    due_date = _parse_due_date(due_date_str)

    try:
        task = TaskService.create_task(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date,
            priority=data.get("priority") or None,
        )

        # La categoría es opcional al crear; si viene, se valida igual que al reasignarla.
        categoria_inicial = data.get("category_id")
        if categoria_inicial:
            try:
                TaskService.assign_category_to_task(
                    task_id=task.id, user_id=user_id, category_id=categoria_inicial
                )
            except CategoryNotFoundError:
                flash("La categoría indicada no existe; la tarea se creó sin categoría.", "error")

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Tarea creada exitosamente",
                        "data": task.to_dict(),
                    }
                ),
                201,
            )

        flash("Tarea creada exitosamente.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskValidationError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "VALIDATION_ERROR",
                        "message": str(e),
                    }
                ),
                400,
            )

        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks"))


@tasks_bp.route("/<int:task_id>/status", methods=["POST", "PATCH"])
@login_required
def update_status_route(task_id: int):
    """Cambio de estado de tareas (HU-03)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form
    new_status = data.get("status")

    try:
        task = TaskService.update_task_status(
            user_id=user_id, task_id=task_id, new_status=new_status
        )

        if _is_json_request():
            res_data = task.to_dict()
            res_data["current_status"] = task.status
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Estado de tarea actualizado",
                        "data": res_data,
                    }
                ),
                200,
            )

        flash("Estado de tarea actualizado.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "TASK_NOT_FOUND",
                        "message": "Tarea no encontrada",
                    }
                ),
                404,
            )
        flash("Tarea no encontrada.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except InvalidStateTransitionError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "INVALID_STATE_TRANSITION",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks")), 400


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST", "PUT"])
@login_required
def edit_task_route(task_id: int):
    """Edición de campos informativos de la tarea (HU-04)."""
    user_id = session["user_id"]

    try:
        task = TaskService.get_task_by_id(user_id=user_id, task_id=task_id)
    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "TASK_NOT_FOUND",
                        "message": "Tarea no encontrada",
                    }
                ),
                404,
            )
        flash("Tarea no encontrada.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    if request.method == "GET":
        return render_template("tasks/edit.html", task=task)

    data = request.get_json(silent=True) or request.form
    title = data.get("title", "")
    description = data.get("description")
    due_date = _parse_due_date(data.get("due_date"))

    try:
        updated_task = TaskService.update_task_details(
            user_id=user_id,
            task_id=task_id,
            title=title,
            description=description,
            due_date=due_date,
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Tarea actualizada correctamente",
                        "data": updated_task.to_dict(),
                    }
                ),
                200,
            )

        flash("Tarea actualizada exitosamente.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskValidationError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "VALIDATION_ERROR",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return render_template("tasks/edit.html", task=task), 400


# Dos reglas para la misma vista: el formulario HTML usa POST /<id>/delete y el
# cliente JSON usa DELETE /<id>. Cada una necesita su propio `endpoint` porque, al
# compartirlo, `url_for` resolvía a la regla que solo acepta DELETE y el formulario
# del navegador recibía 405 Method Not Allowed.
@tasks_bp.route("/<int:task_id>/delete", methods=["POST"], endpoint="delete_task_route")
@tasks_bp.route("/<int:task_id>", methods=["DELETE"], endpoint="delete_task_api")
@login_required
def delete_task_route(task_id: int):
    """Eliminación lógica de tareas (HU-05)."""
    user_id = session["user_id"]
    try:
        deleted_task = TaskService.delete_task(task_id=task_id, user_id=user_id)

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Tarea eliminada exitosamente",
                        "data": {
                            "task_id": deleted_task.id,
                            "is_deleted": deleted_task.is_deleted,
                            "deleted_at": (
                                deleted_task.deleted_at.isoformat()
                                if deleted_task.deleted_at
                                else None
                            ),
                        },
                    }
                ),
                200,
            )

        flash("Tarea eliminada exitosamente.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "TASK_NOT_FOUND",
                        "message": "Tarea no encontrada",
                    }
                ),
                404,
            )
        flash("La tarea no existe o no tienes permiso para eliminarla.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except TaskAlreadyDeletedError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "TASK_ALREADY_DELETED",
                        "message": str(e),
                    }
                ),
                409,
            )
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks")), 400


@tasks_bp.route("/<int:task_id>/reopen", methods=["POST"])
@login_required
def reopen_task_route(task_id: int):
    """Reapertura de tareas completadas (HU-06)."""
    user_id = session["user_id"]
    try:
        reopened_task = TaskService.reopen_task(task_id=task_id, user_id=user_id)

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Tarea reabierta exitosamente",
                        "data": {
                            "task_id": reopened_task.id,
                            "status": reopened_task.status,
                            "previous_status": "completed",
                            "updated_at": (
                                reopened_task.updated_at.isoformat()
                                if reopened_task.updated_at
                                else None
                            ),
                        },
                    }
                ),
                200,
            )

        flash("Tarea reabierta exitosamente.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "TASK_NOT_FOUND",
                        "message": "Tarea no encontrada",
                    }
                ),
                404,
            )
        flash("La tarea no existe o no tienes permiso para reabrirla.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except (InvalidStateTransitionError, TaskAlreadyDeletedError) as e:
        if _is_json_request():
            code = (
                "TASK_ALREADY_DELETED"
                if isinstance(e, TaskAlreadyDeletedError)
                else "INVALID_STATE_FOR_REOPEN"
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": code,
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks")), 400


@tasks_bp.route("/<int:task_id>/assign", methods=["POST"])
@login_required
def assign_task_route(task_id: int):
    """Asignación, reasignación o retiro de asignación de una tarea (HU-10)."""
    actor_id = session["user_id"]
    data = request.get_json(silent=True) or request.form
    assignee_email = data.get("assignee_email", "")

    try:
        task = TaskService.assign_task_to_user(
            task_id=task_id, actor_id=actor_id, assignee_email=assignee_email
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": (
                            "Asignación retirada"
                            if task.assigned_to_id is None
                            else "Tarea asignada exitosamente"
                        ),
                        "data": {
                            "task_id": task.id,
                            "assigned_to_id": task.assigned_to_id,
                            "assignee_email": task.assignee_email,
                            "notification_created": (
                                task.assigned_to_id is not None
                                and task.assigned_to_id != actor_id
                            ),
                        },
                    }
                ),
                200,
            )

        flash(
            "Asignación retirada." if task.assigned_to_id is None else "Tarea asignada.",
            "success",
        )
        return redirect(url_for("tasks.list_tasks"))

    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "TASK_NOT_FOUND",
                        "message": "Tarea no encontrada",
                    }
                ),
                404,
            )
        flash("La tarea no existe.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except NotTaskOwnerError as e:
        # 403, no 404: la tarea existe pero el permiso es lo que falta.
        if _is_json_request():
            return (
                jsonify(
                    {"status": "error", "code": "NOT_TASK_OWNER", "message": str(e)}
                ),
                403,
            )
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks")), 403

    except AssigneeNotFoundError as e:
        if _is_json_request():
            return (
                jsonify(
                    {"status": "error", "code": "ASSIGNEE_NOT_FOUND", "message": str(e)}
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks")), 400


@tasks_bp.route("/<int:task_id>/priority", methods=["POST"])
@login_required
def update_priority_route(task_id: int):
    """Cambio de prioridad de una tarea (HU-07)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form
    priority = data.get("priority")

    try:
        task = TaskService.update_task_priority(
            task_id=task_id, user_id=user_id, priority=priority
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Prioridad actualizada exitosamente",
                        "data": {"task_id": task.id, "priority": task.priority},
                    }
                ),
                200,
            )

        flash("Prioridad actualizada.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "TASK_NOT_FOUND",
                        "message": "Tarea no encontrada",
                    }
                ),
                404,
            )
        flash("La tarea no existe o no tienes permiso para modificarla.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except TaskValidationError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "INVALID_PRIORITY",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks")), 400


@tasks_bp.route("/<int:task_id>/category", methods=["POST"])
@login_required
def assign_category_route(task_id: int):
    """Asignación o desvinculación de categoría de una tarea (HU-08)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form
    category_id = data.get("category_id")

    try:
        task = TaskService.assign_category_to_task(
            task_id=task_id, user_id=user_id, category_id=category_id
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Categoría asignada correctamente",
                        "data": {"task_id": task.id, "category_id": task.category_id},
                    }
                ),
                200,
            )

        flash("Categoría actualizada.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except (TaskNotFoundError, CategoryNotFoundError) as e:
        # Tarea ajena y categoría ajena responden igual: no se confirma su existencia.
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "NOT_FOUND",
                        "message": str(e),
                    }
                ),
                404,
            )
        flash("La tarea o la categoría no existen o no te pertenecen.", "error")
        return redirect(url_for("tasks.list_tasks")), 404
