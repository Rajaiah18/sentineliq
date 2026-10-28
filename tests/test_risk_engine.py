"""
SentinelIQ Unit Tests: Risk Rules, Scoring, and Explainability
"""
import pytest
from risk_engine.engine import RiskEngine
from risk_engine.rules import RuleResult, get_default_risk_rules
from risk_engine.scoring import calculate_risk_score, map_score_to_severity
from risk_engine.explainability import generate_explanation


def test_scoring_empty_rules():
    score, sev = calculate_risk_score([])
    assert score == 0.0
    assert sev == "LOW"


def test_scoring_single_rule():
    r = RuleResult(
        rule_id="RULE-HIGH-VALUE",
        rule_name="High Value",
        rule_category="VALUE",
        severity="HIGH",
        weight=70.0,
        triggered=True,
        reason_code="THRESHOLD_EXCEEDED",
        explanation="Test explanation"
    )
    score, sev = calculate_risk_score([r])
    assert score == 70.0
    assert sev == "HIGH"


def test_scoring_compounding_rules():
    r1 = RuleResult("R1", "Rule 1", "VAL", "HIGH", 70.0, True, "CODE1", "Exp 1")
    r2 = RuleResult("R2", "Rule 2", "VEL", "HIGH", 60.0, True, "CODE2", "Exp 2")
    score, sev = calculate_risk_score([r1, r2])
    # 70 + (0.35 * 60) = 70 + 21 = 91.0 -> CRITICAL
    assert score == 91.0
    assert sev == "CRITICAL"


def test_scoring_clamping_at_100():
    r1 = RuleResult("R1", "Rule 1", "VAL", "CRITICAL", 95.0, True, "CODE1", "Exp 1")
    r2 = RuleResult("R2", "Rule 2", "VAL", "CRITICAL", 90.0, True, "CODE2", "Exp 2")
    r3 = RuleResult("R3", "Rule 3", "VAL", "CRITICAL", 80.0, True, "CODE3", "Exp 3")
    score, sev = calculate_risk_score([r1, r2, r3])
    assert score <= 100.0
    assert sev == "CRITICAL"


def test_high_value_rule_evaluation():
    engine = RiskEngine()
    txn = {
        "transaction_id": "TXN-TEST-HV",
        "amount": 25000.0,  # Exceeds 10,000 threshold
        "currency": "USD",
        "transaction_timestamp": "2026-03-01T10:00:00Z"
    }
    acc = {"account_id": "ACC-01", "account_status": "OPEN", "current_balance": 50000.0, "overdraft_limit": 0.0}
    cust = {"customer_id": "CUS-01", "risk_profile": "LOW"}

    results = engine.evaluate_transaction(txn, acc, cust)
    assert any(r.rule_id == "RULE-HIGH-VALUE" for r in results)


def test_explainability_generation():
    r = RuleResult(
        rule_id="RULE-HIGH-VALUE",
        rule_name="High Value Transaction",
        rule_category="VALUE",
        severity="HIGH",
        weight=70.0,
        triggered=True,
        reason_code="THRESHOLD_HIGH_VALUE_EXCEEDED",
        explanation="Transaction of $25,000 exceeded threshold."
    )
    explanation = generate_explanation([r], {"customer_id": "CUS-01", "first_name": "John", "last_name": "Doe"}, {"account_id": "ACC-01"})
    assert "High Value" in explanation["title"]
    assert "THRESHOLD_HIGH_VALUE_EXCEEDED" in explanation["reason_codes"]
    assert len(explanation["recommended_steps"]) > 0
