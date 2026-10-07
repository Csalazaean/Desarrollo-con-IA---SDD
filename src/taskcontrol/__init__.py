import os
from flask import Flask
from src.taskcontrol.config import config_by_name
from src.taskcontrol.extensions import db, migrate


def create_app(config_name=None):
    """Application factory para el monolito TaskControl."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Importar y registrar blueprints
    from src.taskcontrol.routes.auth import auth_bp
    from src.taskcontrol.routes.tasks import tasks_bp
    from src.taskcontrol.routes.categories import categories_bp
    from src.taskcontrol.routes.notifications import notifications_bp
    from src.taskcontrol.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")
    app.register_blueprint(categories_bp, url_prefix="/categories")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    @app.context_processor
    def inyectar_notificaciones_sin_leer():
        """Expone el contador de no leídas a todas las plantillas (FR-011).

        Va en un context processor y no en cada ruta porque la barra de navegación
        lo muestra en todas las páginas; calcularlo ruta por ruta sería repetirlo
        en cada vista y olvidarlo en la siguiente que se añada.
        """
        from flask import session as flask_session
        from src.taskcontrol.services.notification_service import NotificationService

        if "user_id" not in flask_session:
            return {"unread_notifications": 0}
        return {
            "unread_notifications": NotificationService.unread_count(
                flask_session["user_id"]
            )
        }

    return app
