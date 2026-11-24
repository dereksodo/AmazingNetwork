"""Writing audit entries in the same transaction as the action they describe."""

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(db: Session, actor: User, action: str, target: str, reason: str = "", **details) -> None:
    """Add one audit entry to the current transaction."""
    db.add(AuditLog(actor_id=actor.id, action=action, target=target, reason=reason, details=details))
