import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from src.taskcontrol.extensions import db
from src.taskcontrol.models.audit import AuditLog
from src.taskcontrol.models.password_reset import PasswordResetToken
from src.taskcontrol.models.user import User
from src.taskcontrol.services.audit_service import AuditService


# Canal propio para la simulación de correo de HU-14. Se configura igual que el de
# auditoría porque `app.logger` queda en WARNING cuando el modo debug está apagado,
# y entonces el enlace de restablecimiento —que en este entorno sustituye al correo—
# nunca llegaría a la consola.
reset_logger = logging.getLogger("taskcontrol.password_reset")
if not reset_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    reset_logger.addHandler(_handler)
    reset_logger.setLevel(logging.INFO)


class ValidationError(Exception):
    """Excepción para errores de validación de entrada."""
    pass


class DuplicateEmailError(Exception):
    """Excepción para correos electrónicos ya registrados."""
    pass


class PasswordResetError(Exception):
    """Excepción para fallos en el flujo de recuperación de contraseña."""
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

    # ------------------------------------------------------------------
    # HU-14: Recuperación segura de contraseña
    # ------------------------------------------------------------------

    # Actor convencional para eventos originados por un solicitante no autenticado
    ANONYMOUS_ACTOR_ID = 0

    @staticmethod
    def generate_reset_token() -> str:
        """Genera un token de restablecimiento criptográficamente seguro y URL-safe."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_reset_token(raw_token: str) -> str:
        """Deriva el hash SHA-256 que se persiste en lugar del token en claro."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def request_password_reset(cls, email: str) -> bool:
        """Solicita el restablecimiento de contraseña (HU-14).

        Retorna siempre True, exista o no la cuenta, para no permitir enumerar
        qué correos están registrados (Principio VII). El token solo se emite
        cuando la cuenta existe realmente.
        """
        if not email or not cls.EMAIL_REGEX.match(email.strip()):
            raise ValidationError("Debe proporcionar una dirección de correo electrónico válida")

        email_clean = email.strip().lower()
        user = User.query.filter_by(email=email_clean).first()

        if not user:
            # Respuesta neutra: no se emite token ni se revela la ausencia de la cuenta
            return True

        now_utc = datetime.now(timezone.utc)

        # Invalidar los tokens pendientes previos: solo el último enlace enviado sirve
        pendientes = PasswordResetToken.query.filter_by(
            user_id=user.id, used_at=None
        ).all()
        for token_previo in pendientes:
            token_previo.used_at = now_utc

        raw_token = cls.generate_reset_token()
        minutos = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES", 30)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=cls.hash_reset_token(raw_token),
            expires_at=now_utc + timedelta(minutes=minutos),
            created_at=now_utc,
        )
        db.session.add(token)

        AuditService.log_event(
            actor_id=cls.ANONYMOUS_ACTOR_ID,
            action=AuditLog.ACTION_PASSWORD_RESET_REQUESTED,
            entity_id=user.id,
            details={"email": email_clean, "expires_at": token.expires_at.isoformat()},
        )
        db.session.commit()

        # Entorno académico: el envío de correo se simula escribiendo el enlace en el log
        reset_logger.info(
            "[SIMULACION CORREO] Restablecimiento solicitado para %s | enlace: "
            "/auth/reset-password/%s (vigencia %s minutos)",
            email_clean,
            raw_token,
            minutos,
        )

        return True

    @classmethod
    def verify_reset_token(cls, raw_token: str) -> PasswordResetToken | None:
        """Retorna el token vigente que corresponde al valor en claro, o None."""
        if not raw_token:
            return None

        token = PasswordResetToken.query.filter_by(
            token_hash=cls.hash_reset_token(raw_token)
        ).first()

        if not token or not token.is_valid():
            return None
        return token

    @classmethod
    def reset_password(cls, raw_token: str, new_password: str) -> bool:
        """Restablece la contraseña y consume el token de forma atómica (HU-14)."""
        token = cls.verify_reset_token(raw_token)
        if not token:
            raise PasswordResetError(
                "El enlace de restablecimiento es inválido o ha expirado"
            )

        # La validación ocurre antes de consumir el token: un intento inválido no gasta el enlace
        if not new_password or len(new_password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")

        user = db.session.get(User, token.user_id)
        if not user:
            raise PasswordResetError(
                "El enlace de restablecimiento es inválido o ha expirado"
            )

        user.password_hash = generate_password_hash(new_password)
        token.used_at = datetime.now(timezone.utc)

        AuditService.log_event(
            actor_id=user.id,
            action=AuditLog.ACTION_PASSWORD_RESET_COMPLETED,
            entity_id=user.id,
            details={"email": user.email},
        )
        db.session.commit()

        return True
