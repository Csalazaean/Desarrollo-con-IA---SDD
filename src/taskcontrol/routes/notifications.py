from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
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
    """Listado cronológico descendente de notificaciones del usuario (HU-11)."""
    user_id = session["user_id"]
    notifications = NotificationService.list_user_notifications(user_id=user_id)
    unread_count = NotificationService.get_unread_count(user_id=user_id)

    if _is_json_request():
        return (
            jsonify(
                {
                    "status": "success",
                    "data": {
                        "notifications": [n.to_dict() for n in notifications],
                        "unread_count": unread_count,
                    },
                }
            ),
            200,
        )

    return render_template(
        "notifications/index.html", notifications=notifications, unread_count=unread_count
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_as_read_route(notification_id: int):
    """Marca una notificación propia como leída."""
    user_id = session["user_id"]

    try:
        notification = NotificationService.mark_as_read(
            notification_id=notification_id, user_id=user_id
        )
        if _is_json_request():
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Notificación marcada como leída",
                        "data": notification.to_dict(),
                    }
                ),
                200,
            )
        return redirect(url_for("notifications.list_notifications"))

    except NotificationNotFoundError:
        if _is_json_request():
            return (
                jsonify({"status": "error", "code": "NOTIFICATION_NOT_FOUND", "message": "Notificación no encontrada"}),
                404,
            )
        flash("Notificación no encontrada.", "error")
        return redirect(url_for("notifications.list_notifications")), 404


@notifications_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_as_read_route():
    """Marca todas las notificaciones pendientes del usuario como leídas."""
    user_id = session["user_id"]
    updated_count = NotificationService.mark_all_as_read(user_id=user_id)

    if _is_json_request():
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Todas las notificaciones fueron marcadas como leídas",
                    "data": {"updated_count": updated_count},
                }
            ),
            200,
        )

    flash("Todas las notificaciones fueron marcadas como leídas.", "success")
    return redirect(url_for("notifications.list_notifications"))
