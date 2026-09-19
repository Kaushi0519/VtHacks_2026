"""Developer-facing decision logs. The demo happens in the UI; these are for debugging."""

import logging

from app.models.event import SentinelEvent

log = logging.getLogger("sentinel")


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")


def log_event(event: SentinelEvent) -> None:
    log.info(
        "trace=%s agent=%s kind=%s action=%s target=%s decision=%s reason=%s risk=%s->%s",
        event.trace_id,
        event.actor_agent_id,
        event.kind.value,
        event.action,
        event.target_agent_id or event.target_resource,
        event.decision.value if event.decision else None,
        event.reason_code.value if event.reason_code else None,
        event.risk_before,
        event.risk_after,
    )
