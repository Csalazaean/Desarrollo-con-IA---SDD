import pytest
from src.taskcontrol.services.user_service import UserService, ValidationError, DuplicateEmailError
from werkzeug.security import check_password_hash


def test_register_user_success(app):
    """Verifica que un usuario se registre exitosamente con contraseña cifrada."""
    with app.app_context():
        user = UserService.register_user("test@example.com", "SecurePassword123!")
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash != "SecurePassword123!"
        assert check_password_hash(user.password_hash, "SecurePassword123!")


def test_register_user_duplicate_email(app):
    """Verifica que no se permita registrar el mismo correo dos veces."""
    with app.app_context():
        UserService.register_user("duplicate@example.com", "Password123!")
        with pytest.raises(DuplicateEmailError):
            UserService.register_user("duplicate@example.com", "DifferentPassword123!")


def test_register_user_invalid_email(app):
    """Verifica que se rechace un formato de correo inválido."""
    with app.app_context():
        with pytest.raises(ValidationError):
            UserService.register_user("invalid-email-format", "Password123!")


def test_register_user_short_password(app):
    """Verifica que se rechace una contraseña menor a 8 caracteres."""
    with app.app_context():
        with pytest.raises(ValidationError):
            UserService.register_user("valid@example.com", "short")


def test_authenticate_user_success(app):
    """Verifica autenticación exitosa con credenciales correctas."""
    with app.app_context():
        UserService.register_user("authuser@example.com", "AuthPass123!")
        user = UserService.authenticate_user("authuser@example.com", "AuthPass123!")
        assert user is not None
        assert user.email == "authuser@example.com"


def test_authenticate_user_wrong_password(app):
    """Verifica que falle la autenticación con contraseña incorrecta."""
    with app.app_context():
        UserService.register_user("authuser2@example.com", "AuthPass123!")
        user = UserService.authenticate_user("authuser2@example.com", "WrongPassword123!")
        assert user is None


def test_authenticate_user_nonexistent_email(app):
    """Verifica que retorne None para correos no registrados."""
    with app.app_context():
        user = UserService.authenticate_user("nonexistent@example.com", "AuthPass123!")
        assert user is None
