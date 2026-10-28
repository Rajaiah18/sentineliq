"""
SentinelIQ Risk Rules Definition and Execution
All 12 rules with deterministic evaluation, configurable thresholds, explainable evidence, and reason codes.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.app.models.entities import RiskRule


@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    rule_category: str
    severity: str
    weight: float
    triggered: bool
    reason_code: str
    explanation: str
    evidence: Dict[str, Any] = field(default_factory=dict)


# Default Rule Configurations
DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "RULE-CLOSED-ACCOUNT",
        "rule_name": "Closed Account Transaction",
        "description": "Detects transactions executed against an account that was closed prior to or at the transaction timestamp.",
        "rule_category": "INTEGRITY",
        "enabled": True,
        "severity": "CRITICAL",
        "weight": 95.0,
        "threshold": 0.0,
        "configuration": {"enforce_status": True, "check_effective_timestamp": True},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-OVERDRAFT-EXCEEDED",
        "rule_name": "Negative Balance Overdraft Breach",
        "description": "Detects transactions causing account balance to plunge below permitted overdraft limit.",
        "rule_category": "INTEGRITY",
        "enabled": True,
        "severity": "HIGH",
        "weight": 85.0,
        "threshold": 0.0,
        "configuration": {"tolerance": 0.0},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-TRANSFER-MISMATCH",
        "rule_name": "Transfer Reconciliation Mismatch",
        "description": "Detects transfer groups where outgoing and incoming legs disagree on amount, currency, or relationship.",
        "rule_category": "INTEGRITY",
        "enabled": True,
        "severity": "HIGH",
        "weight": 90.0,
        "threshold": 0.0,
        "configuration": {"amount_tolerance": 0.01},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-ALERT-NO-TXN",
        "rule_name": "Alert Lacks Triggering Transaction",
        "description": "Flags alerts generated without valid triggering transaction references as data integrity violations.",
        "rule_category": "INTEGRITY",
        "enabled": True,
        "severity": "CRITICAL",
        "weight": 100.0,
        "threshold": 1.0,
        "configuration": {"min_transactions": 1},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-CASE-CHRONOLOGY",
        "rule_name": "Case Disposition Precedes Alert",
        "description": "Detects investigation case dispositions or actions recorded with timestamps prior to alert creation.",
        "rule_category": "INTEGRITY",
        "enabled": True,
        "severity": "CRITICAL",
        "weight": 100.0,
        "threshold": 0.0,
        "configuration": {"enforce_strict_order": True},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-HIGH-VALUE",
        "rule_name": "High Value Transaction",
        "description": "Identifies transactions exceeding statutory or risk-based single transaction thresholds.",
        "rule_category": "VALUE",
        "enabled": True,
        "severity": "HIGH",
        "weight": 70.0,
        "threshold": 10000.0,
        "configuration": {"threshold_amount": 10000.0},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-VELOCITY",
        "rule_name": "Unusual Transaction Velocity",
        "description": "Flags accounts exhibiting sudden frequency spikes (>5 transactions in 1 hour).",
        "rule_category": "VELOCITY",
        "enabled": True,
        "severity": "MEDIUM",
        "weight": 65.0,
        "threshold": 5.0,
        "configuration": {"window_seconds": 3600, "max_allowed": 5},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-NEW-DEVICE",
        "rule_name": "High Risk Unrecognized Device",
        "description": "Detects transactions executed on untrusted or newly registered devices for elevated risk profiles.",
        "rule_category": "BEHAVIORAL",
        "enabled": True,
        "severity": "MEDIUM",
        "weight": 60.0,
        "threshold": 0.0,
        "configuration": {"flag_untrusted": True, "check_country_mismatch": True},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-DORMANT-REACTIVATION",
        "rule_name": "Dormant Account Reactivation",
        "description": "Identifies sudden significant transactions on accounts inactive for >90 days.",
        "rule_category": "BEHAVIORAL",
        "enabled": True,
        "severity": "MEDIUM",
        "weight": 60.0,
        "threshold": 90.0,
        "configuration": {"dormant_days": 90, "min_amount": 1000.0},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-CIRCULAR-TRANSFER",
        "rule_name": "Circular Transfer Pattern",
        "description": "Detects cyclical fund movements (A -> B -> C -> A) indicative of layering or wash trading.",
        "rule_category": "BEHAVIORAL",
        "enabled": True,
        "severity": "HIGH",
        "weight": 85.0,
        "threshold": 3.0,
        "configuration": {"max_cycle_length": 4, "time_window_hours": 48},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-UNUSUAL-MERCHANT",
        "rule_name": "High Risk Merchant Category",
        "description": "Flags elevated transactions at high-risk merchant categories (GAMBLING, CRYPTO) or cross-border mismatches.",
        "rule_category": "COMPLIANCE",
        "enabled": True,
        "severity": "MEDIUM",
        "weight": 55.0,
        "threshold": 2500.0,
        "configuration": {"high_risk_categories": ["GAMBLING", "CRYPTO"], "amount_threshold": 2500.0},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    },
    {
        "rule_id": "RULE-MULTI-SIGNAL",
        "rule_name": "Compound Risk Multi-Signal",
        "description": "Aggregates when a customer or account triggers 3 or more concurrent risk indicators.",
        "rule_category": "BEHAVIORAL",
        "enabled": True,
        "severity": "CRITICAL",
        "weight": 90.0,
        "threshold": 3.0,
        "configuration": {"min_distinct_signals": 3},
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    }
]


def get_default_risk_rules() -> List[RiskRule]:
    """Return standard list of RiskRule Pydantic models."""
    return [RiskRule(**r) for r in DEFAULT_RULES]
