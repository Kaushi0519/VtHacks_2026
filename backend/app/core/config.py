"""Infrastructure settings, loaded from environment / repo-root .env.

Security *policy* (roles, weights, thresholds) is NOT here: it lives in the world file
(simulator/fixtures/world.yaml -> models.policy.World / RiskPolicy) so it can be shown and tuned.

Each section is owned by one person; add new settings to your own section to avoid conflicts.
Every setting must also be documented in /.env.example.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # --- Core / gateway (Person 1) ---
    database_url: str = f"sqlite:///{REPO_ROOT / 'backend' / 'sentinel.db'}"
    world_file: Path = REPO_ROOT / "simulator" / "fixtures" / "world.yaml"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # Lets the simulator replay *historical* traffic (AgentRequest.observedAt) through the real
    # pipeline to seed the accountability view. Demo seeding only; keep false otherwise.
    allow_backfill: bool = False
    sweep_interval_seconds: float = 1.0

    # --- ANS identity (Person 3) ---
    # Real ANS is the open reference implementation (github.com/agentnameservice/ans), run locally:
    #   ans-ra :18080  Registration Authority (registration, identity certs, lifecycle)
    #   ans-tl :18081  Transparency Log (agent badge + SCITT COSE_Sign1 receipts; public read)
    #   ans-verify     offline CLI that cryptographically verifies a receipt (Merkle + ES256)
    # (The earlier api.godaddy.com REST assumption was wrong; see docs/ANS.md.)
    ans_mode: Literal["real", "mock"] = "mock"
    ans_ra_url: str = "http://localhost:18080"     # Registration Authority (setup/admin)
    ans_tl_url: str = "http://localhost:18081"     # Transparency Log (verify path; public read)
    ans_ra_api_key: str = "ans-dev-key-change-me"  # RA admin key; only registration needs it, not verify
    ans_verify_bin: str = "ans-verify"             # path to the ans-verify binary
    ans_timeout_seconds: float = 5.0
    ans_cache_ttl_seconds: int = 60
    ans_stale_ok_seconds: int = 3600  # serve last *real* ANS answer if the TL is unreachable

    # --- Gemini behavioral analysis (Person 3) ---
    gemini_mode: Literal["real", "mock"] = "mock"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"  # official current flash alias; pin a version if needed
    gemini_timeout_seconds: float = 8.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
