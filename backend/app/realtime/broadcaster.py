"""In-process pub/sub feeding the SSE stream. Owner: Person 1.

Single-process by design (run uvicorn with ONE worker). Swap for Redis pub/sub only if we ever
need multiple workers, which we won't for the demo.
"""

import asyncio
import json
import logging
from typing import Any

from app.models.agent import Agent
from app.models.event import SentinelEvent
from app.models.incident import Incident
from app.models.policy import PermissionGrant
from app.models.system import StreamType

log = logging.getLogger("sentinel.realtime")


class Broadcaster:
    def __init__(self, queue_size: int = 2000):
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._queue_size = queue_size

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._subscribers.discard(q)

    def publish(self, type_: StreamType, data: dict[str, Any]) -> None:
        message = json.dumps({"type": type_.value, "data": data})
        for q in list(self._subscribers):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                log.warning("dropping slow SSE subscriber")
                self._subscribers.discard(q)

    # Typed helpers. Publish order within one operation: event -> agent -> grant -> incident.
    def event(self, e: SentinelEvent) -> None:
        self.publish(StreamType.EVENT, e.to_json())

    def agent(self, a: Agent) -> None:
        self.publish(StreamType.AGENT, a.to_json())

    def incident(self, i: Incident) -> None:
        self.publish(StreamType.INCIDENT, i.to_json())

    def grant(self, g: PermissionGrant) -> None:
        self.publish(StreamType.GRANT, g.to_json())

    def resync(self) -> None:
        self.publish(StreamType.RESYNC, {})
