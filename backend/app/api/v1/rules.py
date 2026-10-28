"""
SentinelIQ Risk Rules API Router
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from backend.app.database.repository import repo
from backend.app.security.permissions import RequireAdmin
from risk_engine.engine import RiskEngine

router = APIRouter(prefix="/rules", tags=["Risk Rules"])


class RuleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    weight: Optional[float] = None
    threshold: Optional[float] = None
    description: Optional[str] = None


class RuleTestRequest(BaseModel):
    transaction: Dict[str, Any]
    account: Dict[str, Any]
    customer: Dict[str, Any]


@router.get("")
def list_rules():
    return {"data": repo.get_rules()}


@router.get("/{rule_id}")
def get_rule(rule_id: str):
    rule = repo.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")
    return rule


@router.patch("/{rule_id}")
def update_rule(rule_id: str, payload: RuleUpdateRequest, user: Dict[str, Any] = RequireAdmin):
    rule = repo.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = repo.update_rule(rule_id, updates, actor_id=user.get("username", "ADMIN"))
    return updated


@router.post("/{rule_id}/test")
def execute_rule_test(rule_id: str, payload: RuleTestRequest):
    rule = repo.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule {rule_id} not found.")

    engine = RiskEngine()
    results = engine.evaluate_transaction(
        transaction=payload.transaction,
        account=payload.account,
        customer=payload.customer
    )

    matched = next((r for r in results if r.rule_id == rule_id), None)
    return {
        "rule_id": rule_id,
        "triggered": matched is not None,
        "result": matched.__dict__ if matched else None
    }
