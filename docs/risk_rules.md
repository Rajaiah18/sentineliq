# SentinelIQ — Risk Detection Rules & Scoring Reference
**Intelligent Transaction Risk & Investigation Platform**  
*Tagline: Explainable Risk. Traceable Decisions.*

---

## 1. Overview of Risk Rules

SentinelIQ incorporates 12 deterministic, configurable detection rules categorized into Integrity, Value, Velocity, Behavioral, and Compliance dimensions.

### 1.1 Five Mandatory Negative Scenarios

| Rule ID | Rule Name | Category | Severity | Weight | Threshold | Description |
|---|---|---|---|---|---|---|
| `RULE-CLOSED-ACCOUNT` | Closed Account Transaction | INTEGRITY | CRITICAL | 95.0 | 0.0 | Intercepts transactions attempted against closed accounts. |
| `RULE-OVERDRAFT-EXCEEDED` | Overdraft Limit Breach | INTEGRITY | HIGH | 85.0 | 0.0 | Flags transactions causing negative balance beyond authorized limit. |
| `RULE-TRANSFER-MISMATCH` | Transfer Leg Mismatch | INTEGRITY | HIGH | 90.0 | 0.0 | Flags discrepancies between debit and credit transfer legs. |
| `RULE-ALERT-NO-TXN` | Alert Lacks Triggering Txn | INTEGRITY | CRITICAL | 100.0 | 1.0 | Catches orphaned alerts without triggering transaction references. |
| `RULE-CASE-CHRONOLOGY` | Case Chronology Anomaly | INTEGRITY | CRITICAL | 100.0 | 0.0 | Flags dispositions with timestamps prior to alert creation. |

---

### 1.2 Additional Suspicious Activity Detection Rules

| Rule ID | Rule Name | Category | Severity | Weight | Threshold | Description |
|---|---|---|---|---|---|---|
| `RULE-HIGH-VALUE` | High Value Transaction | VALUE | HIGH | 70.0 | $10,000.00 | Flags single transactions exceeding reporting limits. |
| `RULE-VELOCITY` | Transaction Velocity Spike | VELOCITY | MEDIUM | 65.0 | 5.0 | Detects > 5 transactions within a 1-hour window. |
| `RULE-NEW-DEVICE` | Untrusted Device Anomaly | BEHAVIORAL | MEDIUM | 60.0 | 0.0 | Flags transactions from untrusted/flagged hardware devices. |
| `RULE-DORMANT-REACTIVATION` | Dormant Reactivation | BEHAVIORAL | MEDIUM | 60.0 | 90 days | Flags sudden >$1,000 activity after 90+ days dormancy. |
| `RULE-CIRCULAR-TRANSFER` | Circular Transfer Pattern | BEHAVIORAL | HIGH | 85.0 | 3 legs | Detects circular fund cycling across counterparty accounts. |
| `RULE-UNUSUAL-MERCHANT` | High Risk Merchant | COMPLIANCE | MEDIUM | 55.0 | $2,500.00 | Flags large purchases at GAMBLING or CRYPTO merchants. |
| `RULE-MULTI-SIGNAL` | Compound Multi-Signal | BEHAVIORAL | CRITICAL | 90.0 | 3 signals | Aggregates concurrent convergence of 3+ distinct rules. |

---

## 2. Transparent Risk Scoring Formula

The risk score is calculated deterministically on a 0.0 to 100.0 scale:

$$\text{Score} = \min\left(100.0, \, \max(W) + 0.35 \times \sum_{i > 1} W_i\right)$$

Where $W$ represents the descending-sorted list of unique weights from all triggered rules.

### Configurable Severity Bands
- **CRITICAL:** 90.00 – 100.00
- **HIGH:** 70.00 – 89.99
- **MEDIUM:** 40.00 – 69.99
- **LOW:** 0.00 – 39.99

---

## 3. Explainability & Evidence Schema

For every generated alert, SentinelIQ produces:
1. Narrative explanation linking specific rule clauses to observed data.
2. Machine-readable evidence containing exact values (e.g. `balance_after`, `excess_deficit`, `threshold`).
3. Standardized reason codes (e.g. `ERR_CLOSED_ACCOUNT_POSTING`, `BREACH_OVERDRAFT_LIMIT`).
4. Step-by-step procedural recommendations for human investigators.
