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
from src.taskcontrol.services.category_service import (
    CategoryService,
    DuplicateCategoryNameError,
    CategoryNotFoundError,
    InvalidCategoryColorError,
)

categories_bp = Blueprint("categories", __name__)


def _is_json_request():
    return (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )


@categories_bp.route("", methods=["GET"])
@login_required
def list_categories():
    """Listado de categorías del usuario autenticado con conteo de tareas (HU-08)."""
    user_id = session["user_id"]
    categories = CategoryService.list_user_categories(user_id=user_id)

    if _is_json_request():
        return jsonify({"status": "success", "data": {"categories": categories}}), 200

    return render_template("categories/index.html", categories=categories)


@categories_bp.route("", methods=["POST"])
@login_required
def create_category_route():
    """Creación de categoría (HU-08)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form

    name = data.get("name", "")
    description = data.get("description")
    color = data.get("color") or None

    try:
        category = CategoryService.create_category(
            user_id=user_id, name=name, description=description, color=color
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Categoría creada exitosamente",
                        "data": category.to_dict(),
                    }
                ),
                201,
            )

        flash("Categoría creada exitosamente.", "success")
        return redirect(url_for("categories.list_categories"))

    except DuplicateCategoryNameError as e:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "DUPLICATE_CATEGORY_NAME", "message": str(e)}),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories")), 400

    except InvalidCategoryColorError as e:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "INVALID_CATEGORY_COLOR", "message": str(e)}),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories")), 400


@categories_bp.route("/<int:category_id>/edit", methods=["POST"])
@login_required
def edit_category_route(category_id: int):
    """Edición de categoría propia (HU-08, FR-007)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form

    name = data.get("name", "")
    description = data.get("description")
    color = data.get("color") or None

    try:
        category = CategoryService.update_category(
            category_id=category_id,
            user_id=user_id,
            name=name,
            description=description,
            color=color,
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Categoría actualizada exitosamente",
                        "data": category.to_dict(),
                    }
                ),
                200,
            )

        flash("Categoría actualizada exitosamente.", "success")
        return redirect(url_for("categories.list_categories"))

    except CategoryNotFoundError:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "CATEGORY_NOT_FOUND", "message": "Categoría no encontrada"}),
                404,
            )
        flash("Categoría no encontrada.", "error")
        return redirect(url_for("categories.list_categories")), 404

    except DuplicateCategoryNameError as e:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "DUPLICATE_CATEGORY_NAME", "message": str(e)}),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories")), 400

    except InvalidCategoryColorError as e:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "INVALID_CATEGORY_COLOR", "message": str(e)}),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories")), 400


@categories_bp.route("/<int:category_id>/delete", methods=["POST", "DELETE"])
@login_required
def delete_category_route(category_id: int):
    """Eliminación de categoría con desvinculación de tareas sin cascada (HU-08)."""
    user_id = session["user_id"]

    try:
        tasks_unlinked = CategoryService.delete_category(
            category_id=category_id, user_id=user_id
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Categoría eliminada exitosamente. Las tareas asociadas permanecen sin categoría.",
                        "data": {
                            "deleted_category_id": category_id,
                            "tasks_unlinked_count": tasks_unlinked,
                        },
                    }
                ),
                200,
            )

        flash("Categoría eliminada. Las tareas asociadas quedaron sin categoría.", "success")
        return redirect(url_for("categories.list_categories"))

    except CategoryNotFoundError:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "CATEGORY_NOT_FOUND", "message": "Categoría no encontrada"}),
                404,
            )
        flash("Categoría no encontrada.", "error")
        return redirect(url_for("categories.list_categories")), 404
