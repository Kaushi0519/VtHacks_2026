"""Storage layout: a few indexed columns for querying + a JSON `body` holding the full Pydantic
model. The Pydantic contract stays the single source of truth and adding a field needs no
migration (dev: `make reset`). Works on SQLite and Postgres.

Owner: Person 1.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Stores naive UTC, always returns tz-aware UTC (SQLite drops tzinfo)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to UTCDateTime")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        return value.replace(tzinfo=timezone.utc) if value is not None else None


class Base(DeclarativeBase):
    pass


class AgentRow(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    ans_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    body: Mapped[dict] = mapped_column(JSON)  # models.agent.Agent
    profile: Mapped[dict] = mapped_column(JSON)  # models.agent.BehaviorProfile


class GrantRow(Base):
    __tablename__ = "grants"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    body: Mapped[dict] = mapped_column(JSON)  # models.policy.PermissionGrant


class EventRow(Base):
    """Append-only. The repo exposes no update/delete for events."""

    __tablename__ = "events"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String, unique=True, index=True)
    trace_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    actor_agent_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    reason_code: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    incident_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    body: Mapped[dict] = mapped_column(JSON)  # models.event.SentinelEvent


class IncidentRow(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    body: Mapped[dict] = mapped_column(JSON)  # models.incident.Incident
