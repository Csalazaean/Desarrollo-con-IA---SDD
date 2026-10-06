from functools import wraps
from flask import session, request, jsonify, redirect, url_for


def login_required(f):
    """Decorador que exige sesión activa en el backend (Principio VII)."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            # Si la petición es JSON o de API, responder 401 Unauthorized
            if (
                request.is_json
                or request.headers.get("Accept") == "application/json"
                or request.path.startswith("/api/")
            ):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "code": "UNAUTHORIZED",
                            "message": "Autenticación requerida para acceder a este recurso",
                        }
                    ),
                    401,
                )
            # Para peticiones de navegador HTML, redirigir a login
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function
