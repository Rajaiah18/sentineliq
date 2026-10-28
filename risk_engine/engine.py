"""
SentinelIQ Core Risk Detection Engine
Evaluates transactions, accounts, transfers, devices, and integrity constraints.
Produces explainable, deterministic Alert records.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from risk_engine.rules import RuleResult, DEFAULT_RULES
from risk_engine.scoring import calculate_risk_score
from risk_engine.explainability import generate_explanation
from backend.app.models.entities import Alert, Transaction, Account, Customer, TransferLink, RiskRule


class RiskEngine:
    def __init__(self, rules: Optional[List[RiskRule]] = None):
        if rules:
            self.rules_config = {r.rule_id: r for r in rules}
        else:
            self.rules_config = {r["rule_id"]: RiskRule(**r) for r in DEFAULT_RULES}

    def evaluate_transaction(
        self,
        transaction: Dict[str, Any],
        account: Dict[str, Any],
        customer: Dict[str, Any],
        merchant: Optional[Dict[str, Any]] = None,
        device: Optional[Dict[str, Any]] = None,
        recent_account_txns: Optional[List[Dict[str, Any]]] = None,
        account_last_active_date: Optional[str] = None
    ) -> List[RuleResult]:
        """
        Evaluate a single transaction in context and return list of triggered RuleResult objects.
        """
        results: List[RuleResult] = []

        txn_id = transaction.get("transaction_id", "")
        amount = float(transaction.get("amount", 0.0))
        txn_time_str = transaction.get("transaction_timestamp", "")

        # -------------------------------------------------------------
        # Rule 1: Closed Account Transaction (RULE-CLOSED-ACCOUNT)
        # -------------------------------------------------------------
        rule_closed = self.rules_config.get("RULE-CLOSED-ACCOUNT")
        if rule_closed and rule_closed.enabled:
            acc_status = account.get("account_status", "OPEN")
            closed_at = account.get("closed_at")

            is_closed_violation = False
            closure_evidence: Dict[str, Any] = {}

            if acc_status == "CLOSED":
                is_closed_violation = True
                closure_evidence = {
                    "account_status": acc_status,
                    "closed_at": closed_at,
                    "transaction_timestamp": txn_time_str,
                    "violation": "Transaction submitted against closed account status."
                }
            elif closed_at and txn_time_str >= closed_at:
                is_closed_violation = True
                closure_evidence = {
                    "account_status": acc_status,
                    "closed_at": closed_at,
                    "transaction_timestamp": txn_time_str,
                    "violation": "Transaction timestamp is greater than or equal to account closure timestamp."
                }

            if is_closed_violation:
                results.append(RuleResult(
                    rule_id=rule_closed.rule_id,
                    rule_name=rule_closed.rule_name,
                    rule_category=rule_closed.rule_category,
                    severity=rule_closed.severity,
                    weight=rule_closed.weight,
                    triggered=True,
                    reason_code="ERR_CLOSED_ACCOUNT_POSTING",
                    explanation=f"Transaction {txn_id} posted to account {account.get('account_id')} which was closed on {closed_at or 'historical date'}.",
                    evidence=closure_evidence
                ))

        # -------------------------------------------------------------
        # Rule 2: Negative Balance Beyond Overdraft (RULE-OVERDRAFT-EXCEEDED)
        # -------------------------------------------------------------
        rule_overdraft = self.rules_config.get("RULE-OVERDRAFT-EXCEEDED")
        if rule_overdraft and rule_overdraft.enabled:
            balance_after = transaction.get("balance_after")
            overdraft_limit = float(account.get("overdraft_limit", 0.0))

            if balance_after is not None:
                eff_balance = float(balance_after)
                # Overdraft breach condition: balance is negative beyond the overdraft limit
                if eff_balance < (-overdraft_limit):
                    excess_deficit = round(abs(eff_balance) - overdraft_limit, 2)
                    results.append(RuleResult(
                        rule_id=rule_overdraft.rule_id,
                        rule_name=rule_overdraft.rule_name,
                        rule_category=rule_overdraft.rule_category,
                        severity=rule_overdraft.severity,
                        weight=rule_overdraft.weight,
                        triggered=True,
                        reason_code="BREACH_OVERDRAFT_LIMIT",
                        explanation=f"Transaction {txn_id} caused account {account.get('account_id')} balance (${eff_balance:.2f}) to exceed approved overdraft limit (${overdraft_limit:.2f}) by ${excess_deficit:.2f}.",
                        evidence={
                            "balance_after": eff_balance,
                            "overdraft_limit": overdraft_limit,
                            "excess_deficit": excess_deficit
                        }
                    ))

        # -------------------------------------------------------------
        # Rule 6: High Value Transaction (RULE-HIGH-VALUE)
        # -------------------------------------------------------------
        rule_high_val = self.rules_config.get("RULE-HIGH-VALUE")
        if rule_high_val and rule_high_val.enabled:
            threshold = float(rule_high_val.threshold)
            if amount >= threshold:
                results.append(RuleResult(
                    rule_id=rule_high_val.rule_id,
                    rule_name=rule_high_val.rule_name,
                    rule_category=rule_high_val.rule_category,
                    severity=rule_high_val.severity,
                    weight=rule_high_val.weight,
                    triggered=True,
                    reason_code="THRESHOLD_HIGH_VALUE_EXCEEDED",
                    explanation=f"Transaction amount of ${amount:,.2f} exceeded statutory threshold limit of ${threshold:,.2f}.",
                    evidence={"amount": amount, "threshold": threshold, "currency": transaction.get("currency", "USD")}
                ))

        # -------------------------------------------------------------
        # Rule 7: Unusual Transaction Velocity (RULE-VELOCITY)
        # -------------------------------------------------------------
        rule_velocity = self.rules_config.get("RULE-VELOCITY")
        if rule_velocity and rule_velocity.enabled and recent_account_txns:
            try:
                curr_dt = datetime.fromisoformat(txn_time_str.replace("Z", "+00:00"))
                window_sec = rule_velocity.configuration.get("window_seconds", 3600)
                max_allowed = int(rule_velocity.threshold)

                count_in_window = 1
                for past_txn in recent_account_txns:
                    past_time = past_txn.get("transaction_timestamp", "")
                    if past_time and past_txn.get("transaction_id") != txn_id:
                        p_dt = datetime.fromisoformat(past_time.replace("Z", "+00:00"))
                        diff_sec = abs((curr_dt - p_dt).total_seconds())
                        if diff_sec <= window_sec:
                            count_in_window += 1

                if count_in_window > max_allowed:
                    results.append(RuleResult(
                        rule_id=rule_velocity.rule_id,
                        rule_name=rule_velocity.rule_name,
                        rule_category=rule_velocity.rule_category,
                        severity=rule_velocity.severity,
                        weight=rule_velocity.weight,
                        triggered=True,
                        reason_code="ANOMALY_HIGH_VELOCITY",
                        explanation=f"High velocity cluster: detected {count_in_window} transactions within {window_sec // 60} minutes window (max threshold: {max_allowed}).",
                        evidence={"transactions_in_window": count_in_window, "threshold": max_allowed, "window_seconds": window_sec}
                    ))
            except Exception:
                pass

        # -------------------------------------------------------------
        # Rule 8: Unrecognized / Untrusted Device (RULE-NEW-DEVICE)
        # -------------------------------------------------------------
        rule_device = self.rules_config.get("RULE-NEW-DEVICE")
        if rule_device and rule_device.enabled and device:
            dev_status = device.get("device_status", "TRUSTED")
            dev_country = device.get("ip_country")
            cust_country = customer.get("country_code")

            if dev_status in ("UNTRUSTED", "FLAGGED") or (cust_country and dev_country and cust_country != dev_country and amount > 1500.0):
                results.append(RuleResult(
                    rule_id=rule_device.rule_id,
                    rule_name=rule_device.rule_name,
                    rule_category=rule_device.rule_category,
                    severity=rule_device.severity,
                    weight=rule_device.weight,
                    triggered=True,
                    reason_code="ALERT_DEVICE_ANOMALY",
                    explanation=f"Transaction accessed from device {device.get('device_id')} marked {dev_status} with IP location {dev_country} (Customer registered: {cust_country}).",
                    evidence={
                        "device_id": device.get("device_id"),
                        "device_status": dev_status,
                        "ip_country": dev_country,
                        "customer_country": cust_country
                    }
                ))

        # -------------------------------------------------------------
        # Rule 9: Dormant Account Reactivation (RULE-DORMANT-REACTIVATION)
        # -------------------------------------------------------------
        rule_dormant = self.rules_config.get("RULE-DORMANT-REACTIVATION")
        if rule_dormant and rule_dormant.enabled and account_last_active_date:
            try:
                curr_dt = datetime.fromisoformat(txn_time_str.replace("Z", "+00:00"))
                last_dt = datetime.fromisoformat(account_last_active_date.replace("Z", "+00:00"))
                dormant_days = (curr_dt - last_dt).days
                threshold_days = float(rule_dormant.threshold)
                min_amt = float(rule_dormant.configuration.get("min_amount", 1000.0))

                if dormant_days >= threshold_days and amount >= min_amt:
                    results.append(RuleResult(
                        rule_id=rule_dormant.rule_id,
                        rule_name=rule_dormant.rule_name,
                        rule_category=rule_dormant.rule_category,
                        severity=rule_dormant.severity,
                        weight=rule_dormant.weight,
                        triggered=True,
                        reason_code="DORMANT_REACTIVATION",
                        explanation=f"Dormant account reactivation: sudden transaction of ${amount:,.2f} after {dormant_days} days of inactivity (threshold: {threshold_days:.0f} days).",
                        evidence={"dormant_days": dormant_days, "threshold_days": threshold_days, "amount": amount}
                    ))
            except Exception:
                pass

        # -------------------------------------------------------------
        # Rule 11: High Risk Merchant Category (RULE-UNUSUAL-MERCHANT)
        # -------------------------------------------------------------
        rule_merchant = self.rules_config.get("RULE-UNUSUAL-MERCHANT")
        if rule_merchant and rule_merchant.enabled and merchant:
            category = merchant.get("merchant_category", "")
            m_risk = merchant.get("merchant_risk_level", "LOW")
            threshold = float(rule_merchant.threshold)

            high_risk_cats = rule_merchant.configuration.get("high_risk_categories", ["GAMBLING", "CRYPTO"])
            if (category in high_risk_cats or m_risk == "HIGH") and amount >= threshold:
                results.append(RuleResult(
                    rule_id=rule_merchant.rule_id,
                    rule_name=rule_merchant.rule_name,
                    rule_category=rule_merchant.rule_category,
                    severity=rule_merchant.severity,
                    weight=rule_merchant.weight,
                    triggered=True,
                    reason_code="HIGH_RISK_MERCHANT_EXPOSURE",
                    explanation=f"High-risk merchant transaction of ${amount:,.2f} at {merchant.get('merchant_name')} ({category}, Risk: {m_risk}).",
                    evidence={
                        "merchant_id": merchant.get("merchant_id"),
                        "merchant_name": merchant.get("merchant_name"),
                        "category": category,
                        "risk_level": m_risk,
                        "amount": amount
                    }
                ))

        # -------------------------------------------------------------
        # Rule 12: Compound Multi-Signal (RULE-MULTI-SIGNAL)
        # -------------------------------------------------------------
        rule_multi = self.rules_config.get("RULE-MULTI-SIGNAL")
        if rule_multi and rule_multi.enabled:
            # If 3 or more distinct rules already triggered, compound multi-signal triggers
            if len(results) >= int(rule_multi.threshold):
                results.append(RuleResult(
                    rule_id=rule_multi.rule_id,
                    rule_name=rule_multi.rule_name,
                    rule_category=rule_multi.rule_category,
                    severity=rule_multi.severity,
                    weight=rule_multi.weight,
                    triggered=True,
                    reason_code="COMPOUND_MULTI_SIGNAL_BURST",
                    explanation=f"Multiple risk factors converged: {len(results)} distinct violation rules triggered simultaneously on this single transaction event.",
                    evidence={"contributing_rule_ids": [r.rule_id for r in results]}
                ))

        return results

    def evaluate_transfer_reconciliation(
        self,
        source_txn: Dict[str, Any],
        dest_txn: Optional[Dict[str, Any]],
        transfer_link: Dict[str, Any]
    ) -> Optional[RuleResult]:
        """
        Rule 3: Transfer Legs Do Not Reconcile (RULE-TRANSFER-MISMATCH)
        Validates amount, currency, source/dest accounts, counterpart existence.
        """
        rule = self.rules_config.get("RULE-TRANSFER-MISMATCH")
        if not rule or not rule.enabled:
            return None

        mismatches = []
        evidence = {"transfer_link_id": transfer_link.get("transfer_link_id")}

        if not dest_txn:
            mismatches.append("Counterpart destination transaction record missing.")
        else:
            s_amt = float(source_txn.get("amount", 0.0))
            d_amt = float(dest_txn.get("amount", 0.0))
            if abs(s_amt - d_amt) > 0.01:
                mismatches.append(f"Amount mismatch: source leg ${s_amt:.2f} != destination leg ${d_amt:.2f}")
                evidence["source_amount"] = s_amt
                evidence["destination_amount"] = d_amt

            s_curr = source_txn.get("currency")
            d_curr = dest_txn.get("currency")
            if s_curr != d_curr:
                mismatches.append(f"Currency mismatch: source currency {s_curr} != destination currency {d_curr}")
                evidence["source_currency"] = s_curr
                evidence["destination_currency"] = d_curr

            if source_txn.get("destination_account_id") != dest_txn.get("source_account_id") or source_txn.get("source_account_id") != dest_txn.get("destination_account_id"):
                mismatches.append("Account routing misalignment between transfer legs.")

        if mismatches:
            return RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                rule_category=rule.rule_category,
                severity=rule.severity,
                weight=rule.weight,
                triggered=True,
                reason_code="TRANSFER_RECONCILIATION_FAILURE",
                explanation=f"Transfer leg reconciliation failure: {'; '.join(mismatches)}.",
                evidence=evidence
            )
        return None

    def evaluate_alert_integrity(self, alert_id: str, triggered_txn_ids: List[str]) -> Optional[RuleResult]:
        """
        Rule 4: Alert Has No Triggering Transaction (RULE-ALERT-NO-TXN)
        Flags alerts without triggering transactions as data integrity failures.
        """
        rule = self.rules_config.get("RULE-ALERT-NO-TXN")
        if not rule or not rule.enabled:
            return None

        if not triggered_txn_ids:
            return RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                rule_category=rule.rule_category,
                severity=rule.severity,
                weight=rule.weight,
                triggered=True,
                reason_code="INTEGRITY_ORPHANED_ALERT",
                explanation=f"Data integrity fault: Alert {alert_id} was generated without any triggering transaction IDs.",
                evidence={"alert_id": alert_id, "triggered_transaction_ids": []}
            )
        return None

    def evaluate_case_chronology(
        self,
        case_id: str,
        alert_created_at: str,
        case_disposition_timestamp: Optional[str]
    ) -> Optional[RuleResult]:
        """
        Rule 5: Case Disposition Precedes Alert (RULE-CASE-CHRONOLOGY)
        Validates chronological ordering between alert creation and case disposition.
        """
        rule = self.rules_config.get("RULE-CASE-CHRONOLOGY")
        if not rule or not rule.enabled or not case_disposition_timestamp:
            return None

        try:
            a_dt = datetime.fromisoformat(alert_created_at.replace("Z", "+00:00"))
            d_dt = datetime.fromisoformat(case_disposition_timestamp.replace("Z", "+00:00"))
            if d_dt < a_dt:
                return RuleResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    rule_category=rule.rule_category,
                    severity=rule.severity,
                    weight=rule.weight,
                    triggered=True,
                    reason_code="CHRONOLOGY_VIOLATION_CASE_ALERT",
                    explanation=f"Chronological anomaly: Case {case_id} disposition at {case_disposition_timestamp} precedes alert creation at {alert_created_at}.",
                    evidence={
                        "case_id": case_id,
                        "alert_created_at": alert_created_at,
                        "disposition_timestamp": case_disposition_timestamp
                    }
                )
        except Exception:
            pass
        return None
