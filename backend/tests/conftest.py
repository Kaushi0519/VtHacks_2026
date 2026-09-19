import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Full app against a throwaway SQLite DB, mock ANS, rule-based analyzer."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ANS_MODE", "mock")
    monkeypatch.setenv("GEMINI_MODE", "mock")
    monkeypatch.setenv("ALLOW_BACKFILL", "true")
    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
