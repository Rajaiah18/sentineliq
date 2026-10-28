"""
SentinelIQ Explainability & Evidence Generator
Produces human-readable explanations, audit-proof evidence snapshots,
and concrete analyst recommendation steps.
"""
from typing import List, Dict, Any, Optional
from risk_engine.rules import RuleResult


RECOMMENDED_STEPS: Dict[str, List[str]] = {
    "RULE-CLOSED-ACCOUNT": [
        "Verify core banking ledger closure timestamp against transaction timestamp.",
        "Assess whether transaction originated from automated clearing house (ACH) batch or direct interface.",
        "Contact account holder to verify unreturned payment cards or active recurring debits.",
        "Freeze routing identifiers if unauthorized access is suspected."
    ],
    "RULE-OVERDRAFT-EXCEEDED": [
        "Inspect balance calculation history and sequence of settled transactions.",
        "Verify authorized overdraft agreement limits on core banking profile.",
        "Initiate provisional transaction hold or account restriction if deficit exceeds recovery thresholds.",
        "Notify customer relationship manager of unauthorized negative balance breach."
    ],
    "RULE-TRANSFER-MISMATCH": [
        "Reconcile source and destination ledger entries across transfer group ID.",
        "Audit intermediary FX conversion rates, fees, or routing gateway deductions.",
        "Review corresponding ISO 20022 / MT103 wire messages for truncated or modified values.",
        "Hold settlement pending manual confirmation between institution counterparts."
    ],
    "RULE-ALERT-NO-TXN": [
        "Review pipeline ingestion logs for truncated or dropped event payloads.",
        "Validate database referential integrity for orphaned alert triggers.",
        "Flag alert record for technical audit; do not process as valid transaction risk."
    ],
    "RULE-CASE-CHRONOLOGY": [
        "Audit investigator workstation clocks and microsecond timestamp synchronization.",
        "Check whether case was backdated or associated with a pre-existing legacy ticket.",
        "Refer case metadata to Compliance Reviewer for procedural validation."
    ],
    "RULE-HIGH-VALUE": [
        "Confirm source of funds and business rationale with customer profile.",
        "Check historical turnover and expected annual transaction volume.",
        "Review matching invoices, contracts, or bill of lading documents.",
        "File Currency Transaction Report (CTR) / Suspicious Activity Report (SAR) if unverified."
    ],
    "RULE-VELOCITY": [
        "Review device and IP geolocation across rapid transaction cluster.",
        "Determine if automated script, botnet, or credential stuffing pattern is active.",
        "Verify whether transactions represent repeated micro-charges (card testing).",
        "Temporarily restrict online banking credentials pending identity challenge."
    ],
    "RULE-NEW-DEVICE": [
        "Inspect hardware fingerprint, user-agent string, and operating system attributes.",
        "Compare IP country of device with customer resident registration and typical login areas.",
        "Trigger out-of-band Step-Up Multi-Factor Authentication (MFA).",
        "Confirm with cardholder whether new mobile handset was recently authorized."
    ],
    "RULE-DORMANT-REACTIVATION": [
        "Examine dormancy activation documentation and recent credential recovery requests.",
        "Ensure re-KYC (Know Your Customer) requirements were satisfied prior to fund release.",
        "Hold outward transfers until positive voice or biometric verification is obtained."
    ],
    "RULE-CIRCULAR-TRANSFER": [
        "Map full transaction entity graph across accounts and counterparty beneficiaries.",
        "Assess whether fund flow demonstrates round-tripping or smurfing behavior.",
        "Examine economic substance and common beneficial ownership between counterparties."
    ],
    "RULE-UNUSUAL-MERCHANT": [
        "Review merchant category code (MCC) and merchant risk rating.",
        "Evaluate transaction size relative to normal merchant category ticket averages.",
        "Inspect whether customer has declared exposure to virtual assets or gaming."
    ],
    "RULE-MULTI-SIGNAL": [
        "Initiate comprehensive enhanced due diligence (EDD) review.",
        "Escalate dossier immediately to Senior Financial Crime Compliance Manager.",
        "Assemble unified timeline of high-velocity, high-value, and anomalous device triggers.",
        "Prepare SAR/STR draft for regulatory submission."
    ]
}


def generate_explanation(
    triggered_rules: List[RuleResult],
    customer_info: Dict[str, Any],
    account_info: Dict[str, Any],
    transaction_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs comprehensive explanation, structured evidence dictionary,
    and targeted investigation steps.
    """
    if not triggered_rules:
        return {
            "title": "Low Risk Normal Activity",
            "description": "No detection rules breached.",
            "reason_codes": [],
            "explanation": "Transaction complies with standard operational thresholds.",
            "evidence": {},
            "recommended_steps": []
        }

    reason_codes = [r.reason_code for r in triggered_rules]
    primary_rule = triggered_rules[0]

    title = f"{primary_rule.rule_name} Alert"
    if len(triggered_rules) > 1:
        title += f" (+{len(triggered_rules) - 1} compounding rules)"

    explanations: List[str] = []
    evidence_dict: Dict[str, Any] = {
        "customer_id": customer_info.get("customer_id"),
        "customer_name": f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip(),
        "customer_risk_profile": customer_info.get("risk_profile"),
        "account_id": account_info.get("account_id"),
        "account_status": account_info.get("account_status"),
        "current_balance": account_info.get("current_balance"),
        "overdraft_limit": account_info.get("overdraft_limit"),
        "rule_triggers": []
    }

    if transaction_info:
        evidence_dict["transaction_id"] = transaction_info.get("transaction_id")
        evidence_dict["amount"] = transaction_info.get("amount")
        evidence_dict["currency"] = transaction_info.get("currency")
        evidence_dict["transaction_type"] = transaction_info.get("transaction_type")
        evidence_dict["channel"] = transaction_info.get("channel")
        evidence_dict["timestamp"] = transaction_info.get("transaction_timestamp")

    all_recommended_steps: List[str] = []

    for rule in triggered_rules:
        explanations.append(rule.explanation)
        evidence_dict["rule_triggers"].append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "severity": rule.severity,
            "weight": rule.weight,
            "evidence_details": rule.evidence
        })
        steps = RECOMMENDED_STEPS.get(rule.rule_id, ["Conduct standard enhanced due diligence."])
        for s in steps:
            if s not in all_recommended_steps:
                all_recommended_steps.append(s)

    full_explanation = " | ".join(explanations)
    description = f"Generated by {primary_rule.rule_id} ({primary_rule.rule_name}). {primary_rule.explanation}"

    evidence_dict["recommended_investigation_steps"] = all_recommended_steps

    return {
        "title": title,
        "description": description,
        "reason_codes": reason_codes,
        "explanation": full_explanation,
        "evidence": evidence_dict,
        "recommended_steps": all_recommended_steps
    }
