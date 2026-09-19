from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_db(c: Container = Depends(get_container)) -> Iterator[Session]:
    """Read-only request scope. Mutations go through services under c.state_lock."""
    with c.session_factory() as db:
        yield db


def require_operator(
    x_operator_token: str | None = Header(default=None),
    c: Container = Depends(get_container),
) -> str:
    """Guard operator/admin routes. If OPERATOR_TOKEN is unset the check is disabled (local demo);
    when set, the request must send a matching `X-Operator-Token`. Returns the operator principal,
    which callers use for server-side audit attribution (never trust a client-supplied actor)."""
    expected = c.settings.operator_token
    if not expected:
        return "operator"
    if x_operator_token != expected:
        raise HTTPException(status_code=401, detail="missing or invalid operator token")
    return "operator:token"
