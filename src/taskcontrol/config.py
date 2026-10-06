import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Configuración base de la aplicación TaskControl."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-taskcontrol-2026")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'taskcontrol.db'}"
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_PERMANENT = False
    PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES", "30")
    )


class TestingConfig(Config):
    """Configuración para ejecución de pruebas automatizadas."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"


class DevelopmentConfig(Config):
    """Configuración para desarrollo local."""

    DEBUG = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
