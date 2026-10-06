import re
from werkzeug.security import generate_password_hash, check_password_hash
from src.taskcontrol.extensions import db
from src.taskcontrol.models.user import User


class ValidationError(Exception):
    """Excepción para errores de validación de entrada."""
    pass


class DuplicateEmailError(Exception):
    """Excepción para correos electrónicos ya registrados."""
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
