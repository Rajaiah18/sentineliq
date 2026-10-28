"""
SentinelIQ Frontend Jinja2 Server-Rendered Routes
All 11 required views powered by real database repository queries and authentic user sessions.
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, Form, Response, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.app.config import settings
from backend.app.database.repository import repo
from backend.app.security.auth import authenticate_user, create_access_token, decode_access_token, get_demo_users
from generator.generate import DatasetGenerator
from validation.checks import DataValidator
from evaluation.evaluator import RiskEvaluator
from risk_engine.rules import DEFAULT_RULES

frontend_router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="frontend/templates")


def get_session_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    return get_demo_users().get(username)


@frontend_router.get("/")
def index_redirect():
    return RedirectResponse(url="/dashboard")


# =============================================================================
# Page 1: Login
# =============================================================================
@frontend_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "current_user": get_session_user(request),
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password.",
            "current_user": None,
            "storage_mode": repo.storage_mode
        }, status_code=401)

    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return response


# =============================================================================
# Page 2: Dashboard Overview
# =============================================================================
@frontend_router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request):
    user = get_session_user(request)
    metrics = repo.get_overview_metrics()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "dashboard",
        "current_user": user,
        "metrics": metrics,
        "storage_mode": repo.storage_mode
    })


# =============================================================================
# Page 3: Transactions & Transaction Detail
# =============================================================================
@frontend_router.get("/transactions", response_class=HTMLResponse)
def transactions_list(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None
):
    user = get_session_user(request)
    txns, total = repo.get_transactions(page=page, page_size=20, search=search, transaction_type=type, status=status)
    return templates.TemplateResponse("transactions.html", {
        "request": request,
        "active_page": "transactions",
        "current_user": user,
        "transactions": txns,
        "total": total,
        "page": page,
        "page_size": 20,
        "search": search,
        "selected_type": type,
        "selected_status": status,
        "storage_mode": repo.storage_mode
    })


@frontend_router.get("/transactions/{transaction_id}", response_class=HTMLResponse)
def transaction_detail(request: Request, transaction_id: str):
    user = get_session_user(request)
    txn = repo.get_transaction_by_id(transaction_id)
    if not txn:
        return RedirectResponse(url="/transactions")

    cust = repo.get_customer_by_id(txn.get("customer_id", ""))
    src_acc = repo.get_account_by_id(txn.get("source_account_id", ""))
    dst_acc = repo.get_account_by_id(txn.get("destination_account_id", "")) if txn.get("destination_account_id") else None

    all_alerts, _ = repo.get_alerts(page_size=100)
    alerts = [a for a in all_alerts if transaction_id in a.get("triggered_transaction_ids", [])]

    return templates.TemplateResponse("transaction_detail.html", {
        "request": request,
        "active_page": "transactions",
        "current_user": user,
        "transaction": txn,
        "customer": cust,
        "source_account": src_acc,
        "destination_account": dst_acc,
        "alerts": alerts,
        "storage_mode": repo.storage_mode
    })


# =============================================================================
# Page 4: Customers & Accounts
# =============================================================================
@frontend_router.get("/customers", response_class=HTMLResponse)
def customers_list(request: Request, page: int = 1, search: Optional[str] = None, risk: Optional[str] = None):
    user = get_session_user(request)
    custs, total = repo.get_customers(page=page, page_size=20, search=search, risk_profile=risk)
    return templates.TemplateResponse("customers.html", {
        "request": request,
        "active_page": "customers",
        "current_user": user,
        "customers": custs,
        "total": total,
        "page": page,
        "page_size": 20,
        "search": search,
        "selected_risk": risk,
        "storage_mode": repo.storage_mode
    })


@frontend_router.get("/customers/{customer_id}", response_class=HTMLResponse)
def customer_detail(request: Request, customer_id: str):
    user = get_session_user(request)
    cust = repo.get_customer_by_id(customer_id)
    if not cust:
        return RedirectResponse(url="/customers")

    accounts, _ = repo.get_accounts(customer_id=customer_id, page_size=50)
    alerts, _ = repo.get_alerts(customer_id=customer_id, page_size=50)

    return templates.TemplateResponse("customer_detail.html", {
        "request": request,
        "active_page": "customers",
        "current_user": user,
        "customer": cust,
        "accounts": accounts,
        "alerts": alerts,
        "storage_mode": repo.storage_mode
    })


@frontend_router.get("/accounts", response_class=HTMLResponse)
def accounts_list(request: Request, page: int = 1, status: Optional[str] = None):
    user = get_session_user(request)
    accs, total = repo.get_accounts(page=page, page_size=20, status=status)
    return templates.TemplateResponse("accounts.html", {
        "request": request,
        "active_page": "accounts",
        "current_user": user,
        "accounts": accs,
        "total": total,
        "page": page,
        "page_size": 20,
        "selected_status": status,
        "storage_mode": repo.storage_mode
    })


@frontend_router.get("/accounts/{account_id}", response_class=HTMLResponse)
def account_detail(request: Request, account_id: str):
    user = get_session_user(request)
    acc = repo.get_account_by_id(account_id)
    if not acc:
        return RedirectResponse(url="/accounts")

    cust = repo.get_customer_by_id(acc.get("customer_id", ""))
    txns, _ = repo.get_transactions(account_id=account_id, page_size=20)

    return templates.TemplateResponse("account_detail.html", {
        "request": request,
        "active_page": "accounts",
        "current_user": user,
        "account": acc,
        "customer": cust,
        "transactions": txns,
        "storage_mode": repo.storage_mode
    })


# =============================================================================
# Page 5: Alerts & Alert Detail
# =============================================================================
@frontend_router.get("/alerts", response_class=HTMLResponse)
def alerts_list(
    request: Request,
    page: int = 1,
    severity: Optional[str] = None,
    status: Optional[str] = None
):
    user = get_session_user(request)
    alts, total = repo.get_alerts(page=page, page_size=20, severity=severity, status=status)
    return templates.TemplateResponse("alerts.html", {
        "request": request,
        "active_page": "alerts",
        "current_user": user,
        "alerts": alts,
        "total": total,
        "page": page,
        "page_size": 20,
        "selected_severity": severity,
        "selected_status": status,
        "storage_mode": repo.storage_mode
    })


@frontend_router.get("/alerts/{alert_id}", response_class=HTMLResponse)
def alert_detail(request: Request, alert_id: str):
    user = get_session_user(request)
    alt = repo.get_alert_by_id(alert_id)
    if not alt:
        return RedirectResponse(url="/alerts")

    # Fetch triggering transactions
    triggered_txns = []
    for tid in alt.get("triggered_transaction_ids", []):
        t = repo.get_transaction_by_id(tid)
        if t:
            triggered_txns.append(t)

    cases, _ = repo.get_cases(page_size=50)
    linked_cases = [c for c in cases if alert_id in c.get("alert_ids", [])]

    return templates.TemplateResponse("alert_detail.html", {
        "request": request,
        "active_page": "alerts",
        "current_user": user,
        "alert": alt,
        "triggering_transactions": triggered_txns,
        "linked_cases": linked_cases,
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/alerts/{alert_id}/status")
def alert_status_post(request: Request, alert_id: str, status: str = Form(...)):
    user = get_session_user(request)
    actor = user["username"] if user else "ANALYST"
    repo.update_alert_status(alert_id, status.upper(), actor_id=actor)
    return RedirectResponse(url=f"/alerts/{alert_id}", status_code=303)


# =============================================================================
# Page 6: Cases & Case Detail
# =============================================================================
@frontend_router.get("/cases", response_class=HTMLResponse)
def cases_list(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    user = get_session_user(request)
    cases, total = repo.get_cases(page=page, page_size=20, status=status, priority=priority)
    return templates.TemplateResponse("cases.html", {
        "request": request,
        "active_page": "cases",
        "current_user": user,
        "cases": cases,
        "total": total,
        "page": page,
        "page_size": 20,
        "selected_status": status,
        "selected_priority": priority,
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/cases")
def create_case_post(
    request: Request,
    alert_id: str = Form(...),
    customer_id: str = Form(...),
    case_title: str = Form(...),
    priority: str = Form("MEDIUM")
):
    user = get_session_user(request)
    actor = user["username"] if user else "ANALYST"
    case_doc = repo.create_case(
        case_title=case_title,
        description=f"Investigation opened for alert {alert_id}",
        priority=priority,
        alert_ids=[alert_id],
        customer_id=customer_id,
        assigned_analyst_id=actor,
        actor_id=actor
    )
    return RedirectResponse(url=f"/cases/{case_doc['case_id']}", status_code=303)


@frontend_router.get("/cases/{case_id}", response_class=HTMLResponse)
def case_detail(request: Request, case_id: str):
    user = get_session_user(request)
    c = repo.get_case_by_id(case_id)
    if not c:
        return RedirectResponse(url="/cases")

    actions = repo.get_actions_by_case(case_id)
    alerts = []
    for a_id in c.get("alert_ids", []):
        alt = repo.get_alert_by_id(a_id)
        if alt:
            alerts.append(alt)

    return templates.TemplateResponse("case_detail.html", {
        "request": request,
        "active_page": "cases",
        "current_user": user,
        "case": c,
        "alerts": alerts,
        "actions_timeline": actions,
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/cases/{case_id}/action")
def case_action_post(
    request: Request,
    case_id: str,
    action_type: str = Form(...),
    comment: str = Form(...),
    new_status: Optional[str] = Form(None)
):
    user = get_session_user(request)
    analyst_id = user["username"] if user else "ANALYST"
    repo.add_analyst_action(
        case_id=case_id,
        analyst_id=analyst_id,
        action_type=action_type,
        comment=comment,
        new_status=new_status if new_status else None
    )
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@frontend_router.post("/cases/{case_id}/disposition")
def case_disposition_post(
    request: Request,
    case_id: str,
    disposition: str = Form(...),
    reason: str = Form(...)
):
    user = get_session_user(request)
    analyst_id = user["username"] if user else "COMPLIANCE"
    repo.add_analyst_action(
        case_id=case_id,
        analyst_id=analyst_id,
        action_type="DISPOSITION_RECORDED",
        comment=reason,
        new_status="CLOSED" if disposition != "ESCALATED" else "PENDING_REVIEW",
        disposition=disposition
    )
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


# =============================================================================
# Page 7: Risk Rules
# =============================================================================
@frontend_router.get("/rules", response_class=HTMLResponse)
def rules_list(request: Request):
    user = get_session_user(request)
    rules = repo.get_rules()
    return templates.TemplateResponse("rules.html", {
        "request": request,
        "active_page": "rules",
        "current_user": user,
        "rules": rules,
        "storage_mode": repo.storage_mode
    })


@frontend_router.get("/rules/{rule_id}", response_class=HTMLResponse)
def rule_detail(request: Request, rule_id: str):
    user = get_session_user(request)
    rule = repo.get_rule_by_id(rule_id)
    if not rule:
        return RedirectResponse(url="/rules")

    return templates.TemplateResponse("rule_detail.html", {
        "request": request,
        "active_page": "rules",
        "current_user": user,
        "rule": rule,
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/rules/{rule_id}/update")
def rule_update_post(
    request: Request,
    rule_id: str,
    severity: str = Form(...),
    weight: float = Form(...),
    threshold: float = Form(...),
    enabled: str = Form(...)
):
    user = get_session_user(request)
    actor = user["username"] if user else "ADMIN"
    repo.update_rule(rule_id, {
        "severity": severity,
        "weight": weight,
        "threshold": threshold,
        "enabled": (enabled.lower() == "true")
    }, actor_id=actor)
    return RedirectResponse(url=f"/rules/{rule_id}", status_code=303)


# =============================================================================
# Page 8: Data Quality & Validation
# =============================================================================
@frontend_router.get("/validation", response_class=HTMLResponse)
def validation_view(request: Request):
    user = get_session_user(request)
    val_file = os.path.join(settings.REPORTS_DIR, "validation_summary.json")
    report = {}
    if os.path.isfile(val_file):
        with open(val_file, "r", encoding="utf-8") as f:
            report = json.load(f)

    return templates.TemplateResponse("validation.html", {
        "request": request,
        "active_page": "validation",
        "current_user": user,
        "report": report,
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/validation/run")
def run_validation_post():
    validator = DataValidator()
    customers, _ = repo.get_customers(page_size=100)
    accounts, _ = repo.get_accounts(page_size=100)
    transactions, _ = repo.get_transactions(page_size=100)
    alerts, _ = repo.get_alerts(page_size=100)
    cases, _ = repo.get_cases(page_size=100)
    actions = list(repo._memory_store["analyst_actions"].values())
    merchants = list(repo._memory_store["merchants"].values())
    devices = list(repo._memory_store["devices"].values())
    transfers = list(repo._memory_store["transfer_links"].values())

    report = validator.run_all_checks(
        customers=customers,
        accounts=accounts,
        merchants=merchants,
        devices=devices,
        transactions=transactions,
        transfer_links=transfers,
        alerts=alerts,
        cases=cases,
        analyst_actions=actions,
        rules=DEFAULT_RULES
    )
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    with open(os.path.join(settings.REPORTS_DIR, "validation_summary.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return RedirectResponse(url="/validation", status_code=303)


# =============================================================================
# Page 9: Evaluation
# =============================================================================
@frontend_router.get("/evaluation", response_class=HTMLResponse)
def evaluation_view(request: Request):
    user = get_session_user(request)
    eval_file = os.path.join(settings.REPORTS_DIR, "evaluation_summary.json")
    report = {}
    if os.path.isfile(eval_file):
        with open(eval_file, "r", encoding="utf-8") as f:
            report = json.load(f)

    return templates.TemplateResponse("evaluation.html", {
        "request": request,
        "active_page": "evaluation",
        "current_user": user,
        "report": report,
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/evaluation/run")
def run_evaluation_post():
    gt_file = os.path.join(settings.GROUND_TRUTH_DIR, "ground_truth.json")
    if os.path.isfile(gt_file):
        with open(gt_file, "r", encoding="utf-8") as f:
            ground_truth = json.load(f)
        alerts, _ = repo.get_alerts(page_size=100)
        _, total_txns = repo.get_transactions(page_size=1)
        evaluator = RiskEvaluator()
        eval_report = evaluator.evaluate(alerts, ground_truth, total_txns)
        with open(os.path.join(settings.REPORTS_DIR, "evaluation_summary.json"), "w", encoding="utf-8") as f:
            json.dump(eval_report, f, indent=2)

    return RedirectResponse(url="/evaluation", status_code=303)


# =============================================================================
# Page 10: Data Generation & Exports
# =============================================================================
@frontend_router.get("/generator", response_class=HTMLResponse)
def generator_view(request: Request):
    user = get_session_user(request)
    manifest_path = os.path.join(settings.DATASET_EXPORT_DIR, "manifest.json")
    manifest = {}
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    return templates.TemplateResponse("generator.html", {
        "request": request,
        "active_page": "generator",
        "current_user": user,
        "manifest": manifest,
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/generator/run")
def run_generator_post(profile: str = Form("demo"), seed: int = Form(20261022)):
    gen = DatasetGenerator(profile=profile, seed=seed)
    gen.run(
        export_dir=settings.DATASET_EXPORT_DIR,
        gt_dir=settings.GROUND_TRUTH_DIR,
        reports_dir=settings.REPORTS_DIR
    )
    repo._try_load_exports_into_memory()
    return RedirectResponse(url="/generator", status_code=303)


# =============================================================================
# Page 11: Audit Trail
# =============================================================================
@frontend_router.get("/audit", response_class=HTMLResponse)
def audit_view(request: Request, page: int = 1, entity_type: Optional[str] = None):
    user = get_session_user(request)
    events, total = repo.get_audit_events(page=page, page_size=25, entity_type=entity_type)
    return templates.TemplateResponse("audit.html", {
        "request": request,
        "active_page": "audit",
        "current_user": user,
        "audit_events": events,
        "total": total,
        "page": page,
        "page_size": 25,
        "selected_entity": entity_type,
        "storage_mode": repo.storage_mode
    })
