from datetime import datetime, timezone
from src.taskcontrol.extensions import db


class PasswordResetToken(db.Model):
    """Modelo para tokens temporales de restablecimiento de contraseña (HU-14, Principio VII)."""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash = db.Column(db.String(64), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def is_valid(self):
        """Un token es válido si no ha sido usado y no ha expirado."""
        now = datetime.now(timezone.utc)
        # Ensure comparison works even if expires_at is naive or timezone-aware
        exp = self.expires_at
        if exp.tzinfo is None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.used_at is None and now < exp

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token_hash": self.token_hash,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
