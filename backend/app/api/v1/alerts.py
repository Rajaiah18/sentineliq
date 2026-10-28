"""
SentinelIQ Alerts API Router
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import BaseModel
from backend.app.database.repository import repo
from backend.app.security.permissions import RequireAnalyst, get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertStatusUpdate(BaseModel):
    alert_status: str  # NEW | UNDER_REVIEW | ESCALATED | CLOSED


@router.get("")
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    customer_id: Optional[str] = None,
    sort_by: str = "risk_score",
    sort_desc: bool = True
):
    items, total = repo.get_alerts(
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
        customer_id=customer_id,
        sort_by=sort_by,
        sort_desc=sort_desc
    )
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }


@router.get("/{alert_id}")
def get_alert(alert_id: str):
    alt = repo.get_alert_by_id(alert_id)
    if not alt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} not found.")

    cust = repo.get_customer_by_id(alt.get("customer_id", ""))

    # Fetch triggering transactions
    triggered_txns = []
    for tid in alt.get("triggered_transaction_ids", []):
        t = repo.get_transaction_by_id(tid)
        if t:
            triggered_txns.append(t)

    # Fetch related cases
    cases, _ = repo.get_cases(page_size=50)
    linked_cases = [c for c in cases if alert_id in c.get("alert_ids", [])]

    return {
        "alert": alt,
        "customer": cust,
        "triggering_transactions": triggered_txns,
        "linked_cases": linked_cases
    }


@router.get("/{alert_id}/evidence")
def get_alert_evidence(alert_id: str):
    alt = repo.get_alert_by_id(alert_id)
    if not alt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} not found.")
    return {
        "alert_id": alert_id,
        "risk_score": alt.get("risk_score"),
        "severity": alt.get("severity"),
        "reason_codes": alt.get("reason_codes", []),
        "explanation": alt.get("explanation"),
        "evidence": alt.get("evidence", {})
    }


@router.get("/{alert_id}/history")
def get_alert_history(alert_id: str):
    events, _ = repo.get_audit_events(page_size=100)
    matched = [e for e in events if e.get("entity_id") == alert_id or e.get("correlation_id") == alert_id]
    return {
        "alert_id": alert_id,
        "history": matched
    }


@router.patch("/{alert_id}/status")
def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdate,
    user: Dict[str, Any] = RequireAnalyst
):
    valid_statuses = ["NEW", "UNDER_REVIEW", "ESCALATED", "CLOSED"]
    new_st = payload.alert_status.upper()
    if new_st not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid alert status '{payload.alert_status}'. Allowed: {', '.join(valid_statuses)}"
        )

    updated = repo.update_alert_status(alert_id, new_st, actor_id=user.get("username", "ANALYST"))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} not found.")
    return updated
