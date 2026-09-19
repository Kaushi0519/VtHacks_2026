"""Wires the app together. One instance lives on app.state.container."""

import asyncio
from dataclasses import dataclass, field

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.seed import load_world
from app.db.session import create_tables, make_engine, make_session_factory
from app.models.policy import World
from app.realtime.broadcaster import Broadcaster
from app.services.ans import ANSService, build_ans_service
from app.services.gateway.pipeline import Gateway
from app.services.gemini.analyzer import BehaviorAnalyzer, build_analyzer
from app.services.gemini.runner import AnalysisRunner


@dataclass
class Container:
    settings: Settings
    world: World
    engine: Engine
    session_factory: sessionmaker[Session]
    broadcaster: Broadcaster
    # Serializes every state mutation (gateway, sweeper, operator actions, analysis write-back).
    # Hackathon throughput is tiny; correctness beats concurrency here.
    state_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    ans: ANSService = field(init=False)
    analyzer: BehaviorAnalyzer = field(init=False)
    gateway: Gateway = field(init=False)
    analysis: AnalysisRunner = field(init=False)

    def reload_world(self) -> None:
        self.world = load_world(self.settings.world_file)


def build_container(settings: Settings) -> Container:
    engine = make_engine(settings.database_url)
    create_tables(engine)
    c = Container(
        settings=settings,
        world=load_world(settings.world_file),
        engine=engine,
        session_factory=make_session_factory(engine),
        broadcaster=Broadcaster(),
    )
    c.ans = build_ans_service(settings, lambda: c.world)
    c.analyzer = build_analyzer(settings)
    c.gateway = Gateway(c)
    c.analysis = AnalysisRunner(c)
    return c
