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
    CategoryValidationError,
    DuplicateCategoryNameError,
    CategoryNotFoundError,
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
    """Listado de categorías del usuario con conteo de tareas activas (HU-08)."""
    user_id = session["user_id"]
    categorias = CategoryService.get_user_categories(user_id)

    if _is_json_request():
        return jsonify({"status": "success", "data": {"categories": categorias}}), 200

    return render_template("categories/index.html", categories=categorias)


@categories_bp.route("", methods=["POST"])
@login_required
def create_category_route():
    """Creación de categoría (HU-08)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form

    try:
        categoria = CategoryService.create_category(
            user_id=user_id,
            name=data.get("name", ""),
            description=data.get("description"),
            color=data.get("color"),
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Categoría creada exitosamente",
                        "data": {
                            "id": categoria.id,
                            "name": categoria.name,
                            "color": categoria.color,
                        },
                    }
                ),
                201,
            )

        flash("Categoría creada exitosamente.", "success")
        return redirect(url_for("categories.list_categories"))

    except DuplicateCategoryNameError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "DUPLICATE_CATEGORY_NAME",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories")), 400

    except CategoryValidationError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "INVALID_CATEGORY_NAME",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories")), 400


@categories_bp.route("/<int:category_id>/edit", methods=["POST"])
@login_required
def update_category_route(category_id: int):
    """Edición de una categoría propia (FR-007)."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form

    try:
        categoria = CategoryService.update_category(
            category_id=category_id,
            user_id=user_id,
            name=data.get("name", ""),
            description=data.get("description"),
            color=data.get("color"),
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Categoría actualizada exitosamente",
                        "data": {
                            "id": categoria.id,
                            "name": categoria.name,
                            "color": categoria.color,
                        },
                    }
                ),
                200,
            )

        flash("Categoría actualizada exitosamente.", "success")
        return redirect(url_for("categories.list_categories"))

    except CategoryNotFoundError as e:
        if _is_json_request():
            return (
                jsonify(
                    {"status": "error", "code": "CATEGORY_NOT_FOUND", "message": str(e)}
                ),
                404,
            )
        flash("La categoría no existe o no te pertenece.", "error")
        return redirect(url_for("categories.list_categories")), 404

    except DuplicateCategoryNameError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "DUPLICATE_CATEGORY_NAME",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories")), 400

    except CategoryValidationError as e:
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "INVALID_CATEGORY_NAME",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories")), 400


@categories_bp.route("/<int:category_id>/delete", methods=["POST"])
@categories_bp.route("/<int:category_id>", methods=["DELETE"], endpoint="delete_category_api")
@login_required
def delete_category_route(category_id: int):
    """Eliminación de categoría desvinculando sus tareas, sin borrarlas (FR-009)."""
    user_id = session["user_id"]

    try:
        resultado = CategoryService.delete_category(
            category_id=category_id, user_id=user_id
        )

        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": (
                            "Categoría eliminada exitosamente. "
                            "Las tareas asociadas permanecen sin categoría."
                        ),
                        "data": resultado,
                    }
                ),
                200,
            )

        flash(
            "Categoría eliminada. Las tareas asociadas siguen existiendo, ahora sin categoría.",
            "success",
        )
        return redirect(url_for("categories.list_categories"))

    except CategoryNotFoundError as e:
        if _is_json_request():
            return (
                jsonify(
                    {"status": "error", "code": "CATEGORY_NOT_FOUND", "message": str(e)}
                ),
                404,
            )
        flash("La categoría no existe o no te pertenece.", "error")
        return redirect(url_for("categories.list_categories")), 404
