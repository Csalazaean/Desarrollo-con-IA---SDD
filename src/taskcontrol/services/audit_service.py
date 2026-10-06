import json
import logging
from datetime import datetime, timezone
from src.taskcontrol.extensions import db
from src.taskcontrol.models.audit import AuditLog

logger = logging.getLogger("taskcontrol.audit")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class AuditService:
    """Servicio centralizado de auditoría y observabilidad estructurada."""

    @staticmethod
    def log_event(actor_id: int, action: str, entity_id: int, details: dict = None):
        """Registra una mutación en base de datos y emite log estructurado JSON."""
        now = datetime.now(timezone.utc)
        details_str = json.dumps(details) if details else None

        # 1. Persistencia relacional inmutable
        audit_entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_id=entity_id,
            timestamp=now,
            details=details_str,
        )
        db.session.add(audit_entry)
        db.session.flush()

        # 2. Emisión a log estructurado JSON
        log_payload = {
            "timestamp": now.isoformat(),
            "actor_id": actor_id,
            "action": action,
            "entity_id": entity_id,
            "details": details or {},
        }
        logger.info(json.dumps(log_payload))

        return audit_entry
