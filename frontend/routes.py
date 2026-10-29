"""
SentinelIQ Frontend Jinja2 Server-Rendered Routes
All views powered by real database repository queries and authoritative server-side RBAC.
Roles: ADMIN, ANALYST, COMPLIANCE_REVIEWER, READ_ONLY.
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
from fastapi import APIRouter, Request, Form, Response, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.app.config import settings
from backend.app.database.repository import repo
from backend.app.security.auth import authenticate_user, create_access_token, decode_access_token
from backend.app.security.permissions import (
    normalize_role,
    has_permission,
    get_navigation_for_role,
    get_grouped_navigation_for_role,
    VALID_ROLES
)
from generator.generate import DatasetGenerator
from validation.checks import DataValidator
from evaluation.evaluator import RiskEvaluator
from risk_engine.rules import DEFAULT_RULES


class CompatibleJinja2Templates(Jinja2Templates):
    """
    Subclass that provides seamless compatibility across Starlette versions.
    Starlette <0.36 used TemplateResponse(name, context)
    Starlette >=0.36 uses TemplateResponse(request=request, name=name, context=context)
    """
    def TemplateResponse(self, *args, **kwargs):
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            name = args[0]
            context = args[1]
            request = context.get("request") or kwargs.get("request")
            status_code = kwargs.get("status_code", 200)
            return super().TemplateResponse(request=request, name=name, context=context, status_code=status_code)
        elif len(args) == 1 and isinstance(args[0], str):
            name = args[0]
            context = kwargs.get("context", {})
            request = context.get("request") or kwargs.get("request")
            status_code = kwargs.get("status_code", 200)
            return super().TemplateResponse(request=request, name=name, context=context, status_code=status_code)
        return super().TemplateResponse(*args, **kwargs)


frontend_router = APIRouter(include_in_schema=False)
templates = CompatibleJinja2Templates(directory="frontend/templates")


def get_session_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Load authoritative user record from repository using JWT cookie or Bearer header.
    Normalizes role server-side to prevent privilege escalation.
    """
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    user = repo.get_user_by_username(username)
    if not user or not user.get("is_active", True):
        return None

    user["role"] = normalize_role(user.get("role"))
    return user


def get_base_context(request: Request, active_page: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Derive global navigation context, permissions, and session indicators."""
    curr_user = user if user is not None else get_session_user(request)
    role = curr_user["role"] if curr_user else "ANONYMOUS"
    nav_items = get_navigation_for_role(role) if curr_user else [
        {"id": "login", "name": "Sign In", "url": "/login"}
    ]
    nav_groups = get_grouped_navigation_for_role(role) if curr_user else []

    return {
        "request": request,
        "active_page": active_page,
        "current_user": curr_user,
        "nav_items": nav_items,
        "nav_groups": nav_groups,
        "storage_mode": repo.storage_mode,
        "can_edit_cases": has_permission(role, "edit:cases"),
        "can_disposition": has_permission(role, "disposition:cases"),
        "can_edit_rules": has_permission(role, "edit:rules"),
        "can_run_generator": has_permission(role, "run:generator"),
        "can_manage_users": has_permission(role, "manage:users")
    }


def require_html_permission(request: Request, permission: str, active_page: str = "dashboard") -> Tuple[Optional[Dict[str, Any]], Optional[Response]]:
    """
    Enforce permission checks for HTML routes.
    If unauthenticated -> redirect to /login?next=...
    If unauthorized -> render 403 forbidden.html
    If authorized -> return (user, None)
    """
    user = get_session_user(request)
    if not user:
        return None, RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_303_SEE_OTHER)

    if not has_permission(user["role"], permission):
        ctx = get_base_context(request, active_page, user)
        ctx["required_permission"] = permission
        ctx["attempted_path"] = request.url.path
        return user, templates.TemplateResponse("forbidden.html", ctx, status_code=status.HTTP_403_FORBIDDEN)

    return user, None


@frontend_router.get("/")
def index_redirect(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return RedirectResponse(url="/dashboard")


# =============================================================================
# Page 1: Login & Authentication
# =============================================================================
@frontend_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None, next: Optional[str] = None):
    user = get_session_user(request)
    if user:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "next": next,
        "current_user": None,
        "nav_items": [{"id": "login", "name": "Sign In", "url": "/login"}],
        "storage_mode": repo.storage_mode
    })


@frontend_router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form(None)
):
    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password.",
            "current_user": None,
            "nav_items": [{"id": "login", "name": "Sign In", "url": "/login"}],
            "storage_mode": repo.storage_mode
        }, status_code=401)

    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    redirect_target = next if next and next.startswith("/") else "/dashboard"
    response = RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return response


# =============================================================================
# Page 2: Role-Specific Dashboards
# =============================================================================
@frontend_router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login?next=/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    role = user["role"]
    ctx = get_base_context(request, "dashboard", user)

    if role == "ADMIN":
        metrics = repo.get_admin_dashboard_metrics()
        ctx["metrics"] = metrics
        return templates.TemplateResponse("dashboard_admin.html", ctx)

    elif role == "ANALYST":
        metrics = repo.get_analyst_dashboard_metrics(username=user["username"])
        ctx["metrics"] = metrics
        return templates.TemplateResponse("dashboard_analyst.html", ctx)

    elif role == "COMPLIANCE_REVIEWER":
        metrics = repo.get_compliance_dashboard_metrics()
        ctx["metrics"] = metrics
        return templates.TemplateResponse("dashboard_compliance.html", ctx)

    else:  # READ_ONLY
        metrics = repo.get_readonly_dashboard_metrics()
        ctx["metrics"] = metrics
        return templates.TemplateResponse("dashboard_readonly.html", ctx)


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
    user, err = require_html_permission(request, "view:transactions", "transactions")
    if err:
        return err

    txns, total = repo.get_transactions(page=page, page_size=20, search=search, transaction_type=type, status=status)
    ctx = get_base_context(request, "transactions", user)
    ctx.update({
        "transactions": txns,
        "total": total,
        "page": page,
        "page_size": 20,
        "search": search,
        "selected_type": type,
        "selected_status": status
    })
    return templates.TemplateResponse("transactions.html", ctx)


@frontend_router.get("/transactions/{transaction_id}", response_class=HTMLResponse)
def transaction_detail(request: Request, transaction_id: str):
    user, err = require_html_permission(request, "view:transactions", "transactions")
    if err:
        return err

    txn = repo.get_transaction_by_id(transaction_id)
    if not txn:
        return RedirectResponse(url="/transactions")

    cust = repo.get_customer_by_id(txn.get("customer_id", ""))
    src_acc = repo.get_account_by_id(txn.get("source_account_id", ""))
    dst_acc = repo.get_account_by_id(txn.get("destination_account_id", "")) if txn.get("destination_account_id") else None

    all_alerts, _ = repo.get_alerts(page_size=100)
    alerts = [a for a in all_alerts if transaction_id in a.get("triggered_transaction_ids", [])]

    ctx = get_base_context(request, "transactions", user)
    ctx.update({
        "transaction": txn,
        "customer": cust,
        "source_account": src_acc,
        "destination_account": dst_acc,
        "alerts": alerts
    })
    return templates.TemplateResponse("transaction_detail.html", ctx)


# =============================================================================
# Page 4: Customers & Accounts
# =============================================================================
@frontend_router.get("/customers", response_class=HTMLResponse)
def customers_list(request: Request, page: int = 1, search: Optional[str] = None, risk: Optional[str] = None):
    user, err = require_html_permission(request, "view:customers", "customers")
    if err:
        return err

    custs, total = repo.get_customers(page=page, page_size=20, search=search, risk_profile=risk)
    ctx = get_base_context(request, "customers", user)
    ctx.update({
        "customers": custs,
        "total": total,
        "page": page,
        "page_size": 20,
        "search": search,
        "selected_risk": risk
    })
    return templates.TemplateResponse("customers.html", ctx)


@frontend_router.get("/customers/{customer_id}", response_class=HTMLResponse)
def customer_detail(request: Request, customer_id: str):
    user, err = require_html_permission(request, "view:customers", "customers")
    if err:
        return err

    cust = repo.get_customer_by_id(customer_id)
    if not cust:
        return RedirectResponse(url="/customers")

    accounts, _ = repo.get_accounts(customer_id=customer_id, page_size=50)
    alerts, _ = repo.get_alerts(customer_id=customer_id, page_size=50)

    ctx = get_base_context(request, "customers", user)
    ctx.update({
        "customer": cust,
        "accounts": accounts,
        "alerts": alerts
    })
    return templates.TemplateResponse("customer_detail.html", ctx)


@frontend_router.get("/accounts", response_class=HTMLResponse)
def accounts_list(request: Request, page: int = 1, status: Optional[str] = None):
    user, err = require_html_permission(request, "view:accounts", "accounts")
    if err:
        return err

    accs, total = repo.get_accounts(page=page, page_size=20, status=status)
    ctx = get_base_context(request, "accounts", user)
    ctx.update({
        "accounts": accs,
        "total": total,
        "page": page,
        "page_size": 20,
        "selected_status": status
    })
    return templates.TemplateResponse("accounts.html", ctx)


@frontend_router.get("/accounts/{account_id}", response_class=HTMLResponse)
def account_detail(request: Request, account_id: str):
    user, err = require_html_permission(request, "view:accounts", "accounts")
    if err:
        return err

    acc = repo.get_account_by_id(account_id)
    if not acc:
        return RedirectResponse(url="/accounts")

    cust = repo.get_customer_by_id(acc.get("customer_id", ""))
    txns, _ = repo.get_transactions(account_id=account_id, page_size=20)

    ctx = get_base_context(request, "accounts", user)
    ctx.update({
        "account": acc,
        "customer": cust,
        "transactions": txns
    })
    return templates.TemplateResponse("account_detail.html", ctx)


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
    user, err = require_html_permission(request, "view:alerts", "alerts")
    if err:
        return err

    alts, total = repo.get_alerts(page=page, page_size=20, severity=severity, status=status)
    ctx = get_base_context(request, "alerts", user)
    ctx.update({
        "alerts": alts,
        "total": total,
        "page": page,
        "page_size": 20,
        "selected_severity": severity,
        "selected_status": status
    })
    return templates.TemplateResponse("alerts.html", ctx)


@frontend_router.get("/alerts/{alert_id}", response_class=HTMLResponse)
def alert_detail(request: Request, alert_id: str):
    user, err = require_html_permission(request, "view:alerts", "alerts")
    if err:
        return err

    alt = repo.get_alert_by_id(alert_id)
    if not alt:
        return RedirectResponse(url="/alerts")

    triggered_txns = []
    for tid in alt.get("triggered_transaction_ids", []):
        t = repo.get_transaction_by_id(tid)
        if t:
            triggered_txns.append(t)

    cases, _ = repo.get_cases(page_size=50)
    linked_cases = [c for c in cases if alert_id in c.get("alert_ids", [])]

    ctx = get_base_context(request, "alerts", user)
    ctx.update({
        "alert": alt,
        "triggering_transactions": triggered_txns,
        "linked_cases": linked_cases
    })
    return templates.TemplateResponse("alert_detail.html", ctx)


@frontend_router.post("/alerts/{alert_id}/status")
def alert_status_post(request: Request, alert_id: str, status: str = Form(...)):
    user, err = require_html_permission(request, "edit:alerts", "alerts")
    if err:
        return err

    repo.update_alert_status(alert_id, status.upper(), actor_id=user["username"])
    return RedirectResponse(url=f"/alerts/{alert_id}", status_code=303)


# =============================================================================
# Page 6: Cases & Case Detail
# =============================================================================
@frontend_router.get("/cases", response_class=HTMLResponse)
def cases_list(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    filter: Optional[str] = None
):
    user, err = require_html_permission(request, "view:cases", "cases")
    if err:
        return err

    assigned_id = user["username"] if filter == "my_cases" else None
    cases, total = repo.get_cases(page=page, page_size=20, status=status, priority=priority, assigned_analyst_id=assigned_id)

    ctx = get_base_context(request, "cases", user)
    ctx.update({
        "cases": cases,
        "total": total,
        "page": page,
        "page_size": 20,
        "selected_status": status,
        "selected_priority": priority,
        "filter": filter
    })
    return templates.TemplateResponse("cases.html", ctx)


@frontend_router.get("/cases/workspace", response_class=HTMLResponse)
def workspace_view(request: Request):
    user, err = require_html_permission(request, "view:workspace", "workspace")
    if err:
        return err

    all_cases, _ = repo.get_cases(page_size=100)
    my_cases = [c for c in all_cases if str(c.get("assigned_analyst_id", "")).lower() == user["username"].lower() and c.get("case_status") in ["OPEN", "IN_PROGRESS"]]

    ctx = get_base_context(request, "workspace", user)
    ctx.update({
        "my_cases": my_cases
    })
    return templates.TemplateResponse("workspace.html", ctx)


@frontend_router.post("/cases")
def create_case_post(
    request: Request,
    alert_id: str = Form(...),
    customer_id: str = Form(...),
    case_title: str = Form(...),
    priority: str = Form("MEDIUM")
):
    user, err = require_html_permission(request, "create:cases", "cases")
    if err:
        return err

    case_doc = repo.create_case(
        case_title=case_title,
        description=f"Investigation opened for alert {alert_id}",
        priority=priority.upper(),
        alert_ids=[alert_id],
        customer_id=customer_id,
        assigned_analyst_id=user["username"],
        actor_id=user["username"]
    )
    return RedirectResponse(url=f"/cases/{case_doc['case_id']}", status_code=303)


@frontend_router.get("/cases/{case_id}", response_class=HTMLResponse)
def case_detail(request: Request, case_id: str):
    user, err = require_html_permission(request, "view:cases", "cases")
    if err:
        return err

    c = repo.get_case_by_id(case_id)
    if not c:
        return RedirectResponse(url="/cases")

    actions = repo.get_actions_by_case(case_id)
    alerts = []
    for a_id in c.get("alert_ids", []):
        alt = repo.get_alert_by_id(a_id)
        if alt:
            alerts.append(alt)

    ctx = get_base_context(request, "cases", user)
    ctx.update({
        "case": c,
        "alerts": alerts,
        "actions_timeline": actions
    })
    return templates.TemplateResponse("case_detail.html", ctx)


@frontend_router.post("/cases/{case_id}/action")
def case_action_post(
    request: Request,
    case_id: str,
    action_type: str = Form(...),
    comment: str = Form(...),
    new_status: Optional[str] = Form(None)
):
    user, err = require_html_permission(request, "edit:cases", "cases")
    if err:
        return err

    c = repo.get_case_by_id(case_id)
    if not c:
        return RedirectResponse(url="/cases")

    repo.add_analyst_action(
        case_id=case_id,
        analyst_id=user["username"],
        action_type=action_type.upper(),
        comment=comment,
        new_status=new_status.upper() if new_status else None
    )
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@frontend_router.post("/cases/{case_id}/disposition")
def case_disposition_post(
    request: Request,
    case_id: str,
    disposition: str = Form(...),
    reason: str = Form(...)
):
    user, err = require_html_permission(request, "disposition:cases", "cases")
    if err:
        return err

    c = repo.get_case_by_id(case_id)
    if not c:
        return RedirectResponse(url="/cases")

    disp = disposition.upper()
    repo.add_analyst_action(
        case_id=case_id,
        analyst_id=user["username"],
        action_type="DISPOSITION_RECORDED",
        comment=reason,
        new_status="CLOSED" if disp != "ESCALATED" else "PENDING_REVIEW",
        disposition=disp
    )
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


# =============================================================================
# Page 7: Risk Rules (ADMIN only for edit, catalog view for authorized)
# =============================================================================
@frontend_router.get("/rules", response_class=HTMLResponse)
def rules_list(request: Request):
    user, err = require_html_permission(request, "view:rules", "rules")
    if err:
        return err

    rules = repo.get_rules()
    ctx = get_base_context(request, "rules", user)
    ctx.update({"rules": rules})
    return templates.TemplateResponse("rules.html", ctx)


@frontend_router.get("/rules/{rule_id}", response_class=HTMLResponse)
def rule_detail(request: Request, rule_id: str):
    user, err = require_html_permission(request, "view:rules", "rules")
    if err:
        return err

    rule = repo.get_rule_by_id(rule_id)
    if not rule:
        return RedirectResponse(url="/rules")

    ctx = get_base_context(request, "rules", user)
    ctx.update({"rule": rule})
    return templates.TemplateResponse("rule_detail.html", ctx)


@frontend_router.post("/rules/{rule_id}/update")
def rule_update_post(
    request: Request,
    rule_id: str,
    severity: str = Form(...),
    weight: float = Form(...),
    threshold: float = Form(...),
    enabled: str = Form(...)
):
    user, err = require_html_permission(request, "edit:rules", "rules")
    if err:
        return err

    repo.update_rule(rule_id, {
        "severity": severity,
        "weight": weight,
        "threshold": threshold,
        "enabled": (enabled.lower() == "true")
    }, actor_id=user["username"])
    return RedirectResponse(url=f"/rules/{rule_id}", status_code=303)


# =============================================================================
# Page 8: Data Quality & Validation
# =============================================================================
@frontend_router.get("/validation", response_class=HTMLResponse)
def validation_view(request: Request):
    user, err = require_html_permission(request, "view:validation", "validation")
    if err:
        return err

    val_file = os.path.join(settings.REPORTS_DIR, "validation_summary.json")
    report = {}
    if os.path.isfile(val_file):
        with open(val_file, "r", encoding="utf-8") as f:
            report = json.load(f)

    ctx = get_base_context(request, "validation", user)
    ctx.update({"report": report})
    return templates.TemplateResponse("validation.html", ctx)


@frontend_router.post("/validation/run")
def run_validation_post(request: Request):
    user, err = require_html_permission(request, "run:validation", "validation")
    if err:
        return err

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
    user, err = require_html_permission(request, "view:evaluation", "evaluation")
    if err:
        return err

    eval_file = os.path.join(settings.REPORTS_DIR, "evaluation_summary.json")
    report = {}
    if os.path.isfile(eval_file):
        with open(eval_file, "r", encoding="utf-8") as f:
            report = json.load(f)

    ctx = get_base_context(request, "evaluation", user)
    ctx.update({"report": report})
    return templates.TemplateResponse("evaluation.html", ctx)


@frontend_router.post("/evaluation/run")
def run_evaluation_post(request: Request):
    user, err = require_html_permission(request, "run:evaluation", "evaluation")
    if err:
        return err

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
# Page 10: Data Generation & Exports (ADMIN only)
# =============================================================================
@frontend_router.get("/generator", response_class=HTMLResponse)
def generator_view(request: Request):
    user, err = require_html_permission(request, "view:generator", "generator")
    if err:
        return err

    manifest_path = os.path.join(settings.DATASET_EXPORT_DIR, "manifest.json")
    manifest = {}
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    ctx = get_base_context(request, "generator", user)
    ctx.update({"manifest": manifest})
    return templates.TemplateResponse("generator.html", ctx)


@frontend_router.post("/generator/run")
def run_generator_post(request: Request, profile: str = Form("demo"), seed: int = Form(20261022)):
    user, err = require_html_permission(request, "run:generator", "generator")
    if err:
        return err

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
    user, err = require_html_permission(request, "view:audit", "audit")
    if err:
        return err

    events, total = repo.get_audit_events(page=page, page_size=25, entity_type=entity_type)
    ctx = get_base_context(request, "audit", user)
    ctx.update({
        "audit_events": events,
        "total": total,
        "page": page,
        "page_size": 25,
        "selected_entity": entity_type
    })
    return templates.TemplateResponse("audit.html", ctx)


# =============================================================================
# Page 12: User Management (ADMIN only)
# =============================================================================
@frontend_router.get("/users", response_class=HTMLResponse)
def users_view(request: Request, msg: Optional[str] = None):
    user, err = require_html_permission(request, "manage:users", "users")
    if err:
        return err

    users = repo.get_all_users()
    ctx = get_base_context(request, "users", user)
    ctx.update({"users": users, "msg": msg})
    return templates.TemplateResponse("users.html", ctx)


@frontend_router.post("/users/{username}/role")
def user_role_update_post(request: Request, username: str, new_role: str = Form(...)):
    user, err = require_html_permission(request, "manage:users", "users")
    if err:
        return err

    norm_role = new_role.upper().strip()
    if norm_role in VALID_ROLES:
        repo.update_user_role(username, norm_role, actor_id=user["username"])
        return RedirectResponse(url=f"/users?msg=Role+for+{username}+updated+to+{norm_role}", status_code=303)

    return RedirectResponse(url=f"/users?msg=Invalid+role+specified", status_code=303)


# =============================================================================
# Page 13: System Settings (ADMIN only)
# =============================================================================
@frontend_router.get("/settings", response_class=HTMLResponse)
def settings_view(request: Request):
    user, err = require_html_permission(request, "manage:system", "settings")
    if err:
        return err

    ctx = get_base_context(request, "settings", user)
    ctx.update({"config": settings})
    return templates.TemplateResponse("settings.html", ctx)


# =============================================================================
# Page 14: Reports & Exports (COMPLIANCE_REVIEWER and READ_ONLY)
# =============================================================================
@frontend_router.get("/reports", response_class=HTMLResponse)
def reports_view(request: Request):
    user, err = require_html_permission(request, "view:reports", "reports")
    if err:
        return err

    ctx = get_base_context(request, "reports", user)
    return templates.TemplateResponse("reports.html", ctx)
