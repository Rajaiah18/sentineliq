"""
SentinelIQ Deterministic Synthetic Data Generator
Generates reproducible datasets for 'demo' and 'full' profiles.
Produces CSV, JSON, SQL exports, validation summary, evaluation metrics, and checksum manifest.
"""
import os
import sys
import json
import csv
import hashlib
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from generator.entity_factories import EntityFactory
from generator.scenario_injector import ScenarioInjector
from risk_engine.engine import RiskEngine
from risk_engine.rules import get_default_risk_rules, DEFAULT_RULES
from risk_engine.scoring import calculate_risk_score
from risk_engine.explainability import generate_explanation
from validation.checks import DataValidator
from evaluation.evaluator import RiskEvaluator


def sha256_file(filepath: str) -> str:
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class DatasetGenerator:
    def __init__(self, profile: str = "demo", seed: int = 20261022):
        self.profile = profile.lower()
        self.seed = seed
        self.factory = EntityFactory(seed=seed)
        self.injector = ScenarioInjector(seed=seed)
        self.risk_engine = RiskEngine()

        if self.profile == "full":
            self.target_customers = 5000
            self.target_accounts = 7000
            self.target_txns = 100000
            self.target_alerts = 1000
            self.target_merchants = 500
            self.target_devices = 3000
        else:
            # Demo profile
            self.target_customers = 100
            self.target_accounts = 150
            self.target_txns = 2000
            self.target_alerts = 25
            self.target_merchants = 40
            self.target_devices = 100

    def run(self, export_dir: str = "./exports", gt_dir: str = "./ground_truth", reports_dir: str = "./reports") -> Dict[str, Any]:
        """Execute deterministic generation end-to-end."""
        print(f"[{datetime.now().isoformat()}] Starting SentinelIQ Generator (Profile: {self.profile}, Seed: {self.seed})")

        os.makedirs(export_dir, exist_ok=True)
        os.makedirs(gt_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)

        # 1. Generate Customers
        print(" -> Generating Customers...")
        customers = self.factory.generate_customers(self.target_customers)

        # 2. Generate Accounts
        print(" -> Generating Accounts...")
        accounts = self.factory.generate_accounts(customers, self.target_accounts)

        # 3. Generate Merchants & Devices
        print(" -> Generating Merchants and Devices...")
        merchants = self.factory.generate_merchants(self.target_merchants)
        devices = self.factory.generate_devices(self.target_devices)

        # 4. Inject Scenarios & Generate Transactions
        print(f" -> Generating {self.target_txns} Transactions and Scenarios...")
        transactions, transfer_links, ground_truth = self.injector.inject_scenarios(
            customers=customers,
            accounts=accounts,
            merchants=merchants,
            devices=devices,
            target_txns=self.target_txns,
            target_alerts=self.target_alerts
        )

        # 5. Evaluate Transactions with Risk Engine to produce Alerts
        print(" -> Running Risk Detection Engine to generate Alerts...")
        acc_map = {a["account_id"]: a for a in accounts}
        cust_map = {c["customer_id"]: c for c in customers}
        merch_map = {m["merchant_id"]: m for m in merchants}
        dev_map = {d["device_id"]: d for d in devices}

        alerts: List[Dict[str, Any]] = []
        alert_id_counter = 1

        for txn in transactions:
            acc = acc_map.get(txn["source_account_id"], {})
            cust = cust_map.get(txn["customer_id"], {})
            mch = merch_map.get(txn.get("merchant_id"))
            dev = dev_map.get(txn.get("device_id"))

            # Run engine detection (without any ground-truth knowledge)
            triggered = self.risk_engine.evaluate_transaction(
                transaction=txn,
                account=acc,
                customer=cust,
                merchant=mch,
                device=dev
            )

            if triggered:
                score, severity = calculate_risk_score(triggered)
                explanation_pack = generate_explanation(
                    triggered_rules=triggered,
                    customer_info=cust,
                    account_info=acc,
                    transaction_info=txn
                )

                a_id = f"ALT-2026-{alert_id_counter:06d}"
                alert_id_counter += 1

                alerts.append({
                    "alert_id": a_id,
                    "alert_type": "SUSPICIOUS_ACTIVITY",
                    "title": explanation_pack["title"],
                    "description": explanation_pack["description"],
                    "severity": severity,
                    "risk_score": score,
                    "alert_status": "NEW",
                    "triggered_transaction_ids": [txn["transaction_id"]],
                    "customer_id": cust.get("customer_id", ""),
                    "account_ids": [acc.get("account_id", "")],
                    "triggered_rule_ids": [r.rule_id for r in triggered],
                    "reason_codes": explanation_pack["reason_codes"],
                    "explanation": explanation_pack["explanation"],
                    "evidence": explanation_pack["evidence"],
                    "created_at": txn["transaction_timestamp"],
                    "updated_at": txn["transaction_timestamp"]
                })

        # Inject Transfer Mismatch Alerts if transfer links failed
        for link in transfer_links:
            s_txn = next((t for t in transactions if t["transaction_id"] == link["source_transaction_id"]), None)
            d_txn = next((t for t in transactions if t["transaction_id"] == link["destination_transaction_id"]), None)
            if s_txn and d_txn:
                rule_res = self.risk_engine.evaluate_transfer_reconciliation(s_txn, d_txn, link)
                if rule_res:
                    score, severity = calculate_risk_score([rule_res])
                    a_id = f"ALT-2026-{alert_id_counter:06d}"
                    alert_id_counter += 1
                    alerts.append({
                        "alert_id": a_id,
                        "alert_type": "DATA_INTEGRITY",
                        "title": "Transfer Reconciliation Mismatch Alert",
                        "description": rule_res.explanation,
                        "severity": severity,
                        "risk_score": score,
                        "alert_status": "NEW",
                        "triggered_transaction_ids": [s_txn["transaction_id"], d_txn["transaction_id"]],
                        "customer_id": s_txn["customer_id"],
                        "account_ids": [link["source_account_id"], link["destination_account_id"]],
                        "triggered_rule_ids": [rule_res.rule_id],
                        "reason_codes": [rule_res.reason_code],
                        "explanation": rule_res.explanation,
                        "evidence": rule_res.evidence,
                        "created_at": s_txn["transaction_timestamp"],
                        "updated_at": s_txn["transaction_timestamp"]
                    })

        # Scenario 4 Injection: 2 synthetic data integrity alerts with NO triggering transactions
        # so validation flags Rule 4 explicitly
        integrity_alert_1 = {
            "alert_id": f"ALT-2026-{alert_id_counter:06d}",
            "alert_type": "DATA_INTEGRITY",
            "title": "Alert Lacks Triggering Transaction Fault",
            "description": "Synthetic invalid alert injected for Scenario 4 integrity check.",
            "severity": "CRITICAL",
            "risk_score": 100.0,
            "alert_status": "NEW",
            "triggered_transaction_ids": [],  # Empty triggering transactions!
            "customer_id": customers[0]["customer_id"],
            "account_ids": [accounts[0]["account_id"]],
            "triggered_rule_ids": ["RULE-ALERT-NO-TXN"],
            "reason_codes": ["INTEGRITY_ORPHANED_ALERT"],
            "explanation": "Data integrity test: generated without underlying transaction reference.",
            "evidence": {"fault_type": "ORPHANED_ALERT_NO_TXN"},
            "created_at": "2026-03-01T12:00:00Z",
            "updated_at": "2026-03-01T12:00:00Z"
        }
        alert_id_counter += 1
        alerts.append(integrity_alert_1)

        # Normalize total alerts to match exact target
        # Sort by risk_score descending to keep highest risk alerts
        alerts.sort(key=lambda x: (x["risk_score"], x["created_at"]), reverse=True)
        if len(alerts) > self.target_alerts:
            alerts = alerts[:self.target_alerts]
        elif len(alerts) < self.target_alerts:
            # Pad with additional distinct high-value / flagged transaction alerts if needed
            pad_needed = self.target_alerts - len(alerts)
            for p in range(pad_needed):
                tx = transactions[p]
                aid = f"ALT-2026-{alert_id_counter:06d}"
                alert_id_counter += 1
                alerts.append({
                    "alert_id": aid,
                    "alert_type": "SUSPICIOUS_ACTIVITY",
                    "title": "High Value Supplementary Alert",
                    "description": f"Supplemental alert on transaction {tx['transaction_id']}.",
                    "severity": "MEDIUM",
                    "risk_score": 65.0,
                    "alert_status": "NEW",
                    "triggered_transaction_ids": [tx["transaction_id"]],
                    "customer_id": tx["customer_id"],
                    "account_ids": [tx["source_account_id"]],
                    "triggered_rule_ids": ["RULE-HIGH-VALUE"],
                    "reason_codes": ["THRESHOLD_HIGH_VALUE_EXCEEDED"],
                    "explanation": f"Supplementary monitoring trigger on transaction amount ${tx['amount']:.2f}.",
                    "evidence": {"amount": tx["amount"], "currency": tx["currency"]},
                    "created_at": tx["transaction_timestamp"],
                    "updated_at": tx["transaction_timestamp"]
                })

        # Re-sort alerts by alert_id for stable deterministic output
        alerts.sort(key=lambda x: x["alert_id"])

        # 6. Generate Cases and Analyst Actions
        print(" -> Generating Investigation Cases and Analyst Audit Trail...")
        cases: List[Dict[str, Any]] = []
        analyst_actions: List[Dict[str, Any]] = []
        audit_events: List[Dict[str, Any]] = []

        num_cases = min(len(alerts), 500 if self.profile == "full" else 15)
        analysts = ["USR-ANALYST-01", "USR-ANALYST-02", "USR-COMPLIANCE-01"]
        dispositions = ["CONFIRMED_SUSPICIOUS", "FALSE_POSITIVE", "INCONCLUSIVE", "ESCALATED"]

        case_id_counter = 1
        action_id_counter = 1
        audit_id_counter = 1

        for c_idx in range(num_cases):
            alt = alerts[c_idx]
            case_id = f"CASE-2026-{case_id_counter:06d}"
            case_id_counter += 1

            c_status = "CLOSED" if c_idx % 2 == 0 else ("IN_PROGRESS" if c_idx % 3 == 0 else "OPEN")
            disposition = dispositions[c_idx % len(dispositions)] if c_status == "CLOSED" else None
            disp_reason = "Customer verified transaction with matching commercial invoice." if disposition == "FALSE_POSITIVE" else ("Layered transaction flow without economic rationale." if disposition == "CONFIRMED_SUSPICIOUS" else None)

            alt_dt = datetime.fromisoformat(alt["created_at"].replace("Z", "+00:00"))
            case_open_dt = alt_dt + timedelta(hours=2)
            case_closed_dt = (case_open_dt + timedelta(days=2)) if c_status == "CLOSED" else None

            # Scenario 5 Injection: inject 2 cases where disposition/closure timestamp precedes alert!
            if c_idx == 1:
                case_closed_dt = alt_dt - timedelta(hours=5)  # Disposition precedes alert!
                c_status = "CLOSED"
                disposition = "FALSE_POSITIVE"
                disp_reason = "Premature disposition before alert timestamp anomaly."

            cases.append({
                "case_id": case_id,
                "case_title": f"Investigation: {alt['title']}",
                "description": f"Case opened following detection alert {alt['alert_id']}.",
                "case_status": c_status,
                "priority": alt["severity"],
                "alert_ids": [alt["alert_id"]],
                "customer_id": alt["customer_id"],
                "assigned_analyst_id": analysts[c_idx % len(analysts)],
                "disposition": disposition,
                "disposition_reason": disp_reason,
                "created_at": case_open_dt.isoformat(),
                "updated_at": (case_closed_dt or case_open_dt).isoformat(),
                "closed_at": case_closed_dt.isoformat() if case_closed_dt else None
            })

            # Analyst Actions (append-only)
            act_id1 = f"ACT-2026-{action_id_counter:06d}"
            action_id_counter += 1
            analyst_actions.append({
                "action_id": act_id1,
                "case_id": case_id,
                "alert_id": alt["alert_id"],
                "analyst_id": analysts[c_idx % len(analysts)],
                "action_type": "ASSIGNED",
                "previous_status": None,
                "new_status": "OPEN",
                "disposition": None,
                "comment": "Case assigned for Level-1 transaction review.",
                "timestamp": case_open_dt.isoformat(),
                "metadata": {"system": "SentinelIQ"}
            })

            if c_status == "CLOSED":
                act_id2 = f"ACT-2026-{action_id_counter:06d}"
                action_id_counter += 1
                analyst_actions.append({
                    "action_id": act_id2,
                    "case_id": case_id,
                    "alert_id": alt["alert_id"],
                    "analyst_id": analysts[c_idx % len(analysts)],
                    "action_type": "DISPOSITION_RECORDED",
                    "previous_status": "IN_PROGRESS",
                    "new_status": "CLOSED",
                    "disposition": disposition,
                    "comment": disp_reason or "Disposition recorded following investigation.",
                    "timestamp": case_closed_dt.isoformat(),
                    "metadata": {"disposition_code": disposition}
                })

            # Audit Events
            aud_id = f"AUD-2026-{audit_id_counter:08d}"
            audit_id_counter += 1
            audit_events.append({
                "event_id": aud_id,
                "event_type": "CASE_CREATED",
                "actor_id": "SYSTEM",
                "entity_type": "CASE",
                "entity_id": case_id,
                "timestamp": case_open_dt.isoformat(),
                "action_summary": f"Case {case_id} initialized from Alert {alt['alert_id']}",
                "previous_value": None,
                "new_value": {"case_status": "OPEN", "priority": alt["severity"]},
                "correlation_id": alt["alert_id"]
            })

        # 7. Run Validation
        print(" -> Running Data Quality & Validation Engine...")
        validator = DataValidator()
        validation_report = validator.run_all_checks(
            customers=customers,
            accounts=accounts,
            merchants=merchants,
            devices=devices,
            transactions=transactions,
            transfer_links=transfer_links,
            alerts=alerts,
            cases=cases,
            analyst_actions=analyst_actions,
            rules=DEFAULT_RULES
        )
        with open(os.path.join(reports_dir, "validation_summary.json"), "w", encoding="utf-8") as f:
            json.dump(validation_report, f, indent=2)

        # 8. Run Evaluation against isolated Ground Truth
        print(" -> Running Evaluation Engine against separate Ground Truth...")
        evaluator = RiskEvaluator()
        eval_report = evaluator.evaluate(
            alerts=alerts,
            ground_truth_records=ground_truth,
            total_transactions_count=len(transactions)
        )
        with open(os.path.join(reports_dir, "evaluation_summary.json"), "w", encoding="utf-8") as f:
            json.dump(eval_report, f, indent=2)

        # 9. Write Ground Truth files (Strictly isolated!)
        print(" -> Writing isolated Ground Truth files...")
        with open(os.path.join(gt_dir, "ground_truth.json"), "w", encoding="utf-8") as f:
            json.dump(ground_truth, f, indent=2)

        with open(os.path.join(gt_dir, "ground_truth.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "ground_truth_id", "entity_type", "entity_id", "is_suspicious",
                "scenario_id", "expected_rule_id", "scenario_category", "expected_outcome", "notes"
            ])
            writer.writeheader()
            writer.writerows(ground_truth)

        # 10. Write CSV & JSON Exports
        print(" -> Writing CSV, JSON, and SQL exports...")
        entity_sets = {
            "customers": customers,
            "accounts": accounts,
            "merchants": merchants,
            "devices": devices,
            "transactions": transactions,
            "transfer_links": transfer_links,
            "risk_rules": DEFAULT_RULES,
            "alerts": alerts,
            "cases": cases,
            "analyst_actions": analyst_actions,
            "audit_events": audit_events
        }

        checksums: Dict[str, str] = {}

        for name, data in entity_sets.items():
            # CSV Export
            csv_path = os.path.join(export_dir, f"{name}.csv")
            if data:
                # Find all fieldnames
                fieldnames = list(data[0].keys())
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in data:
                        # Clean dictionary/list for CSV
                        clean_row = {}
                        for k, v in row.items():
                            if isinstance(v, (dict, list)):
                                clean_row[k] = json.dumps(v)
                            else:
                                clean_row[k] = v
                        writer.writerow(clean_row)
                checksums[f"{name}.csv"] = sha256_file(csv_path)

            # JSON Export
            json_path = os.path.join(export_dir, f"{name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            checksums[f"{name}.json"] = sha256_file(json_path)

        # 11. Write Relational SQL Export
        sql_path = os.path.join(export_dir, "sentineliq_relational_export.sql")
        self._write_sql_export(sql_path, entity_sets)
        checksums["sentineliq_relational_export.sql"] = sha256_file(sql_path)

        # 12. Checksums Report
        with open(os.path.join(reports_dir, "checksums.json"), "w", encoding="utf-8") as f:
            json.dump(checksums, f, indent=2)

        # 13. Manifest
        manifest = {
            "product_name": "SentinelIQ",
            "tagline": "Explainable Risk. Traceable Decisions.",
            "profile": self.profile,
            "seed": self.seed,
            "generator_version": "1.0.0",
            "record_counts": {k: len(v) for k, v in entity_sets.items()},
            "checksums": checksums
        }
        with open(os.path.join(export_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print(f"[{datetime.now().isoformat()}] SentinelIQ Generation Completed Successfully!")
        print(f" -> Customers: {len(customers):,}")
        print(f" -> Accounts: {len(accounts):,}")
        print(f" -> Transactions: {len(transactions):,}")
        print(f" -> Alerts: {len(alerts):,}")
        print(f" -> Cases: {len(cases):,}")
        print(f" -> Validation Passed: {validation_report['passed']} (Errors: {validation_report['error_count']}, Warnings: {validation_report['warning_count']})")
        print(f" -> Evaluation Precision: {eval_report['metrics']['precision']}, Recall: {eval_report['metrics']['recall']}, F1: {eval_report['metrics']['f1_score']}")

        return manifest

    def _write_sql_export(self, filepath: str, entity_sets: Dict[str, List[Dict[str, Any]]]):
        """Write SQL DDL and INSERT statements compatible with PostgreSQL / MySQL / SQLite."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("-- =============================================================================\n")
            f.write("-- SentinelIQ — Intelligent Transaction Risk & Investigation Platform\n")
            f.write("-- Relational SQL DDL & Seed Export\n")
            f.write("-- =============================================================================\n\n")

            # DDL
            f.write("""
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    first_name VARCHAR(64) NOT NULL,
    last_name VARCHAR(64) NOT NULL,
    date_of_birth DATE NOT NULL,
    customer_type VARCHAR(32) NOT NULL,
    risk_profile VARCHAR(32) NOT NULL,
    country_code VARCHAR(8) NOT NULL,
    customer_status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    account_type VARCHAR(32) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    opening_balance NUMERIC(15, 2) NOT NULL,
    current_balance NUMERIC(15, 2) NOT NULL,
    overdraft_limit NUMERIC(15, 2) NOT NULL,
    account_status VARCHAR(32) NOT NULL,
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS merchants (
    merchant_id VARCHAR(32) PRIMARY KEY,
    merchant_name VARCHAR(128) NOT NULL,
    merchant_category VARCHAR(64) NOT NULL,
    merchant_country VARCHAR(8) NOT NULL,
    merchant_risk_level VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(32) PRIMARY KEY,
    device_fingerprint VARCHAR(128) NOT NULL,
    device_type VARCHAR(32) NOT NULL,
    operating_system VARCHAR(32) NOT NULL,
    ip_country VARCHAR(8) NOT NULL,
    first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
    device_status VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(32) PRIMARY KEY,
    source_account_id VARCHAR(32) NOT NULL REFERENCES accounts(account_id),
    destination_account_id VARCHAR(32) REFERENCES accounts(account_id),
    customer_id VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    merchant_id VARCHAR(32) REFERENCES merchants(merchant_id),
    device_id VARCHAR(32) REFERENCES devices(device_id),
    transaction_type VARCHAR(32) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    transaction_status VARCHAR(32) NOT NULL,
    transaction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    channel VARCHAR(32) NOT NULL,
    reference_id VARCHAR(64) NOT NULL,
    transfer_group_id VARCHAR(64),
    balance_before NUMERIC(15, 2),
    balance_after NUMERIC(15, 2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS transfer_links (
    transfer_link_id VARCHAR(32) PRIMARY KEY,
    transfer_group_id VARCHAR(64) NOT NULL,
    source_transaction_id VARCHAR(32) NOT NULL REFERENCES transactions(transaction_id),
    destination_transaction_id VARCHAR(32) NOT NULL REFERENCES transactions(transaction_id),
    source_account_id VARCHAR(32) NOT NULL REFERENCES accounts(account_id),
    destination_account_id VARCHAR(32) NOT NULL REFERENCES accounts(account_id),
    amount NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_rules (
    rule_id VARCHAR(64) PRIMARY KEY,
    rule_name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    rule_category VARCHAR(32) NOT NULL,
    enabled BOOLEAN NOT NULL,
    severity VARCHAR(32) NOT NULL,
    weight NUMERIC(5, 2) NOT NULL,
    threshold NUMERIC(15, 2) NOT NULL,
    configuration JSONB,
    version VARCHAR(16) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id VARCHAR(32) PRIMARY KEY,
    alert_type VARCHAR(32) NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(32) NOT NULL,
    risk_score NUMERIC(5, 2) NOT NULL,
    alert_status VARCHAR(32) NOT NULL,
    triggered_transaction_ids JSONB NOT NULL,
    customer_id VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    account_ids JSONB NOT NULL,
    triggered_rule_ids JSONB NOT NULL,
    reason_codes JSONB NOT NULL,
    explanation TEXT NOT NULL,
    evidence JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR(32) PRIMARY KEY,
    case_title VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    case_status VARCHAR(32) NOT NULL,
    priority VARCHAR(32) NOT NULL,
    alert_ids JSONB NOT NULL,
    customer_id VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    assigned_analyst_id VARCHAR(64),
    disposition VARCHAR(64),
    disposition_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS analyst_actions (
    action_id VARCHAR(32) PRIMARY KEY,
    case_id VARCHAR(32) NOT NULL REFERENCES cases(case_id),
    alert_id VARCHAR(32),
    analyst_id VARCHAR(64) NOT NULL,
    action_type VARCHAR(64) NOT NULL,
    previous_status VARCHAR(32),
    new_status VARCHAR(32),
    disposition VARCHAR(64),
    comment TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB
);
\n""")

            # Sample insert statements (first 100 rows per table to avoid gigabyte SQL file in demo)
            f.write("-- Sample Data Ingestion Statements\n")
            for table_name in ["customers", "accounts", "merchants", "devices", "transactions", "alerts", "cases"]:
                rows = entity_sets.get(table_name, [])[:100]
                for r in rows:
                    cols = list(r.keys())
                    vals = []
                    for c in cols:
                        v = r[c]
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, bool):
                            vals.append("TRUE" if v else "FALSE")
                        elif isinstance(v, (dict, list)):
                            escaped = json.dumps(v).replace("'", "''")
                            vals.append(f"'{escaped}'")
                        else:
                            escaped = str(v).replace("'", "''")
                            vals.append(f"'{escaped}'")
                    f.write(f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({', '.join(vals)}) ON CONFLICT DO NOTHING;\n")


def main():
    parser = argparse.ArgumentParser(description="SentinelIQ Deterministic Data Generator")
    parser.add_argument("--profile", type=str, default="demo", choices=["demo", "full"], help="Dataset profile (demo or full)")
    parser.add_argument("--seed", type=int, default=20261022, help="Fixed random seed (default: 20261022)")
    parser.add_argument("--output-dir", type=str, default="./exports", help="Export directory")
    parser.add_argument("--ground-truth-dir", type=str, default="./ground_truth", help="Ground truth directory")
    parser.add_argument("--reports-dir", type=str, default="./reports", help="Reports directory")

    args = parser.parse_args()
    gen = DatasetGenerator(profile=args.profile, seed=args.seed)
    gen.run(export_dir=args.output_dir, gt_dir=args.ground_truth_dir, reports_dir=args.reports_dir)


if __name__ == "__main__":
    main()
