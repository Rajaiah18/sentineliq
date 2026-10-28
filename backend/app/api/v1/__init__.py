"""SentinelIQ API v1 Package"""
from fastapi import APIRouter
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.metrics import router as metrics_router
from backend.app.api.v1.customers import customers_router, accounts_router
from backend.app.api.v1.transactions import router as transactions_router
from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.cases import router as cases_router
from backend.app.api.v1.rules import router as rules_router
from backend.app.api.v1.operations import router as operations_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(accounts_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(cases_router)
api_v1_router.include_router(rules_router)
api_v1_router.include_router(operations_router)

__all__ = ["api_v1_router"]
