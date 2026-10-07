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
from src.taskcontrol.services.notification_service import (
    NotificationService,
    NotificationNotFoundError,
)

notifications_bp = Blueprint("notifications", __name__)


def _is_json_request():
    return (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )


@notifications_bp.route("", methods=["GET"])
@login_required
def list_notifications():
    """Centro de notificaciones del usuario autenticado (HU-11, FR-010)."""
    user_id = session["user_id"]
    notificaciones = NotificationService.get_user_notifications(user_id)
    sin_leer = NotificationService.unread_count(user_id)

    if _is_json_request():
        return (
            jsonify(
                {
                    "status": "success",
                    "data": {
                        "notifications": [n.to_dict() for n in notificaciones],
                        "unread_count": sin_leer,
                    },
                }
            ),
            200,
        )

    return render_template(
        "notifications/index.html", notifications=notificaciones, unread_count=sin_leer
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read_route(notification_id: int):
    """Marca una notificación propia como leída (FR-012)."""
    user_id = session["user_id"]

    try:
        notificacion = NotificationService.mark_as_read(notification_id, user_id)

        if _is_json_request():
            datos = notificacion.to_dict()
            datos["unread_count"] = NotificationService.unread_count(user_id)
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Notificación marcada como leída",
                        "data": datos,
                    }
                ),
                200,
            )

        return redirect(url_for("notifications.list_notifications"))

    except NotificationNotFoundError as e:
        # Una notificación ajena responde igual que una inexistente: no se confirma
        # su existencia a quien no es su destinatario (FR-014).
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "NOTIFICATION_NOT_FOUND",
                        "message": str(e),
                    }
                ),
                404,
            )
        flash("La notificación no existe o no te pertenece.", "error")
        return redirect(url_for("notifications.list_notifications")), 404


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read_route():
    """Marca todas las notificaciones pendientes del usuario como leídas (FR-012)."""
    user_id = session["user_id"]
    marcadas = NotificationService.mark_all_as_read(user_id)

    if _is_json_request():
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Todas las notificaciones fueron marcadas como leídas",
                    "data": {
                        "marked_count": marcadas,
                        "unread_count": NotificationService.unread_count(user_id),
                    },
                }
            ),
            200,
        )

    flash("Todas tus notificaciones quedaron marcadas como leídas.", "success")
    return redirect(url_for("notifications.list_notifications"))
