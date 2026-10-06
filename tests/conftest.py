import pytest
from src.taskcontrol import create_app
from src.taskcontrol.extensions import db


@pytest.fixture
def app():
    """Crea una instancia de la aplicación configurada para pruebas con SQLite en memoria."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente de pruebas HTTP de Flask."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI test runner para comandos de Flask."""
    return app.test_cli_runner()
