import re
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from src.taskcontrol.extensions import db
from src.taskcontrol.models.user import User
from src.taskcontrol.models.password_reset import PasswordResetToken
from src.taskcontrol.models.audit import (
    ACTION_PASSWORD_RESET_REQUESTED,
    ACTION_PASSWORD_RESET_COMPLETED,
)
from src.taskcontrol.services.audit_service import AuditService

RESET_TOKEN_TTL_MINUTES = 30

# Logger dedicado para la simulación de envío de correo (HU-14): no depende
# del modo debug de Flask, igual que el logger de auditoría (Principio VIII).
logger = logging.getLogger("taskcontrol.password_reset")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ValidationError(Exception):
    """Excepción para errores de validación de entrada."""
    pass


class DuplicateEmailError(Exception):
    """Excepción para correos electrónicos ya registrados."""
    pass


class InvalidResetTokenError(Exception):
    """Token de restablecimiento inexistente, ya utilizado o expirado."""
    pass


class UserService:
    """Lógica de negocio para cuentas de usuario y autenticación."""

    EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

    @classmethod
    def register_user(cls, email: str, password: str) -> User:
        """Registra un nuevo usuario aplicando validaciones y hash seguro."""
        if not email or not cls.EMAIL_REGEX.match(email.strip()):
            raise ValidationError("Formato de correo electrónico inválido")

        email_clean = email.strip().lower()

        if not password or len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")

        # Verificar unicidad
        existing = User.query.filter_by(email=email_clean).first()
        if existing:
            raise DuplicateEmailError("El correo electrónico ya se encuentra registrado")

        # Generar hash de contraseña (scrypt/pbkdf2)
        password_hash = generate_password_hash(password)

        user = User(email=email_clean, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def authenticate_user(cls, email: str, password: str) -> User | None:
        """Verifica credenciales de acceso; retorna User si es válido o None."""
        if not email or not password:
            return None

        email_clean = email.strip().lower()
        user = User.query.filter_by(email=email_clean).first()

        if user and check_password_hash(user.password_hash, password):
            return user
        return None

    @classmethod
    def request_password_reset(cls, email: str) -> bool:
        """Solicita un token de restablecimiento; responde neutralmente exista o no la cuenta."""
        email_clean = (email or "").strip().lower()
        user = User.query.filter_by(email=email_clean).first()

        if user:
            now = datetime.now(timezone.utc)

            # Invalidar tokens previos aún vigentes antes de emitir uno nuevo
            previous_tokens = PasswordResetToken.query.filter_by(
                user_id=user.id, used_at=None
            ).all()
            for previous in previous_tokens:
                previous.used_at = now

            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
            )
            db.session.add(reset_token)
            db.session.commit()

            # Simulación de envío de correo (no hay proveedor de email en este incremento)
            logger.info(
                "[SIMULACION EMAIL] Enlace de restablecimiento para %s: /auth/reset-password/%s",
                user.email,
                raw_token,
            )

            AuditService.log_event(
                actor_id=user.id,
                action=ACTION_PASSWORD_RESET_REQUESTED,
                entity_id=user.id,
                details={"email": user.email},
            )
            db.session.commit()

        # Respuesta neutra: idéntica exista o no la cuenta (previene enumeración)
        return True

    @classmethod
    def verify_reset_token(cls, raw_token: str) -> PasswordResetToken:
        """Valida un token de restablecimiento (existente, no usado y vigente)."""
        if not raw_token:
            raise InvalidResetTokenError("El enlace de restablecimiento es inválido o ha expirado")

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()

        if not token or not token.is_valid():
            raise InvalidResetTokenError("El enlace de restablecimiento es inválido o ha expirado")

        return token

    @classmethod
    def reset_password(cls, raw_token: str, new_password: str) -> User:
        """Consume un token válido para establecer una nueva contraseña (transacción atómica)."""
        token = cls.verify_reset_token(raw_token)

        if not new_password or len(new_password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")

        user = db.session.get(User, token.user_id)
        user.password_hash = generate_password_hash(new_password)
        token.used_at = datetime.now(timezone.utc)
        db.session.commit()

        AuditService.log_event(
            actor_id=user.id,
            action=ACTION_PASSWORD_RESET_COMPLETED,
            entity_id=user.id,
            details={"email": user.email},
        )
        db.session.commit()

        return user
