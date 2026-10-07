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
from src.taskcontrol.services.user_service import (
    UserService,
    ValidationError,
    DuplicateEmailError,
    InvalidResetTokenError,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registro de usuario (HU-12)."""
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("tasks.list_tasks"))
        return render_template("auth/register.html")

    data = request.get_json(silent=True) or request.form
    email = data.get("email", "")
    password = data.get("password", "")

    wants_json = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )

    try:
        user = UserService.register_user(email=email, password=password)
        if wants_json:
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Usuario registrado exitosamente",
                        "data": user.to_dict(),
                    }
                ),
                201,
            )

        flash("Registro exitoso. Por favor inicia sesión.", "success")
        return redirect(url_for("auth.login"))

    except ValidationError as e:
        if wants_json:
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
        return render_template("auth/register.html", email=email), 400

    except DuplicateEmailError as e:
        if wants_json:
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "EMAIL_ALREADY_EXISTS",
                        "message": str(e),
                    }
                ),
                409,
            )
        flash(str(e), "error")
        return render_template("auth/register.html", email=email), 409


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión (HU-13)."""
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("tasks.list_tasks"))
        return render_template("auth/login.html")

    data = request.get_json(silent=True) or request.form
    email = data.get("email", "")
    password = data.get("password", "")

    wants_json = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )

    user = UserService.authenticate_user(email=email, password=password)
    if not user:
        if wants_json:
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "INVALID_CREDENTIALS",
                        "message": "Correo o contraseña incorrectos",
                    }
                ),
                401,
            )
        flash("Correo o contraseña incorrectos", "error")
        return render_template("auth/login.html", email=email), 401

    # Establecer sesión segura en el backend (Principio VII)
    session["user_id"] = user.id
    session["user_email"] = user.email

    if wants_json:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Inicio de sesión exitoso",
                    "data": user.to_dict(),
                }
            ),
            200,
        )

    flash("Bienvenido de nuevo.", "success")
    return redirect(url_for("tasks.list_tasks"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Solicitud de restablecimiento de contraseña con respuesta neutra (HU-14)."""
    if request.method == "GET":
        return render_template("auth/forgot_password.html")

    data = request.get_json(silent=True) or request.form
    email = data.get("email", "")

    wants_json = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )

    if not email or not UserService.EMAIL_REGEX.match(email.strip()):
        if wants_json:
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "INVALID_EMAIL_FORMAT",
                        "message": "Debe proporcionar una dirección de correo electrónico válida",
                    }
                ),
                400,
            )
        flash("Debe proporcionar una dirección de correo electrónico válida", "error")
        return render_template("auth/forgot_password.html", email=email), 400

    UserService.request_password_reset(email)
    neutral_message = (
        "Si el correo ingresado coincide con una cuenta activa en el sistema, "
        "recibirás un correo con las instrucciones para restablecer tu contraseña."
    )

    if wants_json:
        return jsonify({"status": "success", "message": neutral_message}), 200

    flash(neutral_message, "success")
    return render_template("auth/forgot_password.html", submitted=True)


@auth_bp.route("/reset-password/<string:token>", methods=["GET", "POST"])
def reset_password(token):
    """Confirmación de restablecimiento de contraseña mediante token temporal (HU-14)."""
    if request.method == "GET":
        try:
            UserService.verify_reset_token(token)
        except InvalidResetTokenError:
            flash(
                "El enlace de restablecimiento es inválido o ha expirado. "
                "Por favor, solicita uno nuevo.",
                "error",
            )
            return redirect(url_for("auth.forgot_password")), 400
        return render_template("auth/reset_password.html", token=token)

    data = request.get_json(silent=True) or request.form
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    wants_json = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )
    failure_message = "Las contraseñas no coinciden o el enlace ha caducado"

    if new_password != confirm_password:
        if wants_json:
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "PASSWORD_RESET_FAILED",
                        "message": failure_message,
                    }
                ),
                400,
            )
        flash(failure_message, "error")
        return render_template("auth/reset_password.html", token=token), 400

    try:
        UserService.reset_password(token, new_password)
    except (InvalidResetTokenError, ValidationError):
        if wants_json:
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "PASSWORD_RESET_FAILED",
                        "message": failure_message,
                    }
                ),
                400,
            )
        flash(failure_message, "error")
        return render_template("auth/reset_password.html", token=token), 400

    success_message = (
        "Tu contraseña ha sido restablecida exitosamente. "
        "Ya puedes iniciar sesión con tu nueva contraseña."
    )
    if wants_json:
        return jsonify({"status": "success", "message": success_message}), 200

    flash(success_message, "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Cierre de sesión (HU-13)."""
    session.clear()

    wants_json = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )

    if wants_json:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Sesión finalizada exitosamente",
                }
            ),
            200,
        )

    flash("Has cerrado sesión.", "info")
    return redirect(url_for("auth.login"))
