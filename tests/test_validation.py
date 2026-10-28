"""
SentinelIQ Tests: Validation Suite (24 Checks)
"""
import pytest
from validation.checks import DataValidator
from risk_engine.rules import DEFAULT_RULES


def test_validator_detects_all_five_scenarios():
    validator = DataValidator()

    customers = [{"customer_id": "CUS-01"}]
    accounts = [
        {"account_id": "ACC-01", "customer_id": "CUS-01", "account_status": "CLOSED", "closed_at": "2026-02-01T00:00:00Z", "opened_at": "2026-01-01T00:00:00Z", "overdraft_limit": 500.0},
        {"account_id": "ACC-02", "customer_id": "CUS-01", "account_status": "OPEN", "opened_at": "2026-01-01T00:00:00Z", "overdraft_limit": 0.0}
    ]
    transactions = [
        # Scenario 1: Closed account txn
        {"transaction_id": "TXN-01", "source_account_id": "ACC-01", "customer_id": "CUS-01", "amount": 100.0, "currency": "USD", "transaction_timestamp": "2026-03-01T00:00:00Z", "balance_after": 0.0},
        # Scenario 2: Overdraft breach
        {"transaction_id": "TXN-02", "source_account_id": "ACC-02", "customer_id": "CUS-01", "amount": 2000.0, "currency": "USD", "transaction_timestamp": "2026-03-01T00:00:00Z", "balance_after": -1500.0},
        # Scenario 3 legs:
        {"transaction_id": "TXN-SRC", "source_account_id": "ACC-02", "destination_account_id": "ACC-01", "customer_id": "CUS-01", "amount": 5000.0, "currency": "USD", "transaction_timestamp": "2026-03-01T00:00:00Z"},
        {"transaction_id": "TXN-DST", "source_account_id": "ACC-01", "destination_account_id": "ACC-02", "customer_id": "CUS-01", "amount": 4000.0, "currency": "USD", "transaction_timestamp": "2026-03-01T00:00:00Z"}
    ]
    transfer_links = [
        {"transfer_link_id": "TRL-01", "transfer_group_id": "GRP-01", "source_transaction_id": "TXN-SRC", "destination_transaction_id": "TXN-DST", "source_account_id": "ACC-02", "destination_account_id": "ACC-01"}
    ]
    alerts = [
        # Scenario 4: Alert without transaction
        {"alert_id": "ALT-EMPTY", "triggered_transaction_ids": [], "customer_id": "CUS-01", "triggered_rule_ids": ["RULE-ALERT-NO-TXN"], "created_at": "2026-03-10T00:00:00Z"}
    ]
    cases = [
        # Scenario 5: Case disposition precedes alert
        {"case_id": "CASE-01", "alert_ids": ["ALT-EMPTY"], "customer_id": "CUS-01", "case_status": "CLOSED", "disposition": "FALSE_POSITIVE", "closed_at": "2026-03-01T00:00:00Z"}
    ]

    report = validator.run_all_checks(
        customers=customers,
        accounts=accounts,
        merchants=[],
        devices=[],
        transactions=transactions,
        transfer_links=transfer_links,
        alerts=alerts,
        cases=cases,
        analyst_actions=[],
        rules=DEFAULT_RULES
    )

    scens = report["scenario_validation"]
    assert scens["scenario_1_closed_account_detected"] is True
    assert scens["scenario_2_overdraft_breach_detected"] is True
    assert scens["scenario_3_transfer_mismatch_detected"] is True
    assert scens["scenario_4_alert_no_txn_detected"] is True
    assert scens["scenario_5_case_chronology_detected"] is True
