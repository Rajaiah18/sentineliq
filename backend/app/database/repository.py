"""
SentinelIQ Repository Layer
Provides data access methods with pagination, filtering, sorting, safe upserts,
and seamless support for both MongoDB persistence and in-memory mock persistence for tests/offline.
"""
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pymongo.errors import PyMongoError
from backend.app.config import settings
from backend.app.database.mongodb import get_database, check_database_health


class Repository:
    def __init__(self):
        self.storage_mode = settings.APP_STORAGE.lower()
        # In-memory store for offline/memory mode or unit tests
        self._memory_store: Dict[str, Dict[str, Dict[str, Any]]] = {
            "customers": {},
            "accounts": {},
            "merchants": {},
            "devices": {},
            "transactions": {},
            "transfer_links": {},
            "risk_rules": {},
            "alerts": {},
            "cases": {},
            "analyst_actions": {},
            "audit_events": {},
            "users": {}
        }
        self._try_load_exports_into_memory()

    def _is_mongo_active(self) -> bool:
        if self.storage_mode == "memory":
            return False
        healthy, _, _ = check_database_health()
        return healthy

    def _try_load_exports_into_memory(self):
        """Pre-populate memory store from exports directory if available."""
        export_dir = settings.DATASET_EXPORT_DIR
        if not os.path.isdir(export_dir):
            return

        for entity in self._memory_store.keys():
            json_file = os.path.join(export_dir, f"{entity}.json")
            if os.path.isfile(json_file):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if entity == "transactions" and len(data) > 10000:
                        data = data[:10000]
                    id_key = {
                        "customers": "customer_id",
                        "accounts": "account_id",
                        "merchants": "merchant_id",
                        "devices": "device_id",
                        "transactions": "transaction_id",
                        "transfer_links": "transfer_link_id",
                        "risk_rules": "rule_id",
                        "alerts": "alert_id",
                        "cases": "case_id",
                        "analyst_actions": "action_id",
                        "audit_events": "event_id",
                        "users": "username"
                    }.get(entity, "id")
                    for row in data:
                        k = row.get(id_key)
                        if k:
                            self._memory_store[entity][str(k)] = row
                except Exception:
                    pass

    # =========================================================================
    # Customers
    # =========================================================================
    def get_customers(self, page: int = 1, page_size: int = 20, search: Optional[str] = None, risk_profile: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size

        if self._is_mongo_active():
            db = get_database()
            q: Dict[str, Any] = {}
            if risk_profile:
                q["risk_profile"] = risk_profile.upper()
            if search:
                q["$or"] = [
                    {"customer_id": {"$regex": search, "$options": "i"}},
                    {"first_name": {"$regex": search, "$options": "i"}},
                    {"last_name": {"$regex": search, "$options": "i"}}
                ]
            total = db.customers.count_documents(q)
            docs = list(db.customers.find(q, {"_id": 0}).skip(skip).limit(page_size))
            return docs, total
        else:
            items = list(self._memory_store["customers"].values())
            if risk_profile:
                items = [c for c in items if c.get("risk_profile") == risk_profile.upper()]
            if search:
                s = search.lower()
                items = [c for c in items if s in c.get("customer_id", "").lower() or s in c.get("first_name", "").lower() or s in c.get("last_name", "").lower()]
            total = len(items)
            return items[skip:skip + page_size], total

    def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        if self._is_mongo_active():
            db = get_database()
            return db.customers.find_one({"customer_id": customer_id}, {"_id": 0})
        return self._memory_store["customers"].get(customer_id)

    # =========================================================================
    # Accounts
    # =========================================================================
    def get_accounts(self, page: int = 1, page_size: int = 20, customer_id: Optional[str] = None, status: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size

        if self._is_mongo_active():
            db = get_database()
            q: Dict[str, Any] = {}
            if customer_id:
                q["customer_id"] = customer_id
            if status:
                q["account_status"] = status.upper()
            total = db.accounts.count_documents(q)
            docs = list(db.accounts.find(q, {"_id": 0}).skip(skip).limit(page_size))
            return docs, total
        else:
            items = list(self._memory_store["accounts"].values())
            if customer_id:
                items = [a for a in items if a.get("customer_id") == customer_id]
            if status:
                items = [a for a in items if a.get("account_status") == status.upper()]
            total = len(items)
            return items[skip:skip + page_size], total

    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        if self._is_mongo_active():
            db = get_database()
            return db.accounts.find_one({"account_id": account_id}, {"_id": 0})
        return self._memory_store["accounts"].get(account_id)

    # =========================================================================
    # Transactions
    # =========================================================================
    def get_transactions(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        customer_id: Optional[str] = None,
        account_id: Optional[str] = None,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "transaction_timestamp",
        sort_desc: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size
        direction = -1 if bool(sort_desc) else 1

        if self._is_mongo_active():
            db = get_database()
            q: Dict[str, Any] = {}
            if search:
                q["transaction_id"] = {"$regex": search, "$options": "i"}
            if customer_id:
                q["customer_id"] = customer_id
            if account_id:
                q["$or"] = [{"source_account_id": account_id}, {"destination_account_id": account_id}]
            if transaction_type:
                q["transaction_type"] = transaction_type.upper()
            if status:
                q["transaction_status"] = status.upper()

            total = db.transactions.count_documents(q)
            docs = list(db.transactions.find(q, {"_id": 0}).sort(sort_by, direction).skip(skip).limit(page_size))
            return docs, total
        else:
            items = list(self._memory_store["transactions"].values())
            if search:
                s = search.lower()
                items = [t for t in items if s in t.get("transaction_id", "").lower()]
            if customer_id:
                items = [t for t in items if t.get("customer_id") == customer_id]
            if account_id:
                items = [t for t in items if t.get("source_account_id") == account_id or t.get("destination_account_id") == account_id]
            if transaction_type:
                items = [t for t in items if t.get("transaction_type") == transaction_type.upper()]
            if status:
                items = [t for t in items if t.get("transaction_status") == status.upper()]

            def sort_key(t):
                v = t.get(sort_by)
                return v if v is not None else ""

            items.sort(key=sort_key, reverse=bool(sort_desc))
            total = len(items)
            return items[skip:skip + page_size], total

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        if self._is_mongo_active():
            db = get_database()
            return db.transactions.find_one({"transaction_id": transaction_id}, {"_id": 0})
        return self._memory_store["transactions"].get(transaction_id)

    # =========================================================================
    # Alerts
    # =========================================================================
    def get_alerts(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        customer_id: Optional[str] = None,
        sort_by: str = "risk_score",
        sort_desc: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size
        direction = -1 if bool(sort_desc) else 1

        if self._is_mongo_active():
            db = get_database()
            q: Dict[str, Any] = {}
            if status:
                q["alert_status"] = status.upper()
            if severity:
                q["severity"] = severity.upper()
            if customer_id:
                q["customer_id"] = customer_id
            total = db.alerts.count_documents(q)
            docs = list(db.alerts.find(q, {"_id": 0}).sort(sort_by, direction).skip(skip).limit(page_size))
            return docs, total
        else:
            items = list(self._memory_store["alerts"].values())
            if status:
                items = [a for a in items if a.get("alert_status") == status.upper()]
            if severity:
                items = [a for a in items if a.get("severity") == severity.upper()]
            if customer_id:
                items = [a for a in items if a.get("customer_id") == customer_id]

            def sort_key(a):
                v = a.get(sort_by)
                return float(v) if isinstance(v, (int, float)) else str(v)

            items.sort(key=sort_key, reverse=bool(sort_desc))
            total = len(items)
            return items[skip:skip + page_size], total

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        if self._is_mongo_active():
            db = get_database()
            return db.alerts.find_one({"alert_id": alert_id}, {"_id": 0})
        return self._memory_store["alerts"].get(alert_id)

    def update_alert_status(self, alert_id: str, new_status: str, actor_id: str = "SYSTEM") -> Optional[Dict[str, Any]]:
        now_iso = datetime.now(timezone.utc).isoformat()
        if self._is_mongo_active():
            db = get_database()
            doc = db.alerts.find_one({"alert_id": alert_id}, {"_id": 0})
            if not doc:
                return None
            prev_status = doc.get("alert_status")
            db.alerts.update_one(
                {"alert_id": alert_id},
                {"$set": {"alert_status": new_status, "updated_at": now_iso}}
            )
            # Record audit
            self.insert_audit_event(
                event_type="ALERT_STATUS_CHANGED",
                actor_id=actor_id,
                entity_type="ALERT",
                entity_id=alert_id,
                action_summary=f"Alert {alert_id} status updated from {prev_status} to {new_status}",
                previous_value={"status": prev_status},
                new_value={"status": new_status}
            )
            return db.alerts.find_one({"alert_id": alert_id}, {"_id": 0})
        else:
            alt = self._memory_store["alerts"].get(alert_id)
            if not alt:
                return None
            prev_status = alt.get("alert_status")
            alt["alert_status"] = new_status
            alt["updated_at"] = now_iso
            self.insert_audit_event(
                event_type="ALERT_STATUS_CHANGED",
                actor_id=actor_id,
                entity_type="ALERT",
                entity_id=alert_id,
                action_summary=f"Alert {alert_id} status updated from {prev_status} to {new_status}",
                previous_value={"status": prev_status},
                new_value={"status": new_status}
            )
            return alt

    # =========================================================================
    # Cases & Analyst Actions
    # =========================================================================
    def get_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_analyst_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size

        if self._is_mongo_active():
            db = get_database()
            q: Dict[str, Any] = {}
            if status:
                q["case_status"] = status.upper()
            if priority:
                q["priority"] = priority.upper()
            if assigned_analyst_id:
                q["assigned_analyst_id"] = assigned_analyst_id
            total = db.cases.count_documents(q)
            docs = list(db.cases.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size))
            return docs, total
        else:
            items = list(self._memory_store["cases"].values())
            if status:
                items = [c for c in items if c.get("case_status") == status.upper()]
            if priority:
                items = [c for c in items if c.get("priority") == priority.upper()]
            if assigned_analyst_id:
                items = [c for c in items if c.get("assigned_analyst_id") == assigned_analyst_id]
            items.sort(key=lambda c: c.get("created_at", ""), reverse=True)
            total = len(items)
            return items[skip:skip + page_size], total

    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        if self._is_mongo_active():
            db = get_database()
            return db.cases.find_one({"case_id": case_id}, {"_id": 0})
        return self._memory_store["cases"].get(case_id)

    def create_case(
        self,
        case_title: str,
        description: str,
        priority: str,
        alert_ids: List[str],
        customer_id: str,
        assigned_analyst_id: Optional[str] = None,
        actor_id: str = "SYSTEM"
    ) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        count = len(self._memory_store["cases"]) + 1
        case_id = f"CASE-2026-{count:06d}"

        case_doc = {
            "case_id": case_id,
            "case_title": case_title,
            "description": description,
            "case_status": "OPEN",
            "priority": priority,
            "alert_ids": alert_ids,
            "customer_id": customer_id,
            "assigned_analyst_id": assigned_analyst_id,
            "disposition": None,
            "disposition_reason": None,
            "created_at": now_iso,
            "updated_at": now_iso,
            "closed_at": None
        }

        if self._is_mongo_active():
            db = get_database()
            db.cases.insert_one(case_doc)
        self._memory_store["cases"][case_id] = case_doc

        # Record Audit Event
        self.insert_audit_event(
            event_type="CASE_CREATED",
            actor_id=actor_id,
            entity_type="CASE",
            entity_id=case_id,
            action_summary=f"Created investigation case {case_id}: '{case_title}'",
            previous_value=None,
            new_value=case_doc
        )
        return case_doc

    def add_analyst_action(
        self,
        case_id: str,
        analyst_id: str,
        action_type: str,
        comment: str,
        new_status: Optional[str] = None,
        disposition: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        case = self.get_case_by_id(case_id)
        if not case:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        act_count = len(self._memory_store["analyst_actions"]) + 1
        act_id = f"ACT-2026-{act_count:06d}"
        prev_status = case.get("case_status")

        action_doc = {
            "action_id": act_id,
            "case_id": case_id,
            "alert_id": case.get("alert_ids", [None])[0] if case.get("alert_ids") else None,
            "analyst_id": analyst_id,
            "action_type": action_type,
            "previous_status": prev_status,
            "new_status": new_status or prev_status,
            "disposition": disposition,
            "comment": comment,
            "timestamp": now_iso,
            "metadata": metadata or {}
        }

        # Update case state
        update_fields: Dict[str, Any] = {"updated_at": now_iso}
        if new_status:
            update_fields["case_status"] = new_status
        if disposition:
            update_fields["disposition"] = disposition
            update_fields["disposition_reason"] = comment
            if new_status == "CLOSED":
                update_fields["closed_at"] = now_iso

        if self._is_mongo_active():
            db = get_database()
            db.analyst_actions.insert_one(action_doc)
            db.cases.update_one({"case_id": case_id}, {"$set": update_fields})
        self._memory_store["analyst_actions"][act_id] = action_doc
        if case_id in self._memory_store["cases"]:
            self._memory_store["cases"][case_id].update(update_fields)

        # Audit Event
        self.insert_audit_event(
            event_type="ANALYST_ACTION_RECORDED",
            actor_id=analyst_id,
            entity_type="CASE",
            entity_id=case_id,
            action_summary=f"Analyst action {action_type} recorded on case {case_id}: {comment[:60]}",
            previous_value={"status": prev_status},
            new_value={"status": new_status or prev_status, "disposition": disposition}
        )
        return action_doc

    def get_actions_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        if self._is_mongo_active():
            db = get_database()
            return list(db.analyst_actions.find({"case_id": case_id}, {"_id": 0}).sort("timestamp", 1))
        acts = [a for a in self._memory_store["analyst_actions"].values() if a.get("case_id") == case_id]
        acts.sort(key=lambda a: a.get("timestamp", ""))
        return acts

    # =========================================================================
    # Rules
    # =========================================================================
    def get_rules(self) -> List[Dict[str, Any]]:
        if self._is_mongo_active():
            db = get_database()
            docs = list(db.risk_rules.find({}, {"_id": 0}))
            if docs:
                return docs
        return list(self._memory_store["risk_rules"].values())

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        if self._is_mongo_active():
            db = get_database()
            return db.risk_rules.find_one({"rule_id": rule_id}, {"_id": 0})
        return self._memory_store["risk_rules"].get(rule_id)

    def update_rule(self, rule_id: str, updates: Dict[str, Any], actor_id: str = "ADMIN") -> Optional[Dict[str, Any]]:
        now_iso = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now_iso
        if self._is_mongo_active():
            db = get_database()
            db.risk_rules.update_one({"rule_id": rule_id}, {"$set": updates})
            res = db.risk_rules.find_one({"rule_id": rule_id}, {"_id": 0})
        else:
            rule = self._memory_store["risk_rules"].get(rule_id)
            if not rule:
                return None
            rule.update(updates)
            res = rule

        self.insert_audit_event(
            event_type="RULE_MODIFIED",
            actor_id=actor_id,
            entity_type="RISK_RULE",
            entity_id=rule_id,
            action_summary=f"Risk rule {rule_id} updated",
            previous_value=None,
            new_value=updates
        )
        return res

    # =========================================================================
    # Audit Events
    # =========================================================================
    def insert_audit_event(
        self,
        event_type: str,
        actor_id: str,
        entity_type: str,
        entity_id: str,
        action_summary: str,
        previous_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        count = len(self._memory_store["audit_events"]) + 1
        now_iso = datetime.now(timezone.utc).isoformat()
        evt = {
            "event_id": f"AUD-2026-{count:08d}",
            "event_type": event_type,
            "actor_id": actor_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timestamp": now_iso,
            "action_summary": action_summary,
            "previous_value": previous_value,
            "new_value": new_value,
            "correlation_id": correlation_id
        }
        if self._is_mongo_active():
            try:
                db = get_database()
                db.audit_events.insert_one(evt)
            except Exception:
                pass
        self._memory_store["audit_events"][evt["event_id"]] = evt
        return evt

    def get_audit_events(self, page: int = 1, page_size: int = 25, entity_type: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size

        if self._is_mongo_active():
            db = get_database()
            q = {"entity_type": entity_type.upper()} if entity_type else {}
            total = db.audit_events.count_documents(q)
            docs = list(db.audit_events.find(q, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(page_size))
            return docs, total
        else:
            items = list(self._memory_store["audit_events"].values())
            if entity_type:
                items = [e for e in items if e.get("entity_type") == entity_type.upper()]
            items.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
            total = len(items)
            return items[skip:skip + page_size], total

    # =========================================================================
    # Dashboard Overview Metrics
    # =========================================================================
    def get_overview_metrics(self) -> Dict[str, Any]:
        """Real database-backed counts and distributions."""
        if self._is_mongo_active():
            db = get_database()
            tot_cust = db.customers.count_documents({})
            tot_acc = db.accounts.count_documents({})
            tot_txn = db.transactions.count_documents({})
            tot_alt = db.alerts.count_documents({})
            open_cases = db.cases.count_documents({"case_status": "OPEN"})
            crit_alerts = db.alerts.count_documents({"severity": "CRITICAL"})

            # Aggregations
            sev_agg = list(db.alerts.aggregate([{"$group": {"_id": "$severity", "count": {"$sum": 1}}}]))
            sev_dist = {r["_id"]: r["count"] for r in sev_agg if r["_id"]}

            status_agg = list(db.alerts.aggregate([{"$group": {"_id": "$alert_status", "count": {"$sum": 1}}}]))
            status_dist = {r["_id"]: r["count"] for r in status_agg if r["_id"]}

            case_agg = list(db.cases.aggregate([{"$group": {"_id": "$case_status", "count": {"$sum": 1}}}]))
            case_dist = {r["_id"]: r["count"] for r in case_agg if r["_id"]}

            recent_alerts = list(db.alerts.find({}, {"_id": 0}).sort("created_at", -1).limit(5))
            recent_actions = list(db.analyst_actions.find({}, {"_id": 0}).sort("timestamp", -1).limit(5))
        else:
            tot_cust = len(self._memory_store["customers"])
            tot_acc = len(self._memory_store["accounts"])
            tot_txn = len(self._memory_store["transactions"])
            tot_alt = len(self._memory_store["alerts"])
            open_cases = len([c for c in self._memory_store["cases"].values() if c.get("case_status") == "OPEN"])
            crit_alerts = len([a for a in self._memory_store["alerts"].values() if a.get("severity") == "CRITICAL"])

            sev_dist: Dict[str, int] = {}
            for a in self._memory_store["alerts"].values():
                s = a.get("severity", "LOW")
                sev_dist[s] = sev_dist.get(s, 0) + 1

            status_dist: Dict[str, int] = {}
            for a in self._memory_store["alerts"].values():
                st = a.get("alert_status", "NEW")
                status_dist[st] = status_dist.get(st, 0) + 1

            case_dist: Dict[str, int] = {}
            for c in self._memory_store["cases"].values():
                st = c.get("case_status", "OPEN")
                case_dist[st] = case_dist.get(st, 0) + 1

            recent_alerts = sorted(list(self._memory_store["alerts"].values()), key=lambda a: a.get("created_at", ""), reverse=True)[:5]
            recent_actions = sorted(list(self._memory_store["analyst_actions"].values()), key=lambda a: a.get("timestamp", ""), reverse=True)[:5]

        return {
            "total_customers": tot_cust,
            "total_accounts": tot_acc,
            "total_transactions": tot_txn,
            "total_alerts": tot_alt,
            "open_cases": open_cases,
            "critical_alerts": crit_alerts,
            "alerts_by_severity": sev_dist,
            "alerts_by_status": status_dist,
            "cases_by_status": case_dist,
            "recent_alerts": recent_alerts,
            "recent_actions": recent_actions,
            "storage_mode": "mongodb" if self._is_mongo_active() else "memory"
        }


# Global Singleton Repository
repo = Repository()
