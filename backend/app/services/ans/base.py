"""ANSService: the only way Sentinel talks to the Agent Name Service. Owner: Person 3.

ANS establishes WHO an agent is (registration, resolution, lifecycle, revocation).
Sentinel decides whether that verified agent's CURRENT BEHAVIOR deserves access.
Nothing outside app/services/ans/ may know ANS endpoint details.
"""

import re
from typing import Literal, Protocol

from app.models.identity import IdentityResult

# ANS name format (GoDaddy ANS): ans://v{semver}.{agentHost}
ANS_NAME_RE = re.compile(r"^ans://v(?P<version>\d+\.\d+\.\d+)\.(?P<host>[A-Za-z0-9.-]+)$")


def parse_ans_name(ans_name: str) -> tuple[str, str] | None:
    """Returns (version, agent_host) or None if malformed."""
    m = ANS_NAME_RE.match(ans_name)
    return (m.group("version"), m.group("host")) if m else None


class ANSService(Protocol):
    mode: Literal["real", "mock"]
    base_url: str | None

    async def verify_agent(self, ans_name: str) -> IdentityResult:
        """Resolve the name and check lifecycle status. verified == (resolves and ACTIVE).
        Must never raise: network problems return ans_status UNREACHABLE (fail closed)."""
        ...

    async def warm_up(self, ans_names: list[str]) -> None:
        """Pre-resolve enrolled agents at startup so the demo doesn't pay first-call latency."""
        ...

    def invalidate(self, ans_name: str | None = None) -> None: ...
