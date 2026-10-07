import hashlib
import logging
import re
import pytest
from datetime import datetime, timedelta, timezone
from src.taskcontrol.extensions import db
from src.taskcontrol.models.audit import AuditLog
from src.taskcontrol.models.password_reset import PasswordResetToken
from src.taskcontrol.services.user_service import (
    UserService,
    ValidationError,
    DuplicateEmailError,
    PasswordResetError,
    reset_logger,
)
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


# ---------------------------------------------------------------------------
# HU-14: Recuperación segura de contraseña
# ---------------------------------------------------------------------------


def _issue_token(user, minutes: int = 30, used: bool = False) -> str:
    """Emite un token de restablecimiento y retorna su valor en claro."""
    raw_token = UserService.generate_reset_token()
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=UserService.hash_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
        used_at=datetime.now(timezone.utc) if used else None,
    )
    db.session.add(token)
    db.session.commit()
    return raw_token


def test_password_reset_request_neutral_response_existing_and_non_existing_email(app):
    """La solicitud responde igual exista o no la cuenta, sin filtrar correos registrados."""
    with app.app_context():
        user = UserService.register_user("existente@example.com", "Password123!")

        resultado_existente = UserService.request_password_reset("existente@example.com")
        resultado_inexistente = UserService.request_password_reset("fantasma@example.com")

        # Respuesta idéntica: no se puede distinguir un correo registrado de uno que no lo está
        assert resultado_existente is True
        assert resultado_inexistente is True

        # Pero internamente solo se emite token para la cuenta que sí existe
        tokens = PasswordResetToken.query.all()
        assert len(tokens) == 1
        assert tokens[0].user_id == user.id


def test_password_reset_token_hashed_in_database(app, caplog):
    """El token se persiste como hash SHA-256, nunca en texto plano (Principio VII)."""
    with app.app_context():
        UserService.register_user("hash@example.com", "Password123!")

        with caplog.at_level(logging.INFO):
            UserService.request_password_reset("hash@example.com")

        coincidencia = re.search(r"/auth/reset-password/([A-Za-z0-9_-]+)", caplog.text)
        assert coincidencia, "El enlace simulado debe registrarse en el log de la aplicación"
        raw_token = coincidencia.group(1)

        token = PasswordResetToken.query.one()
        assert token.token_hash != raw_token
        assert token.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
        assert len(token.token_hash) == 64


def test_password_reset_success_updates_password_and_invalidates_token(app):
    """Restablecer actualiza el hash de la contraseña y consume el token de forma atómica."""
    with app.app_context():
        user = UserService.register_user("reset@example.com", "PasswordVieja123!")
        raw_token = _issue_token(user)

        UserService.reset_password(raw_token, "PasswordNueva456!")

        db.session.refresh(user)
        assert check_password_hash(user.password_hash, "PasswordNueva456!")
        assert not check_password_hash(user.password_hash, "PasswordVieja123!")

        token = PasswordResetToken.query.one()
        assert token.used_at is not None

        # La credencial nueva es la que sirve para autenticarse
        assert UserService.authenticate_user("reset@example.com", "PasswordNueva456!") is not None
        assert UserService.authenticate_user("reset@example.com", "PasswordVieja123!") is None


def test_cannot_reuse_already_used_reset_token(app):
    """Un token ya consumido no puede reutilizarse."""
    with app.app_context():
        user = UserService.register_user("reuso@example.com", "Password123!")
        raw_token = _issue_token(user)

        UserService.reset_password(raw_token, "PrimeraNueva123!")

        with pytest.raises(PasswordResetError):
            UserService.reset_password(raw_token, "SegundaNueva123!")

        # La contraseña permanece en el primer valor restablecido
        db.session.refresh(user)
        assert check_password_hash(user.password_hash, "PrimeraNueva123!")


def test_cannot_use_expired_reset_token(app):
    """Un token vencido es rechazado aunque no se haya usado."""
    with app.app_context():
        user = UserService.register_user("expirado@example.com", "Password123!")
        raw_token = _issue_token(user, minutes=-1)

        with pytest.raises(PasswordResetError):
            UserService.reset_password(raw_token, "PasswordNueva456!")

        assert UserService.verify_reset_token(raw_token) is None


def test_multiple_reset_requests_invalidates_previous_pending_tokens(app):
    """Una nueva solicitud invalida los tokens pendientes anteriores."""
    with app.app_context():
        user = UserService.register_user("multiple@example.com", "Password123!")
        primer_token = _issue_token(user)

        UserService.request_password_reset("multiple@example.com")

        # El token anterior queda inutilizable
        assert UserService.verify_reset_token(primer_token) is None
        with pytest.raises(PasswordResetError):
            UserService.reset_password(primer_token, "PasswordNueva456!")

        # Y existe exactamente un token vigente (el recién emitido)
        vigentes = [t for t in PasswordResetToken.query.all() if t.is_valid()]
        assert len(vigentes) == 1


def test_reset_password_rejects_short_password(app):
    """La contraseña nueva respeta la longitud mínima de 8 caracteres."""
    with app.app_context():
        user = UserService.register_user("corta@example.com", "Password123!")
        raw_token = _issue_token(user)

        with pytest.raises(ValidationError):
            UserService.reset_password(raw_token, "corta")

        # El token no se consume ante una contraseña inválida
        token = PasswordResetToken.query.one()
        assert token.used_at is None


def test_audit_logs_for_password_reset_requested_and_completed(app):
    """Solicitud y restablecimiento quedan auditados por separado (Principio VIII)."""
    with app.app_context():
        user = UserService.register_user("auditoria@example.com", "Password123!")

        UserService.request_password_reset("auditoria@example.com")
        solicitados = AuditLog.query.filter_by(
            action=AuditLog.ACTION_PASSWORD_RESET_REQUESTED
        ).all()
        assert len(solicitados) == 1
        assert solicitados[0].entity_id == user.id

        raw_token = _issue_token(user)
        UserService.reset_password(raw_token, "PasswordNueva456!")

        completados = AuditLog.query.filter_by(
            action=AuditLog.ACTION_PASSWORD_RESET_COMPLETED
        ).all()
        assert len(completados) == 1
        assert completados[0].entity_id == user.id


def test_reset_link_logger_emits_at_info_without_forcing_level():
    """El enlace simulado debe llegar a consola con la configuración real de la app.

    Regresión: usando `app.logger` el mensaje se perdía con el modo debug apagado,
    porque su nivel efectivo es WARNING. Como en este entorno el log sustituye al
    correo, perderlo deja HU-14 inutilizable aunque las pruebas pasen.
    """
    assert reset_logger.isEnabledFor(logging.INFO)


def test_password_reset_request_rejects_invalid_email_format(app):
    """Un correo con formato inválido se rechaza antes de cualquier consulta."""
    with app.app_context():
        with pytest.raises(ValidationError):
            UserService.request_password_reset("no-es-un-correo")
