from flask import Blueprint

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    from flask import redirect, url_for, session

    if "user_id" in session:
        return redirect(url_for("tasks.list_tasks"))
    return redirect(url_for("auth.login"))
