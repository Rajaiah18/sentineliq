"""
SentinelIQ API Handler Integration Tests
Directly tests API v1 endpoints, request validation, business logic, and repository integration.
"""
import pytest
from fastapi import HTTPException
from backend.app.api.v1.auth import login, get_profile, LoginRequest
from backend.app.api.v1.metrics import get_overview, get_alert_metrics, get_case_metrics
from backend.app.api.v1.customers import list_customers, get_customer, list_accounts, get_account
from backend.app.api.v1.transactions import list_transactions, get_transaction
from backend.app.api.v1.alerts import list_alerts, get_alert, update_alert_status, AlertStatusUpdate
from backend.app.api.v1.cases import list_cases, create_case, get_case, add_case_action, record_case_disposition, CreateCaseRequest, CaseActionRequest, DispositionRequest
from backend.app.api.v1.rules import list_rules, get_rule, update_rule, execute_rule_test, RuleUpdateRequest, RuleTestRequest
from backend.app.api.v1.operations import list_available_exports, list_audit_log
from backend.app.database.repository import repo
from backend.app.security.auth import get_demo_users


def test_auth_login_success():
    req = LoginRequest(username="admin", password="SentinelIQ@Admin2026!")
    from fastapi import Response
    res = login(req, Response())
    assert res.token_type == "bearer"
    assert res.role == "ADMIN"
    assert len(res.access_token) > 20


def test_auth_login_invalid():
    req = LoginRequest(username="admin", password="WrongPassword!")
    from fastapi import Response
    with pytest.raises(HTTPException) as exc:
        login(req, Response())
    assert exc.value.status_code == 401


def test_metrics_endpoints():
    overview = get_overview()
    assert "total_customers" in overview
    assert "total_alerts" in overview

    alert_metrics = get_alert_metrics()
    assert "by_severity" in alert_metrics
    assert "by_status" in alert_metrics

    case_metrics = get_case_metrics()
    assert "open_cases" in case_metrics
    assert "by_status" in case_metrics


def test_customers_and_accounts_api():
    cust_res = list_customers(page=1, page_size=10)
    assert "data" in cust_res
    assert "total" in cust_res

    acc_res = list_accounts(page=1, page_size=10)
    assert "data" in acc_res
    assert "total" in acc_res


def test_transactions_and_alerts_api():
    txn_res = list_transactions(page=1, page_size=10)
    assert "data" in txn_res
    assert "total" in txn_res

    alt_res = list_alerts(page=1, page_size=10)
    assert "data" in alt_res
    assert "total" in alt_res


def test_alert_detail_and_status_patch():
    alerts_data, _ = repo.get_alerts(page_size=1)
    if alerts_data:
        target_alert = alerts_data[0]
        a_id = target_alert["alert_id"]

        detail = get_alert(a_id)
        assert detail["alert"]["alert_id"] == a_id
        assert "customer" in detail

        # Update status
        updated = update_alert_status(
            alert_id=a_id,
            payload=AlertStatusUpdate(alert_status="UNDER_REVIEW"),
            user=get_demo_users()["analyst"]
        )
        assert updated["alert_status"] == "UNDER_REVIEW"


def test_case_lifecycle_api():
    # 1. Create Case
    alerts_data, _ = repo.get_alerts(page_size=1)
    a_id = alerts_data[0]["alert_id"] if alerts_data else "ALT-2026-000001"
    
    # Ensure alert exists in memory if empty
    if not alerts_data:
        repo._memory_store["alerts"][a_id] = {
            "alert_id": a_id, "title": "Test", "severity": "HIGH", "risk_score": 80.0,
            "alert_status": "NEW", "customer_id": "CUS-000001", "created_at": "2026-01-01T00:00:00Z"
        }

    case_payload = CreateCaseRequest(
        case_title="API Test Investigation",
        description="Created via pytest API suite",
        priority="HIGH",
        alert_ids=[a_id],
        customer_id="CUS-000001"
    )
    created_case = create_case(case_payload, user=get_demo_users()["analyst"])
    case_id = created_case["case_id"]
    assert created_case["case_status"] == "OPEN"

    # 2. Add Analyst Action
    action_payload = CaseActionRequest(
        action_type="NOTE_ADDED",
        comment="Reviewed initial transaction logs.",
        new_status="IN_PROGRESS"
    )
    action = add_case_action(case_id, action_payload, user=get_demo_users()["analyst"])
    assert action["action_type"] == "NOTE_ADDED"
    assert action["new_status"] == "IN_PROGRESS"

    # 3. Retrieve Case Detail
    detail = get_case(case_id)
    assert detail["case"]["case_status"] == "IN_PROGRESS"
    assert len(detail["actions_timeline"]) >= 1

    # 4. Record Disposition
    disp_payload = DispositionRequest(
        disposition="CONFIRMED_SUSPICIOUS",
        reason="Layering and circular transfer activity verified."
    )
    disp_res = record_case_disposition(case_id, disp_payload, user=get_demo_users()["compliance"])
    assert disp_res["status"] == "success"
    assert disp_res["disposition"] == "CONFIRMED_SUSPICIOUS"


def test_rules_api_and_testing():
    rules_res = list_rules()
    assert len(rules_res["data"]) >= 12

    rule = get_rule("RULE-HIGH-VALUE")
    assert rule["rule_id"] == "RULE-HIGH-VALUE"

    # Rule Testing
    test_req = RuleTestRequest(
        transaction={"transaction_id": "TXN-TEST", "amount": 25000.0, "currency": "USD", "transaction_timestamp": "2026-01-01T00:00:00Z"},
        account={"account_id": "ACC-01", "account_status": "OPEN", "current_balance": 50000.0, "overdraft_limit": 0.0},
        customer={"customer_id": "CUS-01", "risk_profile": "LOW"}
    )
    test_result = execute_rule_test("RULE-HIGH-VALUE", test_req)
    assert test_result["triggered"] is True


def test_exports_and_audit_api():
    exports = list_available_exports()
    assert "exports" in exports

    audit = list_audit_log(page=1, page_size=10)
    assert "data" in audit
    assert "total" in audit
