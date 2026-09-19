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
    ans_mode: Literal["real", "mock"] = "mock"
    ans_base_url: str = "https://api.godaddy.com"
    ans_api_key: str = ""  # PAT, or "key:secret" when ans_auth_scheme=sso-key
    ans_auth_scheme: Literal["bearer", "sso-key"] = "bearer"
    ans_timeout_seconds: float = 3.0
    ans_cache_ttl_seconds: int = 60
    ans_stale_ok_seconds: int = 3600  # serve last *real* ANS answer if ANS is unreachable

    # --- Gemini behavioral analysis (Person 3) ---
    gemini_mode: Literal["real", "mock"] = "mock"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout_seconds: float = 8.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
