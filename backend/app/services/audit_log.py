"""Audit log service placeholder.

This in-memory implementation is intentionally temporary. The next migration
step will replace it with PostgreSQL persistence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.app.core.logging import get_logger, mask_sensitive
from backend.app.schemas.registration import AuditEvent

logger = get_logger(__name__)


class AuditLogService:
    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    def record(
        self,
        *,
        actor_email: str,
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            actor_email=actor_email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata or {},
        )
        self._events.append(event)
        logger.info(
            "audit_event",
            extra={
                "audit_event_id": event.id,
                "actor_email": actor_email,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "metadata": mask_sensitive(event.metadata),
            },
        )
        return event

    def list_events(self) -> List[AuditEvent]:
        return list(reversed(self._events))


audit_log = AuditLogService()
