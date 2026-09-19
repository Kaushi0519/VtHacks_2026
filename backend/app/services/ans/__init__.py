from collections.abc import Callable

from app.core.config import Settings
from app.models.policy import World
from app.services.ans.base import ANSService
from app.services.ans.mock import MockANSService
from app.services.ans.reference import ReferenceANSService


def build_ans_service(settings: Settings, get_world: Callable[[], World]) -> ANSService:
    if settings.ans_mode == "real":
        return ReferenceANSService(settings, get_world)
    return MockANSService(get_world)
