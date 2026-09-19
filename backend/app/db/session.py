from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.tables import Base


def make_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def create_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def drop_and_create_tables(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
