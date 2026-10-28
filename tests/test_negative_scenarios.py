"""
SentinelIQ Tests: Five Mandatory Negative Scenarios
Explicitly tests detection and validation reporting for:
Scenario 1: Transaction references a closed account.
Scenario 2: Negative balance beyond allowed overdraft limit.
Scenario 3: Transfer legs do not reconcile.
Scenario 4: Alert has no triggering transaction.
Scenario 5: Case disposition precedes alert creation.
"""
import pytest
from risk_engine.engine import RiskEngine
from validation.checks import DataValidator
from risk_engine.rules import DEFAULT_RULES


def test_scenario_1_closed_account_detected():
    """Scenario 1: Transaction posted against closed account."""
    engine = RiskEngine()
    txn = {
        "transaction_id": "TXN-SCEN-1",
        "source_account_id": "ACC-CLOSED-01",
        "customer_id": "CUS-01",
        "amount": 500.0,
        "currency": "USD",
        "transaction_timestamp": "2026-03-15T12:00:00Z"
    }
    acc = {
        "account_id": "ACC-CLOSED-01",
        "account_status": "CLOSED",
        "closed_at": "2026-02-01T00:00:00Z",
        "current_balance": 0.0,
        "overdraft_limit": 0.0
    }
    cust = {"customer_id": "CUS-01", "risk_profile": "LOW"}

    results = engine.evaluate_transaction(txn, acc, cust)
    closed_triggers = [r for r in results if r.rule_id == "RULE-CLOSED-ACCOUNT"]
    assert len(closed_triggers) == 1
    assert closed_triggers[0].triggered is True
    assert closed_triggers[0].reason_code == "ERR_CLOSED_ACCOUNT_POSTING"


def test_scenario_2_negative_balance_exceeds_overdraft_detected():
    """Scenario 2: Balance plunged into negative beyond permitted overdraft limit."""
    engine = RiskEngine()
    overdraft_limit = 500.0
    balance_after = -850.0  # Deficit exceeds overdraft by $350.00
    txn = {
        "transaction_id": "TXN-SCEN-2",
        "source_account_id": "ACC-OD-01",
        "customer_id": "CUS-01",
        "amount": 1000.0,
        "balance_after": balance_after,
        "currency": "USD",
        "transaction_timestamp": "2026-03-15T12:00:00Z"
    }
    acc = {
        "account_id": "ACC-OD-01",
        "account_status": "OPEN",
        "current_balance": 150.0,
        "overdraft_limit": overdraft_limit
    }
    cust = {"customer_id": "CUS-01", "risk_profile": "LOW"}

    results = engine.evaluate_transaction(txn, acc, cust)
    overdraft_triggers = [r for r in results if r.rule_id == "RULE-OVERDRAFT-EXCEEDED"]
    assert len(overdraft_triggers) == 1
    assert overdraft_triggers[0].triggered is True
    assert overdraft_triggers[0].reason_code == "BREACH_OVERDRAFT_LIMIT"
    assert overdraft_triggers[0].evidence["excess_deficit"] == 350.0


def test_scenario_3_transfer_legs_do_not_reconcile():
    """Scenario 3: Outgoing and incoming transfer legs disagree in amount and currency."""
    engine = RiskEngine()
    src_txn = {
        "transaction_id": "TXN-SRC-01",
        "source_account_id": "ACC-01",
        "destination_account_id": "ACC-02",
        "amount": 10000.0,
        "currency": "USD"
    }
    dest_txn = {
        "transaction_id": "TXN-DST-01",
        "source_account_id": "ACC-02",
        "destination_account_id": "ACC-01",
        "amount": 9500.0,  # Mismatched amount
        "currency": "EUR"   # Mismatched currency
    }
    link = {
        "transfer_link_id": "TRL-SCEN-3",
        "source_transaction_id": "TXN-SRC-01",
        "destination_transaction_id": "TXN-DST-01",
        "source_account_id": "ACC-01",
        "destination_account_id": "ACC-02"
    }

    res = engine.evaluate_transfer_reconciliation(src_txn, dest_txn, link)
    assert res is not None
    assert res.triggered is True
    assert res.rule_id == "RULE-TRANSFER-MISMATCH"
    assert "Amount mismatch" in res.explanation
    assert "Currency mismatch" in res.explanation


def test_scenario_4_alert_no_triggering_transaction_reported():
    """Scenario 4: Alert without triggering transactions is reported as data integrity fault."""
    engine = RiskEngine()
    res = engine.evaluate_alert_integrity("ALT-ORPHAN-01", [])
    assert res is not None
    assert res.triggered is True
    assert res.rule_id == "RULE-ALERT-NO-TXN"
    assert res.reason_code == "INTEGRITY_ORPHANED_ALERT"


def test_scenario_5_case_disposition_precedes_alert_reported():
    """Scenario 5: Case disposition dated prior to alert creation."""
    engine = RiskEngine()
    alert_created_at = "2026-03-20T10:00:00Z"
    case_disposition_timestamp = "2026-03-19T10:00:00Z"  # Precedes alert!

    res = engine.evaluate_case_chronology(
        case_id="CASE-CHRONO-01",
        alert_created_at=alert_created_at,
        case_disposition_timestamp=case_disposition_timestamp
    )
    assert res is not None
    assert res.triggered is True
    assert res.rule_id == "RULE-CASE-CHRONOLOGY"
    assert res.reason_code == "CHRONOLOGY_VIOLATION_CASE_ALERT"
