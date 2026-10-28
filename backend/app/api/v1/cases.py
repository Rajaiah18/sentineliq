"""
SentinelIQ Investigation Cases API Router
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from backend.app.database.repository import repo
from backend.app.security.permissions import RequireAnalyst, RequireCompliance, get_current_user

router = APIRouter(prefix="/cases", tags=["Investigation Cases"])


class CreateCaseRequest(BaseModel):
    case_title: str
    description: str
    priority: str = Field("MEDIUM", description="LOW | MEDIUM | HIGH | CRITICAL")
    alert_ids: List[str]
    customer_id: str
    assigned_analyst_id: Optional[str] = None


class CaseActionRequest(BaseModel):
    action_type: str = Field(..., description="ASSIGNED | STATUS_CHANGE | NOTE_ADDED | DISPOSITION_RECORDED | ESCALATED")
    comment: str
    new_status: Optional[str] = None
    disposition: Optional[str] = None


class DispositionRequest(BaseModel):
    disposition: str = Field(..., description="CONFIRMED_SUSPICIOUS | FALSE_POSITIVE | INCONCLUSIVE | ESCALATED")
    reason: str


VALID_STATUS_TRANSITIONS = {
    "OPEN": ["IN_PROGRESS", "CLOSED"],
    "IN_PROGRESS": ["PENDING_REVIEW", "CLOSED"],
    "PENDING_REVIEW": ["IN_PROGRESS", "CLOSED"],
    "CLOSED": ["OPEN"]  # Re-opened under exceptional circumstances
}


@router.get("")
def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_analyst_id: Optional[str] = None
):
    items, total = repo.get_cases(
        page=page,
        page_size=page_size,
        status=status,
        priority=priority,
        assigned_analyst_id=assigned_analyst_id
    )
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_case(payload: CreateCaseRequest, user: Dict[str, Any] = RequireAnalyst):
    # Verify alert exists
    for a_id in payload.alert_ids:
        alt = repo.get_alert_by_id(a_id)
        if not alt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Referenced alert {a_id} does not exist.")

    case_doc = repo.create_case(
        case_title=payload.case_title,
        description=payload.description,
        priority=payload.priority.upper(),
        alert_ids=payload.alert_ids,
        customer_id=payload.customer_id,
        assigned_analyst_id=payload.assigned_analyst_id or user.get("user_id"),
        actor_id=user.get("username", "ANALYST")
    )
    return case_doc


@router.get("/{case_id}")
def get_case(case_id: str):
    c = repo.get_case_by_id(case_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found.")

    cust = repo.get_customer_by_id(c.get("customer_id", ""))
    actions = repo.get_actions_by_case(case_id)

    alerts = []
    for a_id in c.get("alert_ids", []):
        alt = repo.get_alert_by_id(a_id)
        if alt:
            alerts.append(alt)

    return {
        "case": c,
        "customer": cust,
        "alerts": alerts,
        "actions_timeline": actions
    }


@router.post("/{case_id}/actions")
def add_case_action(case_id: str, payload: CaseActionRequest, user: Dict[str, Any] = RequireAnalyst):
    c = repo.get_case_by_id(case_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found.")

    curr_status = c.get("case_status", "OPEN")
    if payload.new_status and payload.new_status.upper() != curr_status:
        target_status = payload.new_status.upper()
        allowed = VALID_STATUS_TRANSITIONS.get(curr_status, [])
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {curr_status} to {target_status}. Allowed: {', '.join(allowed)}"
            )

    action_doc = repo.add_analyst_action(
        case_id=case_id,
        analyst_id=user.get("user_id", "ANALYST"),
        action_type=payload.action_type.upper(),
        comment=payload.comment,
        new_status=payload.new_status.upper() if payload.new_status else None,
        disposition=payload.disposition.upper() if payload.disposition else None
    )
    return action_doc


@router.post("/{case_id}/disposition")
def record_case_disposition(case_id: str, payload: DispositionRequest, user: Dict[str, Any] = RequireCompliance):
    c = repo.get_case_by_id(case_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found.")

    valid_dispositions = ["CONFIRMED_SUSPICIOUS", "FALSE_POSITIVE", "INCONCLUSIVE", "ESCALATED"]
    disp = payload.disposition.upper()
    if disp not in valid_dispositions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid disposition '{payload.disposition}'. Allowed: {', '.join(valid_dispositions)}"
        )

    action_doc = repo.add_analyst_action(
        case_id=case_id,
        analyst_id=user.get("user_id", "COMPLIANCE"),
        action_type="DISPOSITION_RECORDED",
        comment=payload.reason,
        new_status="CLOSED" if disp != "ESCALATED" else "PENDING_REVIEW",
        disposition=disp
    )
    return {"status": "success", "case_id": case_id, "disposition": disp, "action": action_doc}
