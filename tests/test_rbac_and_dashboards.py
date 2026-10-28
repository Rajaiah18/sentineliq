"""
SentinelIQ RBAC & Role-Specific Dashboard Test Suite
Validates server-side authorization, navigation isolation, template contexts,
API write protection, and IDOR prevention across all 4 roles:
- ADMIN
- ANALYST
- COMPLIANCE_REVIEWER
- READ_ONLY
"""
import pytest
from fastapi import HTTPException, status
from starlette.requests import Request
from starlette.responses import RedirectResponse

from backend.app.database.repository import repo
from backend.app.security.auth import create_access_token
from backend.app.security.permissions import (
    get_navigation_for_role,
    normalize_role,
    has_permission,
    require_roles,
    RequireAdmin,
    RequireAnalyst,
    RequireCompliance,
    RequireReadWrite,
    VALID_ROLES
)
from backend.app.api.v1.rules import update_rule, RuleUpdateRequest
from backend.app.api.v1.operations import trigger_generation_run, GenerationRunRequest
from backend.app.api.v1.alerts import update_alert_status, AlertStatusUpdate
from backend.app.api.v1.cases import create_case, CreateCaseRequest, record_case_disposition, DispositionRequest, add_case_action, CaseActionRequest
from backend.app.api.v1.auth import modify_user_role, RoleUpdateRequest
from frontend.routes import require_html_permission, get_session_user, get_base_context


def make_dummy_request(headers=None, cookies=None, path="/dashboard") -> Request:
    """Construct an ASGI Request object without binding network sockets."""
    hdr_list = []
    if headers:
        for k, v in headers.items():
            hdr_list.append((k.lower().encode("utf-8"), v.encode("utf-8")))
    if cookies:
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        hdr_list.append((b"cookie", cookie_str.encode("utf-8")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": hdr_list
    }
    return Request(scope)


# =============================================================================
# 1. Navigation Menu Tests by Role
# =============================================================================
def test_admin_navigation_items():
    nav = get_navigation_for_role("ADMIN")
    nav_ids = [item["id"] for item in nav]
    assert "dashboard" in nav_ids
    assert "rules" in nav_ids
    assert "generator" in nav_ids
    assert "users" in nav_ids
    assert "settings" in nav_ids
    assert "audit" in nav_ids
    assert len(nav) == 13


def test_analyst_navigation_items():
    nav = get_navigation_for_role("ANALYST")
    nav_ids = [item["id"] for item in nav]
    assert "dashboard" in nav_ids
    assert "cases" in nav_ids
    assert "workspace" in nav_ids
    assert "alerts" in nav_ids
    # Must NOT contain admin or generation items
    assert "rules" not in nav_ids
    assert "generator" not in nav_ids
    assert "users" not in nav_ids
    assert "settings" not in nav_ids
    assert len(nav) == 7


def test_compliance_navigation_items():
    nav = get_navigation_for_role("COMPLIANCE_REVIEWER")
    nav_ids = [item["id"] for item in nav]
    assert "dashboard" in nav_ids
    assert "cases" in nav_ids
    assert "audit" in nav_ids
    assert "validation" in nav_ids
    assert "evaluation" in nav_ids
    assert "reports" in nav_ids
    # Must NOT contain administration or generation
    assert "rules" not in nav_ids
    assert "generator" not in nav_ids
    assert "users" not in nav_ids
    assert len(nav) == 7


def test_readonly_navigation_items():
    nav = get_navigation_for_role("READ_ONLY")
    nav_ids = [item["id"] for item in nav]
    assert "dashboard" in nav_ids
    assert "transactions" in nav_ids
    assert "customers" in nav_ids
    assert "accounts" in nav_ids
    assert "alerts" in nav_ids
    assert "cases" in nav_ids
    assert "reports" in nav_ids
    # Strictly read-only: no admin or mutation tools
    assert "rules" not in nav_ids
    assert "generator" not in nav_ids
    assert "users" not in nav_ids
    assert "workspace" not in nav_ids
    assert len(nav) == 7


# =============================================================================
# 2. Server-Side Role Normalization & Session Extraction
# =============================================================================
def test_role_normalization_fails_closed():
    assert normalize_role("admin") == "ADMIN"
    assert normalize_role("ANALYST") == "ANALYST"
    assert normalize_role("compliance_reviewer") == "COMPLIANCE_REVIEWER"
    assert normalize_role("Read_Only") == "READ_ONLY"
    # Unrecognized or malicious roles fail closed to READ_ONLY
    assert normalize_role("SUPERUSER") == "READ_ONLY"
    assert normalize_role("") == "READ_ONLY"
    assert normalize_role(None) == "READ_ONLY"


def test_unauthenticated_user_session():
    req = make_dummy_request()
    user = get_session_user(req)
    assert user is None


def test_authenticated_user_session_from_cookie():
    token = create_access_token(data={"sub": "analyst", "role": "ANALYST"})
    req = make_dummy_request(cookies={"access_token": token})
    user = get_session_user(req)
    assert user is not None
    assert user["username"] == "analyst"
    assert user["role"] == "ANALYST"


# =============================================================================
# 3. HTML Route Permission Enforcement (Redirect vs 403 Forbidden)
# =============================================================================
def test_unauthenticated_request_redirects_to_login():
    req = make_dummy_request(path="/rules")
    user, resp = require_html_permission(req, "view:rules", "rules")
    assert user is None
    assert isinstance(resp, RedirectResponse)
    assert "/login" in resp.headers["location"]


def test_analyst_cannot_access_rules_html():
    token = create_access_token(data={"sub": "analyst", "role": "ANALYST"})
    req = make_dummy_request(cookies={"access_token": token}, path="/rules")
    user, resp = require_html_permission(req, "view:rules", "rules")
    assert user is not None
    # Must return 403 Forbidden page
    assert resp.status_code == 403


def test_compliance_cannot_access_generator_html():
    token = create_access_token(data={"sub": "compliance", "role": "COMPLIANCE_REVIEWER"})
    req = make_dummy_request(cookies={"access_token": token}, path="/generator")
    user, resp = require_html_permission(req, "view:generator", "generator")
    assert user is not None
    assert resp.status_code == 403


def test_admin_can_access_rules_and_generator_html():
    token = create_access_token(data={"sub": "admin", "role": "ADMIN"})
    req = make_dummy_request(cookies={"access_token": token}, path="/rules")
    user, resp = require_html_permission(req, "view:rules", "rules")
    assert user is not None
    assert resp is None  # Allowed


# =============================================================================
# 4. Role-Specific Dashboard Metrics Integrity
# =============================================================================
def test_admin_dashboard_metrics_structure():
    metrics = repo.get_admin_dashboard_metrics()
    assert "total_customers" in metrics
    assert "total_accounts" in metrics
    assert "total_rules" in metrics
    assert "active_rules" in metrics
    assert "db_healthy" in metrics
    assert "recent_audit_events" in metrics


def test_analyst_dashboard_metrics_structure():
    metrics = repo.get_analyst_dashboard_metrics(username="analyst")
    assert "my_open_cases_count" in metrics
    assert "unassigned_cases_count" in metrics
    assert "new_alerts_count" in metrics
    assert "urgent_alerts" in metrics
    assert "cases_under_24h" in metrics


def test_compliance_dashboard_metrics_structure():
    metrics = repo.get_compliance_dashboard_metrics()
    assert "pending_review_count" in metrics
    assert "escalated_cases_count" in metrics
    assert "confirmed_suspicious_count" in metrics
    assert "false_positives_count" in metrics
    assert "eval_f1" in metrics
    assert "val_checks_pass" in metrics


def test_readonly_dashboard_metrics_structure():
    metrics = repo.get_readonly_dashboard_metrics()
    assert "total_customers" in metrics
    assert "total_volume_usd" in metrics
    assert "alert_rate_percent" in metrics
    assert "channel_dist" in metrics


# =============================================================================
# 5. Backend API Authorization & Write Protection
# =============================================================================
def test_admin_can_update_rules():
    rules = repo.get_rules()
    assert len(rules) > 0
    rule_id = rules[0]["rule_id"]

    admin_user = {"username": "admin", "role": "ADMIN"}
    res = update_rule(rule_id, RuleUpdateRequest(weight=65.0), user=admin_user)
    assert res is not None
    assert res["weight"] == 65.0


def test_non_admin_cannot_update_rules():
    analyst_checker = require_roles(["ADMIN"])
    analyst_user = {"username": "analyst", "role": "ANALYST"}
    with pytest.raises(HTTPException) as exc:
        analyst_checker(analyst_user)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_compliance_cannot_trigger_dataset_generation():
    gen_checker = require_roles(["ADMIN"])
    compliance_user = {"username": "compliance", "role": "COMPLIANCE_REVIEWER"}
    with pytest.raises(HTTPException) as exc:
        gen_checker(compliance_user)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_analyst_can_create_case_and_update_alert_status():
    analyst_user = {"username": "analyst", "user_id": "USR-ANALYST-01", "role": "ANALYST"}
    alerts, _ = repo.get_alerts(page_size=1)
    assert len(alerts) > 0
    target_alert_id = alerts[0]["alert_id"]
    target_customer_id = alerts[0]["customer_id"]

    # Triage alert
    updated_alert = update_alert_status(target_alert_id, AlertStatusUpdate(alert_status="UNDER_REVIEW"), user=analyst_user)
    assert updated_alert["alert_status"] == "UNDER_REVIEW"

    # Create case
    case_req = CreateCaseRequest(
        case_title="Test Analyst Case",
        description="Testing analyst creation",
        priority="HIGH",
        alert_ids=[target_alert_id],
        customer_id=target_customer_id
    )
    case_res = create_case(case_req, user=analyst_user)
    assert case_res["case_title"] == "Test Analyst Case"


def test_readonly_cannot_create_or_modify_cases():
    write_checker = require_roles(["ADMIN", "ANALYST"])
    readonly_user = {"username": "readonly", "role": "READ_ONLY"}
    with pytest.raises(HTTPException) as exc:
        write_checker(readonly_user)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_compliance_can_record_disposition():
    compliance_user = {"username": "compliance", "user_id": "USR-COMPLIANCE-01", "role": "COMPLIANCE_REVIEWER"}
    # Grab an existing case
    cases, _ = repo.get_cases(page_size=1)
    if cases:
        c_id = cases[0]["case_id"]
        disp_req = DispositionRequest(disposition="CONFIRMED_SUSPICIOUS", reason="Verified multi-hop laundering pattern.")
        res = record_case_disposition(c_id, disp_req, user=compliance_user)
        assert res["status"] == "success"
        assert res["disposition"] == "CONFIRMED_SUSPICIOUS"


def test_analyst_cannot_record_final_disposition():
    disp_checker = require_roles(["ADMIN", "COMPLIANCE_REVIEWER"])
    analyst_user = {"username": "analyst", "role": "ANALYST"}
    with pytest.raises(HTTPException) as exc:
        disp_checker(analyst_user)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# 6. User Role Management & Privilege Elevation Defense
# =============================================================================
def test_admin_can_modify_user_role():
    admin_user = {"username": "admin", "role": "ADMIN"}
    res = modify_user_role("readonly", RoleUpdateRequest(role="ANALYST"), admin=admin_user)
    assert res["status"] == "success"
    assert res["user"]["role"] == "ANALYST"

    # Verify updated role is immediately reflected from repository
    user = repo.get_user_by_username("readonly")
    assert user["role"] == "ANALYST"

    # Restore back to READ_ONLY for clean state
    repo.update_user_role("readonly", "READ_ONLY", actor_id="ADMIN")


def test_non_admin_cannot_modify_user_role():
    admin_checker = require_roles(["ADMIN"])
    analyst_user = {"username": "analyst", "role": "ANALYST"}
    with pytest.raises(HTTPException) as exc:
        admin_checker(analyst_user)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# 7. IDOR Protection (Non-existent or Unauthorized Resources)
# =============================================================================
def test_case_action_on_nonexistent_case_fails():
    analyst_user = {"username": "analyst", "user_id": "USR-ANALYST-01", "role": "ANALYST"}
    act_req = CaseActionRequest(action_type="NOTE_ADDED", comment="Investigating invalid case")
    with pytest.raises(HTTPException) as exc:
        add_case_action("CASE-INVALID-999999", act_req, user=analyst_user)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


def test_case_disposition_on_nonexistent_case_fails():
    compliance_user = {"username": "compliance", "user_id": "USR-COMPLIANCE-01", "role": "COMPLIANCE_REVIEWER"}
    disp_req = DispositionRequest(disposition="CONFIRMED_SUSPICIOUS", reason="Testing invalid ID")
    with pytest.raises(HTTPException) as exc:
        record_case_disposition("CASE-NONEXISTENT-999999", disp_req, user=compliance_user)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
