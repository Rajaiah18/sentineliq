"""
SentinelIQ Deterministic Risk Scoring & Severity Banding
Calculates transparent 0-100 risk score and maps to configurable severity bands.
"""
from typing import List, Dict, Any, Tuple
from risk_engine.rules import RuleResult

# Configurable Severity Bands
SEVERITY_BANDS = {
    "CRITICAL": (90.0, 100.0),
    "HIGH": (70.0, 89.99),
    "MEDIUM": (40.0, 69.99),
    "LOW": (0.0, 39.99)
}


def calculate_risk_score(triggered_rules: List[RuleResult]) -> Tuple[float, str]:
    """
    Transparent aggregation formula:
    Score = max(weights) + 0.3 * sum(remaining_weights)
    Clamped strictly between 0.0 and 100.0.
    """
    if not triggered_rules:
        return 0.0, "LOW"

    # Filter out duplicate rule IDs
    unique_rules: Dict[str, RuleResult] = {}
    for r in triggered_rules:
        if r.rule_id not in unique_rules or r.weight > unique_rules[r.rule_id].weight:
            unique_rules[r.rule_id] = r

    weights = sorted([r.weight for r in unique_rules.values()], reverse=True)
    if not weights:
        return 0.0, "LOW"

    max_weight = weights[0]
    remainder_sum = sum(weights[1:])
    raw_score = max_weight + (0.35 * remainder_sum)
    final_score = round(min(max(raw_score, 0.0), 100.0), 2)

    # Map to severity band
    severity = "LOW"
    for band_name, (low, high) in SEVERITY_BANDS.items():
        if low <= final_score <= high:
            severity = band_name
            break

    return final_score, severity


def map_score_to_severity(score: float) -> str:
    """Return severity string for a given numeric score."""
    clamped = min(max(score, 0.0), 100.0)
    for band_name, (low, high) in SEVERITY_BANDS.items():
        if low <= clamped <= high:
            return band_name
    return "LOW"
