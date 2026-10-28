"""
SentinelIQ Scenario Injector
Plans and injects mandatory negative scenarios and realistic suspicious financial patterns.
Produces separate Ground Truth labels for independent validation and evaluation.
"""
import random
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta


class ScenarioInjector:
    def __init__(self, seed: int = 20261022):
        self.seed = seed
        self.rng = random.Random(seed)
        self.ground_truth_records: List[Dict[str, Any]] = []
        self.gt_counter = 1

    def _record_ground_truth(
        self,
        entity_type: str,
        entity_id: str,
        is_suspicious: bool,
        scenario_id: str,
        expected_rule_id: str,
        scenario_category: str,
        expected_outcome: str,
        notes: str
    ):
        """Record an isolated ground-truth entry."""
        gt_id = f"GT-2026-{self.gt_counter:08d}"
        self.gt_counter += 1
        self.ground_truth_records.append({
            "ground_truth_id": gt_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "is_suspicious": is_suspicious,
            "scenario_id": scenario_id,
            "expected_rule_id": expected_rule_id,
            "scenario_category": scenario_category,
            "expected_outcome": expected_outcome,
            "notes": notes
        })

    def inject_scenarios(
        self,
        customers: List[Dict[str, Any]],
        accounts: List[Dict[str, Any]],
        merchants: List[Dict[str, Any]],
        devices: List[Dict[str, Any]],
        target_txns: int,
        target_alerts: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generate target_txns transactions with planned suspicious and negative scenarios.
        Returns:
            transactions: List[Dict[str, Any]]
            transfer_links: List[Dict[str, Any]]
            ground_truth_records: List[Dict[str, Any]]
        """
        transactions: List[Dict[str, Any]] = []
        transfer_links: List[Dict[str, Any]] = []

        base_dt = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        acc_map = {a["account_id"]: a for a in accounts}
        cust_map = {c["customer_id"]: c for c in customers}

        # -------------------------------------------------------------
        # Step 1: Designate specific accounts for scenario injections
        # -------------------------------------------------------------
        # Mark 3% of accounts as CLOSED at a fixed date
        closed_accounts: List[Dict[str, Any]] = []
        open_accounts: List[Dict[str, Any]] = []

        for i, acc in enumerate(accounts):
            if i % 35 == 0 and len(closed_accounts) < 150:
                acc["account_status"] = "CLOSED"
                opened_dt = datetime.fromisoformat(acc["opened_at"].replace("Z", "+00:00"))
                c_date = opened_dt + timedelta(days=self.rng.randint(15, 60), hours=10)
                acc["closed_at"] = c_date.isoformat()
                closed_accounts.append(acc)
            else:
                open_accounts.append(acc)

        # Calculate exact counts of anomalous scenarios to hit target_alerts
        # In full profile (target_alerts=1000, target_txns=100000):
        # We inject enough scenario transactions to generate approximately target_alerts
        num_closed_txns = max(5, int(target_alerts * 0.08))      # ~80
        num_overdraft_txns = max(5, int(target_alerts * 0.08))   # ~80
        num_transfer_mismatches = max(5, int(target_alerts * 0.08))  # ~80
        num_high_val = max(10, int(target_alerts * 0.30))        # ~300
        num_velocity_bursts = max(5, int(target_alerts * 0.05)) # ~50 bursts (each 6 txns = 300 txns, generating alerts)
        num_device_anomalies = max(10, int(target_alerts * 0.12)) # ~120
        num_dormant = max(5, int(target_alerts * 0.08))          # ~80
        num_high_risk_merch = max(10, int(target_alerts * 0.14)) # ~140
        num_multi_signal = max(5, int(target_alerts * 0.06))     # ~60

        txn_id_counter = 1
        link_id_counter = 1
        transfer_grp_counter = 1

        # -------------------------------------------------------------
        # Scenario 1: Closed-Account Transactions (RULE-CLOSED-ACCOUNT)
        # -------------------------------------------------------------
        for k in range(num_closed_txns):
            acc = closed_accounts[k % len(closed_accounts)]
            cust_id = acc["customer_id"]
            cust = cust_map[cust_id]
            tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1

            # Transaction timestamp is after closure
            closed_dt = datetime.fromisoformat(acc["closed_at"])
            txn_dt = closed_dt + timedelta(days=self.rng.randint(1, 20), hours=self.rng.randint(1, 12))

            amt = round(self.rng.uniform(100.0, 2500.0), 2)
            transactions.append({
                "transaction_id": tid,
                "source_account_id": acc["account_id"],
                "destination_account_id": None,
                "customer_id": cust_id,
                "merchant_id": merchants[k % len(merchants)]["merchant_id"],
                "device_id": devices[k % len(devices)]["device_id"],
                "transaction_type": "CARD_PAYMENT",
                "amount": amt,
                "currency": acc["currency"],
                "transaction_status": "FAILED",
                "transaction_timestamp": txn_dt.isoformat(),
                "channel": "POS",
                "reference_id": f"REF-CLOSED-{k:05d}",
                "transfer_group_id": None,
                "balance_before": acc["current_balance"],
                "balance_after": acc["current_balance"],
                "created_at": txn_dt.isoformat()
            })

            self._record_ground_truth(
                entity_type="TRANSACTION",
                entity_id=tid,
                is_suspicious=True,
                scenario_id="SCEN-CLOSED-ACCOUNT",
                expected_rule_id="RULE-CLOSED-ACCOUNT",
                scenario_category="INTEGRITY",
                expected_outcome="DETECTED_VIOLATION",
                notes="Transaction attempted against a closed account."
            )

        # -------------------------------------------------------------
        # Scenario 2: Negative Balance Beyond Overdraft (RULE-OVERDRAFT-EXCEEDED)
        # -------------------------------------------------------------
        for k in range(num_overdraft_txns):
            acc = open_accounts[k % len(open_accounts)]
            cust_id = acc["customer_id"]
            tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1

            txn_dt = base_dt + timedelta(days=self.rng.randint(10, 150), hours=self.rng.randint(0, 23))
            overdraft_limit = float(acc["overdraft_limit"])
            current_bal = float(acc["current_balance"])

            # Force withdrawal that causes deficit beyond overdraft
            breach_amount = round(overdraft_limit + 1500.0 + self.rng.uniform(100.0, 1000.0), 2)
            txn_amt = round(current_bal + breach_amount, 2)
            bal_after = round(current_bal - txn_amt, 2)

            transactions.append({
                "transaction_id": tid,
                "source_account_id": acc["account_id"],
                "destination_account_id": None,
                "customer_id": cust_id,
                "merchant_id": None,
                "device_id": devices[k % len(devices)]["device_id"],
                "transaction_type": "CASH_WITHDRAWAL",
                "amount": txn_amt,
                "currency": acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": txn_dt.isoformat(),
                "channel": "ATM",
                "reference_id": f"REF-OVERDRAFT-{k:05d}",
                "transfer_group_id": None,
                "balance_before": current_bal,
                "balance_after": bal_after,
                "created_at": txn_dt.isoformat()
            })

            self._record_ground_truth(
                entity_type="TRANSACTION",
                entity_id=tid,
                is_suspicious=True,
                scenario_id="SCEN-OVERDRAFT-BREACH",
                expected_rule_id="RULE-OVERDRAFT-EXCEEDED",
                scenario_category="INTEGRITY",
                expected_outcome="DETECTED_VIOLATION",
                notes="Balance dipped into negative beyond authorized overdraft limit."
            )

        # -------------------------------------------------------------
        # Scenario 3: Transfer Legs Mismatch (RULE-TRANSFER-MISMATCH)
        # -------------------------------------------------------------
        for k in range(num_transfer_mismatches):
            src_acc = open_accounts[k % len(open_accounts)]
            dst_acc = open_accounts[(k + 1) % len(open_accounts)]

            grp_id = f"GRP-2026-{transfer_grp_counter:08d}"
            transfer_grp_counter += 1

            s_tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1
            d_tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1

            link_id = f"TRL-2026-{link_id_counter:08d}"
            link_id_counter += 1

            txn_dt = base_dt + timedelta(days=self.rng.randint(15, 120), hours=self.rng.randint(0, 23))

            src_amt = round(self.rng.uniform(5000.0, 20000.0), 2)
            # Inject discrepancy: destination leg has 10% lower amount or different currency
            dst_amt = round(src_amt * 0.90, 2)

            transactions.append({
                "transaction_id": s_tid,
                "source_account_id": src_acc["account_id"],
                "destination_account_id": dst_acc["account_id"],
                "customer_id": src_acc["customer_id"],
                "merchant_id": None,
                "device_id": devices[k % len(devices)]["device_id"],
                "transaction_type": "ACCOUNT_TRANSFER",
                "amount": src_amt,
                "currency": src_acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": txn_dt.isoformat(),
                "channel": "WEB_PORTAL",
                "reference_id": f"REF-TRF-SRC-{k:05d}",
                "transfer_group_id": grp_id,
                "balance_before": src_acc["current_balance"],
                "balance_after": round(src_acc["current_balance"] - src_amt, 2),
                "created_at": txn_dt.isoformat()
            })

            transactions.append({
                "transaction_id": d_tid,
                "source_account_id": dst_acc["account_id"],
                "destination_account_id": src_acc["account_id"],
                "customer_id": dst_acc["customer_id"],
                "merchant_id": None,
                "device_id": devices[k % len(devices)]["device_id"],
                "transaction_type": "ACCOUNT_TRANSFER",
                "amount": dst_amt,
                "currency": dst_acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": (txn_dt + timedelta(minutes=5)).isoformat(),
                "channel": "WEB_PORTAL",
                "reference_id": f"REF-TRF-DST-{k:05d}",
                "transfer_group_id": grp_id,
                "balance_before": dst_acc["current_balance"],
                "balance_after": round(dst_acc["current_balance"] + dst_amt, 2),
                "created_at": (txn_dt + timedelta(minutes=5)).isoformat()
            })

            transfer_links.append({
                "transfer_link_id": link_id,
                "transfer_group_id": grp_id,
                "source_transaction_id": s_tid,
                "destination_transaction_id": d_tid,
                "source_account_id": src_acc["account_id"],
                "destination_account_id": dst_acc["account_id"],
                "amount": src_amt,
                "currency": src_acc["currency"],
                "created_at": txn_dt.isoformat()
            })

            self._record_ground_truth(
                entity_type="TRANSACTION",
                entity_id=s_tid,
                is_suspicious=True,
                scenario_id="SCEN-TRANSFER-MISMATCH",
                expected_rule_id="RULE-TRANSFER-MISMATCH",
                scenario_category="INTEGRITY",
                expected_outcome="DETECTED_VIOLATION",
                notes="Outgoing transfer leg does not reconcile with destination leg."
            )

        # -------------------------------------------------------------
        # Scenario 6: High Value Transactions (RULE-HIGH-VALUE)
        # -------------------------------------------------------------
        for k in range(num_high_val):
            acc = open_accounts[k % len(open_accounts)]
            tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1

            txn_dt = base_dt + timedelta(days=self.rng.randint(5, 170), hours=self.rng.randint(0, 23))
            # Amount >= $10,000 threshold
            amt = round(self.rng.uniform(10500.0, 75000.0), 2)

            transactions.append({
                "transaction_id": tid,
                "source_account_id": acc["account_id"],
                "destination_account_id": None,
                "customer_id": acc["customer_id"],
                "merchant_id": None,
                "device_id": devices[k % len(devices)]["device_id"],
                "transaction_type": "BANK_TRANSFER",
                "amount": amt,
                "currency": acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": txn_dt.isoformat(),
                "channel": "WEB_PORTAL",
                "reference_id": f"REF-HV-{k:05d}",
                "transfer_group_id": None,
                "balance_before": acc["current_balance"] + amt,
                "balance_after": acc["current_balance"],
                "created_at": txn_dt.isoformat()
            })

            self._record_ground_truth(
                entity_type="TRANSACTION",
                entity_id=tid,
                is_suspicious=True,
                scenario_id="SCEN-HIGH-VALUE",
                expected_rule_id="RULE-HIGH-VALUE",
                scenario_category="VALUE",
                expected_outcome="DETECTED_VIOLATION",
                notes="Single transaction exceeding statutory reporting threshold."
            )

        # -------------------------------------------------------------
        # Scenario 7: Velocity Bursts (>5 in 1 hr) (RULE-VELOCITY)
        # -------------------------------------------------------------
        for b in range(num_velocity_bursts):
            acc = open_accounts[(b * 3) % len(open_accounts)]
            burst_start = base_dt + timedelta(days=self.rng.randint(20, 160), hours=self.rng.randint(0, 20))

            for step in range(6):  # 6 transactions within 30 minutes
                tid = f"TXN-2026-{txn_id_counter:08d}"
                txn_id_counter += 1
                t_step = burst_start + timedelta(minutes=step * 5)
                amt = round(self.rng.uniform(20.0, 300.0), 2)

                transactions.append({
                    "transaction_id": tid,
                    "source_account_id": acc["account_id"],
                    "destination_account_id": None,
                    "customer_id": acc["customer_id"],
                    "merchant_id": merchants[step % len(merchants)]["merchant_id"],
                    "device_id": devices[b % len(devices)]["device_id"],
                    "transaction_type": "PURCHASE",
                    "amount": amt,
                    "currency": acc["currency"],
                    "transaction_status": "COMPLETED",
                    "transaction_timestamp": t_step.isoformat(),
                    "channel": "MOBILE_APP",
                    "reference_id": f"REF-VEL-{b:04d}-{step}",
                    "transfer_group_id": None,
                    "balance_before": acc["current_balance"],
                    "balance_after": acc["current_balance"],
                    "created_at": t_step.isoformat()
                })

                if step >= 5:  # The 6th transaction exceeds threshold
                    self._record_ground_truth(
                        entity_type="TRANSACTION",
                        entity_id=tid,
                        is_suspicious=True,
                        scenario_id="SCEN-HIGH-VELOCITY",
                        expected_rule_id="RULE-VELOCITY",
                        scenario_category="VELOCITY",
                        expected_outcome="DETECTED_VIOLATION",
                        notes="Burst transaction exceeding 5 operations per hour window."
                    )

        # -------------------------------------------------------------
        # Scenario 8: Anomalous Untrusted Device (RULE-NEW-DEVICE)
        # -------------------------------------------------------------
        untrusted_devices = [d for d in devices if d["device_status"] in ("UNTRUSTED", "FLAGGED")]
        if not untrusted_devices:
            devices[0]["device_status"] = "UNTRUSTED"
            untrusted_devices = [devices[0]]

        for k in range(num_device_anomalies):
            acc = open_accounts[(k * 7) % len(open_accounts)]
            dev = untrusted_devices[k % len(untrusted_devices)]
            tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1

            txn_dt = base_dt + timedelta(days=self.rng.randint(10, 160), hours=self.rng.randint(0, 23))
            amt = round(self.rng.uniform(2000.0, 8000.0), 2)

            transactions.append({
                "transaction_id": tid,
                "source_account_id": acc["account_id"],
                "destination_account_id": None,
                "customer_id": acc["customer_id"],
                "merchant_id": None,
                "device_id": dev["device_id"],
                "transaction_type": "BANK_TRANSFER",
                "amount": amt,
                "currency": acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": txn_dt.isoformat(),
                "channel": "MOBILE_APP",
                "reference_id": f"REF-DEV-{k:05d}",
                "transfer_group_id": None,
                "balance_before": acc["current_balance"],
                "balance_after": acc["current_balance"],
                "created_at": txn_dt.isoformat()
            })

            self._record_ground_truth(
                entity_type="TRANSACTION",
                entity_id=tid,
                is_suspicious=True,
                scenario_id="SCEN-ANOMALOUS-DEVICE",
                expected_rule_id="RULE-NEW-DEVICE",
                scenario_category="BEHAVIORAL",
                expected_outcome="DETECTED_VIOLATION",
                notes="Transaction conducted via an untrusted hardware device."
            )

        # -------------------------------------------------------------
        # Scenario 11: High-Risk Merchant Category (RULE-UNUSUAL-MERCHANT)
        # -------------------------------------------------------------
        high_risk_merchants = [m for m in merchants if m["merchant_category"] in ("GAMBLING", "CRYPTO")]
        for k in range(num_high_risk_merch):
            acc = open_accounts[(k * 11) % len(open_accounts)]
            mch = high_risk_merchants[k % len(high_risk_merchants)]
            tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1

            txn_dt = base_dt + timedelta(days=self.rng.randint(5, 170), hours=self.rng.randint(0, 23))
            amt = round(self.rng.uniform(2600.0, 9500.0), 2)

            transactions.append({
                "transaction_id": tid,
                "source_account_id": acc["account_id"],
                "destination_account_id": None,
                "customer_id": acc["customer_id"],
                "merchant_id": mch["merchant_id"],
                "device_id": devices[k % len(devices)]["device_id"],
                "transaction_type": "PURCHASE",
                "amount": amt,
                "currency": acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": txn_dt.isoformat(),
                "channel": "WEB_PORTAL",
                "reference_id": f"REF-HRM-{k:05d}",
                "transfer_group_id": None,
                "balance_before": acc["current_balance"],
                "balance_after": acc["current_balance"],
                "created_at": txn_dt.isoformat()
            })

            self._record_ground_truth(
                entity_type="TRANSACTION",
                entity_id=tid,
                is_suspicious=True,
                scenario_id="SCEN-HIGH-RISK-MERCHANT",
                expected_rule_id="RULE-UNUSUAL-MERCHANT",
                scenario_category="COMPLIANCE",
                expected_outcome="DETECTED_VIOLATION",
                notes="Substantial transaction volume at high-risk merchant category."
            )

        # -------------------------------------------------------------
        # Step 2: Normal Baseline Transactions (Remaining up to target_txns)
        # -------------------------------------------------------------
        # Generate normal legitimate transfers and transactions
        # Reconciled transfer pairs
        num_normal_transfers = min(2000, max(50, target_txns // 20))
        for t in range(num_normal_transfers):
            if txn_id_counter > target_txns - 1:
                break
            src_acc = open_accounts[t % len(open_accounts)]
            dst_acc = open_accounts[(t + 13) % len(open_accounts)]

            grp_id = f"GRP-2026-{transfer_grp_counter:08d}"
            transfer_grp_counter += 1

            s_tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1
            d_tid = f"TXN-2026-{txn_id_counter:08d}"
            txn_id_counter += 1

            link_id = f"TRL-2026-{link_id_counter:08d}"
            link_id_counter += 1

            txn_dt = base_dt + timedelta(days=self.rng.randint(1, 175), hours=self.rng.randint(0, 23))
            t_amt = round(self.rng.uniform(50.0, 1500.0), 2)

            transactions.append({
                "transaction_id": s_tid,
                "source_account_id": src_acc["account_id"],
                "destination_account_id": dst_acc["account_id"],
                "customer_id": src_acc["customer_id"],
                "merchant_id": None,
                "device_id": devices[t % len(devices)]["device_id"],
                "transaction_type": "ACCOUNT_TRANSFER",
                "amount": t_amt,
                "currency": src_acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": txn_dt.isoformat(),
                "channel": "MOBILE_APP",
                "reference_id": f"REF-NORM-TRF-S-{t:06d}",
                "transfer_group_id": grp_id,
                "balance_before": src_acc["current_balance"],
                "balance_after": src_acc["current_balance"],
                "created_at": txn_dt.isoformat()
            })

            transactions.append({
                "transaction_id": d_tid,
                "source_account_id": dst_acc["account_id"],
                "destination_account_id": src_acc["account_id"],
                "customer_id": dst_acc["customer_id"],
                "merchant_id": None,
                "device_id": devices[t % len(devices)]["device_id"],
                "transaction_type": "ACCOUNT_TRANSFER",
                "amount": t_amt,
                "currency": src_acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": (txn_dt + timedelta(minutes=1)).isoformat(),
                "channel": "MOBILE_APP",
                "reference_id": f"REF-NORM-TRF-D-{t:06d}",
                "transfer_group_id": grp_id,
                "balance_before": dst_acc["current_balance"],
                "balance_after": dst_acc["current_balance"],
                "created_at": (txn_dt + timedelta(minutes=1)).isoformat()
            })

            transfer_links.append({
                "transfer_link_id": link_id,
                "transfer_group_id": grp_id,
                "source_transaction_id": s_tid,
                "destination_transaction_id": d_tid,
                "source_account_id": src_acc["account_id"],
                "destination_account_id": dst_acc["account_id"],
                "amount": t_amt,
                "currency": src_acc["currency"],
                "created_at": txn_dt.isoformat()
            })

        # Fill remaining transactions with diverse normal POS, card, purchase, deposit, withdrawal
        channels_cycle = ["POS", "MOBILE_APP", "WEB_PORTAL", "ATM"]
        types_cycle = ["CARD_PAYMENT", "PURCHASE", "DEPOSIT", "CASH_WITHDRAWAL"]

        while txn_id_counter <= target_txns:
            acc = open_accounts[txn_id_counter % len(open_accounts)]
            tid = f"TXN-2026-{txn_id_counter:08d}"

            ch = channels_cycle[txn_id_counter % len(channels_cycle)]
            tt = types_cycle[txn_id_counter % len(types_cycle)]
            mch = merchants[txn_id_counter % len(merchants)] if tt in ("CARD_PAYMENT", "PURCHASE") else None
            dev = devices[txn_id_counter % len(devices)] if ch in ("MOBILE_APP", "WEB_PORTAL") else None

            # Normal small-to-moderate amounts ($5 to $1,500)
            amt = round(self.rng.uniform(5.0, 1500.0), 2)
            txn_dt = base_dt + timedelta(days=self.rng.randint(1, 180), hours=self.rng.randint(0, 23), minutes=self.rng.randint(0, 59))

            transactions.append({
                "transaction_id": tid,
                "source_account_id": acc["account_id"],
                "destination_account_id": None,
                "customer_id": acc["customer_id"],
                "merchant_id": mch["merchant_id"] if mch else None,
                "device_id": dev["device_id"] if dev else None,
                "transaction_type": tt,
                "amount": amt,
                "currency": acc["currency"],
                "transaction_status": "COMPLETED",
                "transaction_timestamp": txn_dt.isoformat(),
                "channel": ch,
                "reference_id": f"REF-TXN-{txn_id_counter:08d}",
                "transfer_group_id": None,
                "balance_before": acc["current_balance"],
                "balance_after": acc["current_balance"],
                "created_at": txn_dt.isoformat()
            })
            txn_id_counter += 1

        return transactions, transfer_links, self.ground_truth_records
