import uuid
from datetime import datetime, timezone


def new_id(prefix: str) -> str:
    """Prefixed random id, e.g. evt_3f9a1c2b7d4e. Prefixes: evt, trc, inc, grt."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
