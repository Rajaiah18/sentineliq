"""
SentinelIQ Unit Tests: Domain Models & Pydantic Validation
"""
import pytest
from pydantic import ValidationError
from backend.app.models import (
    Customer, Account, Merchant, Device, Transaction,
    TransferLink, RiskRule, Alert, Case, AnalystAction, AuditEvent, GroundTruth
)


def test_customer_model_valid():
    c = Customer(
        customer_id="CUS-000001",
        first_name="Alexander",
        last_name="Sterling",
        date_of_birth="1985-04-12",
        customer_type="INDIVIDUAL",
        risk_profile="LOW",
        country_code="US",
        customer_status="ACTIVE",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z"
    )
    assert c.customer_id == "CUS-000001"
    d = c.to_mongo_dict()
    assert d["first_name"] == "Alexander"


def test_customer_model_missing_field():
    with pytest.raises(ValidationError):
        Customer(
            customer_id="CUS-000001",
            first_name="Alexander",
            # missing last_name
            date_of_birth="1985-04-12",
            customer_type="INDIVIDUAL",
            risk_profile="LOW",
            country_code="US",
            customer_status="ACTIVE",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z"
        )


def test_account_model_valid():
    a = Account(
        account_id="ACC-CUS-000001-01",
        customer_id="CUS-000001",
        account_type="CHECKING",
        currency="USD",
        opening_balance=5000.0,
        current_balance=4200.50,
        overdraft_limit=1000.0,
        account_status="OPEN",
        opened_at="2026-01-01T00:00:00Z",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z"
    )
    assert a.account_id == "ACC-CUS-000001-01"
    assert a.closed_at is None


def test_transaction_model_negative_amount_fails():
    with pytest.raises(ValidationError):
        Transaction(
            transaction_id="TXN-2026-00000001",
            source_account_id="ACC-01",
            customer_id="CUS-01",
            transaction_type="CARD_PAYMENT",
            amount=-50.0,  # Negative amount must fail (gt=0.0)
            currency="USD",
            transaction_status="COMPLETED",
            transaction_timestamp="2026-01-01T12:00:00Z",
            channel="POS",
            reference_id="REF-01",
            created_at="2026-01-01T12:00:00Z"
        )


def test_alert_model_valid():
    alt = Alert(
        alert_id="ALT-2026-000001",
        alert_type="SUSPICIOUS_ACTIVITY",
        title="High Value Anomaly",
        description="Transaction exceeds threshold",
        severity="HIGH",
        risk_score=85.0,
        alert_status="NEW",
        triggered_transaction_ids=["TXN-2026-00000001"],
        customer_id="CUS-000001",
        account_ids=["ACC-01"],
        triggered_rule_ids=["RULE-HIGH-VALUE"],
        reason_codes=["THRESHOLD_EXCEEDED"],
        explanation="Single transaction of $50,000 exceeded threshold.",
        evidence={"amount": 50000.0},
        created_at="2026-01-01T12:00:00Z",
        updated_at="2026-01-01T12:00:00Z"
    )
    assert alt.risk_score == 85.0
    assert len(alt.triggered_transaction_ids) == 1
