from fastapi import APIRouter
from app.api.v1.endpoints import (
    candidates,
    jobs,
    interviews,
    workflows,
    agents
)


api_router = APIRouter()

api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
api_router.include_router(interviews.router)
api_router.include_router(workflows.router)
api_router.include_router(agents.router)
