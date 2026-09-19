from fastapi import APIRouter

from app.api import accountability, agents, events, gateway, incidents, system

api_router = APIRouter(prefix="/api")
for module in (system, gateway, agents, events, incidents, accountability):
    api_router.include_router(module.router)
