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
    PasswordResetError,
)

auth_bp = Blueprint("auth", __name__)

# Mensaje único para solicitudes de recuperación: no revela si la cuenta existe (Principio VII)
NEUTRAL_RESET_MESSAGE = (
    "Si el correo ingresado coincide con una cuenta activa en el sistema, "
    "recibirás un correo con las instrucciones para restablecer tu contraseña."
)
INVALID_TOKEN_MESSAGE = (
    "El enlace de restablecimiento es inválido o ha expirado. "
    "Por favor, solicita uno nuevo."
)


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


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Solicitud de restablecimiento de contraseña (HU-14)."""
    if request.method == "GET":
        return render_template("auth/forgot_password.html")

    data = request.get_json(silent=True) or request.form
    email = data.get("email", "")

    wants_json = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )

    try:
        UserService.request_password_reset(email)
    except ValidationError as e:
        if wants_json:
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "INVALID_EMAIL_FORMAT",
                        "message": str(e),
                    }
                ),
                400,
            )
        flash(str(e), "error")
        return render_template("auth/forgot_password.html", email=email), 400

    # Respuesta idéntica exista o no la cuenta: impide enumerar correos registrados
    if wants_json:
        return (
            jsonify({"status": "success", "message": NEUTRAL_RESET_MESSAGE}),
            200,
        )

    return render_template("auth/forgot_password.html", neutral_message=NEUTRAL_RESET_MESSAGE)


@auth_bp.route("/reset-password/<string:token>", methods=["GET", "POST"])
def reset_password(token):
    """Confirmación de restablecimiento de contraseña (HU-14)."""
    wants_json = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.path.startswith("/api/")
    )

    if request.method == "GET":
        if not UserService.verify_reset_token(token):
            if wants_json:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "code": "PASSWORD_RESET_FAILED",
                            "message": INVALID_TOKEN_MESSAGE,
                        }
                    ),
                    400,
                )
            flash(INVALID_TOKEN_MESSAGE, "error")
            return render_template("auth/forgot_password.html"), 400

        return render_template("auth/reset_password.html", token=token)

    data = request.get_json(silent=True) or request.form
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    def _fallo(mensaje):
        if wants_json:
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "PASSWORD_RESET_FAILED",
                        "message": mensaje,
                    }
                ),
                400,
            )
        flash(mensaje, "error")
        return render_template("auth/reset_password.html", token=token), 400

    if new_password != confirm_password:
        return _fallo("Las contraseñas no coinciden o el enlace ha caducado")

    try:
        UserService.reset_password(token, new_password)
    except (PasswordResetError, ValidationError) as e:
        return _fallo(str(e))

    if wants_json:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": (
                        "Tu contraseña ha sido restablecida exitosamente. "
                        "Ya puedes iniciar sesión con tu nueva contraseña."
                    ),
                }
            ),
            200,
        )

    flash("Tu contraseña ha sido restablecida exitosamente.", "success")
    return redirect(url_for("auth.login"))
