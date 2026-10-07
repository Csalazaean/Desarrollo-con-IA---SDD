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
from src.taskcontrol.routes.auth_helpers import login_required
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
from src.taskcontrol.services.category_service import CategoryNotFoundError, CategoryService

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
    sort = request.args.get("sort")
    category_filter = request.args.get("category_id")
    view = request.args.get("view", "all")

    tasks = TaskService.get_user_tasks(
        user_id=user_id, status=status_filter, sort=sort, category_id=category_filter, view=view
    )

    if _is_json_request():
        return (
            jsonify(
                {
                    "status": "success",
                    "data": {
                        "tasks": [t.to_dict(current_user_id=user_id) for t in tasks],
                        "count": len(tasks),
                        "filter": status_filter,
                    },
                }
            ),
            200,
        )

    categories = CategoryService.list_user_categories(user_id=user_id)

    return render_template(
        "tasks/index.html",
        tasks=tasks,
        current_status=status_filter,
        current_sort=sort,
        current_category=category_filter,
        current_view=view,
        current_user_id=user_id,
        categories=categories,
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
    priority = data.get("priority") or "medium"

    try:
        task = TaskService.create_task(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
        )

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

    except InvalidPriorityError as e:
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
        return redirect(url_for("tasks.list_tasks"))


@tasks_bp.route("/reorder", methods=["POST"])
@login_required
def reorder_tasks_route():
    """Persiste el nuevo orden visual tras arrastrar y soltar (HU-16)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    task_ids = data.get("task_ids")

    if not task_ids or not isinstance(task_ids, list):
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "VALIDATION_ERROR",
                    "message": "Debe proporcionar un arreglo de identificadores de tarea",
                }
            ),
            400,
        )

    try:
        updated_count = TaskService.reorder_tasks(user_id=user_id, task_ids=task_ids)
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Orden actualizado exitosamente",
                    "data": {"updated_count": updated_count},
                }
            ),
            200,
        )
    except TaskNotFoundError:
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "TASK_NOT_FOUND",
                    "message": "Una o más tareas no existen o no te pertenecen",
                }
            ),
            404,
        )


@tasks_bp.route("/<int:task_id>/priority", methods=["POST", "PATCH"])
@login_required
def update_priority_route(task_id: int):
    """Cambio de prioridad de una tarea (HU-07)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form
    priority = data.get("priority")

    try:
        task = TaskService.update_task_priority(
            user_id=user_id, task_id=task_id, priority=priority
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
        flash("Tarea no encontrada.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except InvalidPriorityError as e:
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


@tasks_bp.route("/<int:task_id>/category", methods=["POST", "PATCH"])
@login_required
def assign_category_route(task_id: int):
    """Asignación (o desasignación) de categoría a una tarea (HU-08)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form
    category_id = data.get("category_id")
    if category_id in ("", "null", "none", None):
        category_id = None
    else:
        category_id = int(category_id)

    try:
        task = TaskService.assign_category(
            user_id=user_id, task_id=task_id, category_id=category_id
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Categoría de la tarea actualizada",
                        "data": task.to_dict(),
                    }
                ),
                200,
            )

        flash("Categoría de la tarea actualizada.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "TASK_NOT_FOUND", "message": "Tarea no encontrada"}),
                404,
            )
        flash("Tarea no encontrada.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except CategoryNotFoundError:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "CATEGORY_NOT_FOUND", "message": "Categoría no encontrada"}),
                404,
            )
        flash("Categoría no encontrada.", "error")
        return redirect(url_for("tasks.list_tasks")), 404


@tasks_bp.route("/<int:task_id>/assign", methods=["POST"])
@login_required
def assign_task_route(task_id: int):
    """Asignación de una tarea propia a otro usuario por correo (HU-10)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form
    assigned_to_email = data.get("assigned_to_email", "")

    if not assigned_to_email or not assigned_to_email.strip():
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "VALIDATION_ERROR", "message": "Debe indicar un correo electrónico válido"}),
                400,
            )
        flash("Debe indicar un correo electrónico válido.", "error")
        return redirect(url_for("tasks.list_tasks")), 400

    try:
        task = TaskService.assign_task(
            task_id=task_id, user_id=user_id, assigned_to_email=assigned_to_email
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Tarea asignada exitosamente",
                        "data": task.to_dict(current_user_id=user_id),
                    }
                ),
                200,
            )

        flash("Tarea asignada exitosamente.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "TASK_NOT_FOUND", "message": "Tarea no encontrada"}),
                404,
            )
        flash("Tarea no encontrada.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except AssigneeNotFoundError as e:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "ASSIGNEE_NOT_FOUND", "message": str(e)}),
                404,
            )
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks")), 404


@tasks_bp.route("/<int:task_id>/unassign", methods=["POST"])
@login_required
def unassign_task_route(task_id: int):
    """Retira la asignación de una tarea propia; nunca notifica (HU-10)."""
    user_id = session["user_id"]

    try:
        task = TaskService.unassign_task(task_id=task_id, user_id=user_id)

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Asignación retirada exitosamente",
                        "data": task.to_dict(current_user_id=user_id),
                    }
                ),
                200,
            )

        flash("Asignación retirada exitosamente.", "success")
        return redirect(url_for("tasks.list_tasks"))

    except TaskNotFoundError:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "TASK_NOT_FOUND", "message": "Tarea no encontrada"}),
                404,
            )
        flash("Tarea no encontrada.", "error")
        return redirect(url_for("tasks.list_tasks")), 404


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
        categories = CategoryService.list_user_categories(user_id=user_id)
        return render_template("tasks/edit.html", task=task, categories=categories)

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


@tasks_bp.route("/<int:task_id>/delete", methods=["POST", "DELETE"])
@login_required
def delete_task_route(task_id: int):
    """Eliminación lógica (soft delete) de una tarea propia (HU-05)."""
    user_id = session["user_id"]

    try:
        task = TaskService.delete_task(user_id=user_id, task_id=task_id)

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Tarea eliminada exitosamente",
                        "data": {
                            "task_id": task.id,
                            "is_deleted": task.is_deleted,
                            "deleted_at": task.deleted_at.isoformat()
                            if task.deleted_at
                            else None,
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
        flash("Tarea no encontrada.", "error")
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
        return redirect(url_for("tasks.list_tasks")), 409


@tasks_bp.route("/<int:task_id>/reopen", methods=["POST"])
@login_required
def reopen_task_route(task_id: int):
    """Reapertura de una tarea completada, devolviéndola a 'pending' (HU-06)."""
    user_id = session["user_id"]

    try:
        task = TaskService.reopen_task(user_id=user_id, task_id=task_id)

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Tarea reabierta exitosamente",
                        "data": {
                            "task_id": task.id,
                            "status": task.status,
                            "previous_status": "completed",
                            "updated_at": task.updated_at.isoformat()
                            if task.updated_at
                            else None,
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
        flash("Tarea no encontrada.", "error")
        return redirect(url_for("tasks.list_tasks")), 404

    except InvalidTaskStateTransitionError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "INVALID_STATE_FOR_REOPEN",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks")), 400
