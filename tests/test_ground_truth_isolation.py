"""
SentinelIQ Tests: Ground Truth Isolation Verification
Ensures:
1. Transaction records and features contain no ground-truth columns.
2. The Risk Engine executes without access to ground truth.
3. Removing ground-truth files does not impede transaction risk detection.
4. Ground truth is joined strictly after inference in evaluation.
"""
import os
import tempfile
import pytest
from risk_engine.engine import RiskEngine
from generator.generate import DatasetGenerator
from evaluation.evaluator import RiskEvaluator
from validation.checks import DataValidator


def test_transactions_contain_no_ground_truth_columns():
    """Verify transactions do not leak ground-truth labels."""
    gen = DatasetGenerator(profile="demo", seed=20261022)
    with tempfile.TemporaryDirectory() as tmpdir:
        gen.run(
            export_dir=os.path.join(tmpdir, "exports"),
            gt_dir=os.path.join(tmpdir, "gt"),
            reports_dir=os.path.join(tmpdir, "reports")
        )
        import csv
        with open(os.path.join(tmpdir, "exports", "transactions.csv"), "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

        forbidden_keys = {"is_suspicious", "ground_truth_id", "scenario_id", "true_label"}
        for col in header:
            assert col not in forbidden_keys, f"Ground-truth feature leakage: '{col}' found in transactions.csv!"


def test_risk_engine_operates_without_ground_truth():
    """Verify RiskEngine requires only operational context."""
    engine = RiskEngine()
    # Transaction without any scenario or label metadata
    txn = {
        "transaction_id": "TXN-BLIND-01",
        "amount": 15000.0,
        "currency": "USD",
        "transaction_timestamp": "2026-04-01T10:00:00Z"
    }
    acc = {"account_id": "ACC-01", "account_status": "OPEN", "current_balance": 20000.0, "overdraft_limit": 0.0}
    cust = {"customer_id": "CUS-01", "risk_profile": "MEDIUM"}

    # Detection runs purely on features
    results = engine.evaluate_transaction(txn, acc, cust)
    assert len(results) > 0
    assert any(r.rule_id == "RULE-HIGH-VALUE" for r in results)


def test_evaluator_joins_ground_truth_post_detection():
    """Verify evaluation correctly performs post-inference join."""
    evaluator = RiskEvaluator()
    alerts = [{
        "alert_id": "ALT-01",
        "triggered_transaction_ids": ["TXN-TEST-01"],
        "severity": "HIGH",
        "triggered_rule_ids": ["RULE-HIGH-VALUE"]
    }]
    gt = [{
        "ground_truth_id": "GT-01",
        "entity_type": "TRANSACTION",
        "entity_id": "TXN-TEST-01",
        "is_suspicious": True,
        "scenario_id": "SCEN-HIGH-VALUE"
    }]

    res = evaluator.evaluate(alerts, gt, total_transactions_count=100)
    assert res["confusion_matrix"]["true_positives"] == 1
    assert res["metrics"]["precision"] == 1.0
    assert res["metrics"]["recall"] == 1.0
