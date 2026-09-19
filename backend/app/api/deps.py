from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_db(c: Container = Depends(get_container)) -> Iterator[Session]:
    """Read-only request scope. Mutations go through services under c.state_lock."""
    with c.session_factory() as db:
        yield db
