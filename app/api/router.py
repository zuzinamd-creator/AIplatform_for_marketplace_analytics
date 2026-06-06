from fastapi import APIRouter

from app.api import ai, analytics, auth, costs, dashboard, ops, reports, system, workflow

api_router = APIRouter()
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(costs.router, prefix="/costs", tags=["costs"])
api_router.include_router(ops.router, prefix="/ops", tags=["operations"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
