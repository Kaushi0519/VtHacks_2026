"""Identity as reported by ANS. CONTRACT FILE (see models/common.py).

ANS answers "who is this agent, and is its registration valid?". It says nothing about
whether the agent's *current behavior* is acceptable; that is Lattice's job.
"""

from datetime import datetime
from typing import Literal

from app.models.common import ApiModel

# ANS lifecycle statuses come straight from GoDaddy ANS (AgentLifecycleStatus):
#   PENDING_VALIDATION, PENDING_DNS, ACTIVE, FAILED, EXPIRED, DEPRECATED, REVOKED
# plus Lattice-side outcomes when no lifecycle status could be read:
#   NOT_FOUND (name does not resolve), INVALID_NAME, UNREACHABLE (ANS down, no usable cache)
AnsStatus = str


class IdentityResult(ApiModel):
    ans_name: str
    verified: bool  # True only when the name resolves AND lifecycle status is ACTIVE
    ans_status: AnsStatus
    source: Literal["ans", "mock"]  # "mock" must never be presented as a live ANS call
    ans_agent_id: str | None = None  # ANS registry UUID
    tl_verified: bool = False  # Transparency-Log SCITT receipt cryptographically verified (real mode)
    checked_at: datetime
    cached: bool = False
    stale: bool = False  # served from cache because ANS was unreachable
    detail: str | None = None
