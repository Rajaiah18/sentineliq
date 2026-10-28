"""
SentinelIQ Deterministic Evaluation Pipeline
Strictly joins detection outputs to separately stored ground truth AFTER inference.
Computes Confusion Matrix, Precision, Recall, F1, Specificity, Accuracy,
Per-Rule detection metrics, and Per-Scenario breakdowns.
"""
from typing import Dict, Any, List, Optional
import json
import csv
import os
from datetime import datetime


class RiskEvaluator:
    def evaluate(
        self,
        alerts: List[Dict[str, Any]],
        ground_truth_records: List[Dict[str, Any]],
        total_transactions_count: int
    ) -> Dict[str, Any]:
        """
        Evaluate alert detections against isolated ground truth.
        """
        # Map of transaction_id -> Alert
        flagged_txns: Dict[str, Dict[str, Any]] = {}
        for a in alerts:
            for tid in a.get("triggered_transaction_ids", []):
                flagged_txns[tid] = a

        # Ground truth mapping: entity_id (transaction_id) -> GroundTruth record
        gt_txns = {gt["entity_id"]: gt for gt in ground_truth_records if gt.get("entity_type") == "TRANSACTION"}

        # Metrics counters
        tp = 0  # Flagged by system & truly suspicious
        fp = 0  # Flagged by system & NOT suspicious in ground truth
        fn = 0  # NOT flagged by system & truly suspicious in ground truth
        tn = 0  # NOT flagged by system & NOT suspicious

        per_scenario_metrics: Dict[str, Dict[str, int]] = {}
        per_rule_metrics: Dict[str, Dict[str, int]] = {}
        severity_counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for a in alerts:
            sev = a.get("severity", "LOW")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            for r_id in a.get("triggered_rule_ids", []):
                if r_id not in per_rule_metrics:
                    per_rule_metrics[r_id] = {"alerts_triggered": 0, "true_positives": 0, "false_positives": 0}
                per_rule_metrics[r_id]["alerts_triggered"] += 1

        # Evaluate against ground truth records
        for entity_id, gt in gt_txns.items():
            scen_id = gt.get("scenario_id", "UNKNOWN")
            is_suspicious = gt.get("is_suspicious", False)

            if scen_id not in per_scenario_metrics:
                per_scenario_metrics[scen_id] = {"total": 0, "detected": 0, "missed": 0}
            per_scenario_metrics[scen_id]["total"] += 1

            is_flagged = entity_id in flagged_txns

            if is_suspicious:
                if is_flagged:
                    tp += 1
                    per_scenario_metrics[scen_id]["detected"] += 1
                    alert_obj = flagged_txns[entity_id]
                    for r_id in alert_obj.get("triggered_rule_ids", []):
                        if r_id in per_rule_metrics:
                            per_rule_metrics[r_id]["true_positives"] += 1
                else:
                    fn += 1
                    per_scenario_metrics[scen_id]["missed"] += 1
            else:
                if is_flagged:
                    fp += 1
                    alert_obj = flagged_txns[entity_id]
                    for r_id in alert_obj.get("triggered_rule_ids", []):
                        if r_id in per_rule_metrics:
                            per_rule_metrics[r_id]["false_positives"] += 1
                else:
                    tn += 1

        # Account for normal transactions not explicitly enumerated in synthetic ground-truth anomalies
        # True Negatives include all unflagged normal transactions
        total_evaluated_gt = len(gt_txns)
        unlabeled_transactions = max(0, total_transactions_count - total_evaluated_gt)
        # Any transaction outside GT that was not flagged is a true negative
        # Any transaction outside GT that was flagged is treated as FP
        flagged_outside_gt = len([t for t in flagged_txns if t not in gt_txns])
        fp += flagged_outside_gt
        tn += max(0, unlabeled_transactions - flagged_outside_gt)

        # Calculate standard ratios with zero-division protection
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0
        specificity = round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0.0
        accuracy = round((tp + tn) / (tp + tn + fp + fn), 4) if (tp + tn + fp + fn) > 0 else 0.0

        summary = {
            "evaluation_timestamp": datetime.utcnow().isoformat() + "Z",
            "confusion_matrix": {
                "true_positives": tp,
                "false_positives": fp,
                "true_negatives": tn,
                "false_negatives": fn
            },
            "metrics": {
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "specificity": specificity,
                "accuracy": accuracy
            },
            "alerts_by_severity": severity_counts,
            "total_alerts_evaluated": len(alerts),
            "total_transactions_scope": total_transactions_count,
            "per_rule_metrics": per_rule_metrics,
            "per_scenario_metrics": per_scenario_metrics,
            "metric_definitions": {
                "precision": "TP / (TP + FP) — Fraction of generated alerts that correspond to genuine risk scenarios.",
                "recall": "TP / (TP + FN) — Fraction of genuine risk scenarios successfully flagged by rules.",
                "f1_score": "2 * (Precision * Recall) / (Precision + Recall) — Harmonic mean of precision and recall.",
                "specificity": "TN / (TN + FP) — Proportion of legitimate transactions accurately unflagged.",
                "accuracy": "(TP + TN) / Total — Overall classification accuracy across all transactions."
            }
        }
        return summary
