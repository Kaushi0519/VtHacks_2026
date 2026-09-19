"""Shared base + enums for every wire contract.

CONTRACT FILE. Everything in app/models/ is mirrored by frontend/types/sentinel.ts and
documented in docs/API.md. Change all three in the same commit; Person 1 reviews.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """camelCase on the wire, snake_case in Python. Accepts either on input."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_HUMAN = "require_human"
    QUARANTINE = "quarantine"


class RiskLevel(StrEnum):
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Sensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
