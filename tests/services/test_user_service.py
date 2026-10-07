import hashlib
from datetime import datetime, timedelta, timezone
import pytest
from src.taskcontrol.services.user_service import (
    UserService,
    ValidationError,
    DuplicateEmailError,
    InvalidResetTokenError,
)
from src.taskcontrol.models.password_reset import PasswordResetToken
from src.taskcontrol.models.audit import AuditLog
from src.taskcontrol.extensions import db
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


# --- US3 (Incremento 2): Recuperación Segura de Contraseña (HU-14) ---

def _extract_simulated_token(caplog) -> str:
    """Extrae el token en texto plano del log de simulación de envío de correo."""
    for record in caplog.records:
        if "/auth/reset-password/" in record.message:
            return record.message.rsplit("/auth/reset-password/", 1)[1].strip()
    raise AssertionError("No se encontró el log de simulación de envío de correo")


def test_password_reset_request_neutral_response_existing_and_non_existing_email(app, caplog):
    """Verifica respuesta neutra idéntica (True) exista o no la cuenta."""
    with app.app_context():
        UserService.register_user("resetexists@example.com", "Password123!")

        with caplog.at_level("INFO"):
            result_existing = UserService.request_password_reset("resetexists@example.com")
            result_missing = UserService.request_password_reset("noexiste@example.com")

        assert result_existing is True
        assert result_missing is True

        # Solo la cuenta existente genera token y auditoría
        assert PasswordResetToken.query.count() == 1
        audit = AuditLog.query.filter_by(action="PASSWORD_RESET_REQUESTED").first()
        assert audit is not None


def test_password_reset_token_hashed_in_database(app, caplog):
    """Verifica que el token en texto plano nunca se persista; solo su hash SHA-256."""
    with app.app_context():
        user = UserService.register_user("resethash@example.com", "Password123!")
        with caplog.at_level("INFO"):
            UserService.request_password_reset("resethash@example.com")
        raw_token = _extract_simulated_token(caplog)

        stored = PasswordResetToken.query.filter_by(user_id=user.id).first()
        assert stored is not None
        assert stored.token_hash != raw_token
        assert stored.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()


def test_password_reset_success_updates_password_and_invalidates_token(app, caplog):
    """Verifica que reset_password actualice la contraseña e invalide el token usado."""
    with app.app_context():
        user = UserService.register_user("resetsuccess@example.com", "OldPassword123!")
        with caplog.at_level("INFO"):
            UserService.request_password_reset("resetsuccess@example.com")
        raw_token = _extract_simulated_token(caplog)

        UserService.reset_password(raw_token, "NewPassword456!")

        refreshed = db.session.get(type(user), user.id)
        assert check_password_hash(refreshed.password_hash, "NewPassword456!")

        token_record = PasswordResetToken.query.filter_by(user_id=user.id).first()
        assert token_record.used_at is not None

        audit = AuditLog.query.filter_by(action="PASSWORD_RESET_COMPLETED").first()
        assert audit is not None


def test_cannot_reuse_already_used_reset_token(app, caplog):
    """Verifica que un token ya consumido no pueda reutilizarse."""
    with app.app_context():
        UserService.register_user("resetreuse@example.com", "OldPassword123!")
        with caplog.at_level("INFO"):
            UserService.request_password_reset("resetreuse@example.com")
        raw_token = _extract_simulated_token(caplog)

        UserService.reset_password(raw_token, "NewPassword456!")

        with pytest.raises(InvalidResetTokenError):
            UserService.reset_password(raw_token, "AnotherPassword789!")


def test_cannot_use_expired_reset_token(app, caplog):
    """Verifica que un token expirado (>30 min) sea rechazado."""
    with app.app_context():
        user = UserService.register_user("resetexpired@example.com", "OldPassword123!")
        with caplog.at_level("INFO"):
            UserService.request_password_reset("resetexpired@example.com")
        raw_token = _extract_simulated_token(caplog)

        token_record = PasswordResetToken.query.filter_by(user_id=user.id).first()
        token_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()

        with pytest.raises(InvalidResetTokenError):
            UserService.reset_password(raw_token, "NewPassword456!")
