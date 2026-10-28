"""
SentinelIQ MongoDB Indexes Definition
Creates explicit unique and compound indexes for optimal querying and referential performance.
"""
from typing import Dict, Any, List
import pymongo
from pymongo.database import Database


def create_all_indexes(db: Database) -> Dict[str, List[str]]:
    """
    Ensure all unique constraints and compound query indexes exist in MongoDB.
    """
    index_results = {}

    # Customers
    db.customers.create_index([("customer_id", pymongo.ASCENDING)], unique=True, name="idx_cust_id_unique")
    db.customers.create_index([("risk_profile", pymongo.ASCENDING)], name="idx_cust_risk")
    index_results["customers"] = ["idx_cust_id_unique", "idx_cust_risk"]

    # Accounts
    db.accounts.create_index([("account_id", pymongo.ASCENDING)], unique=True, name="idx_acc_id_unique")
    db.accounts.create_index([("customer_id", pymongo.ASCENDING)], name="idx_acc_customer_id")
    db.accounts.create_index([("account_status", pymongo.ASCENDING)], name="idx_acc_status")
    index_results["accounts"] = ["idx_acc_id_unique", "idx_acc_customer_id", "idx_acc_status"]

    # Merchants
    db.merchants.create_index([("merchant_id", pymongo.ASCENDING)], unique=True, name="idx_merch_id_unique")
    db.merchants.create_index([("merchant_category", pymongo.ASCENDING)], name="idx_merch_category")
    index_results["merchants"] = ["idx_merch_id_unique", "idx_merch_category"]

    # Devices
    db.devices.create_index([("device_id", pymongo.ASCENDING)], unique=True, name="idx_dev_id_unique")
    db.devices.create_index([("device_fingerprint", pymongo.ASCENDING)], name="idx_dev_fingerprint")
    index_results["devices"] = ["idx_dev_id_unique", "idx_dev_fingerprint"]

    # Transactions
    db.transactions.create_index([("transaction_id", pymongo.ASCENDING)], unique=True, name="idx_txn_id_unique")
    db.transactions.create_index([("customer_id", pymongo.ASCENDING)], name="idx_txn_cust_id")
    db.transactions.create_index([("source_account_id", pymongo.ASCENDING)], name="idx_txn_src_acc")
    db.transactions.create_index([("transaction_timestamp", pymongo.DESCENDING)], name="idx_txn_timestamp_desc")
    db.transactions.create_index([("transfer_group_id", pymongo.ASCENDING)], sparse=True, name="idx_txn_transfer_grp")
    db.transactions.create_index([
        ("source_account_id", pymongo.ASCENDING),
        ("transaction_timestamp", pymongo.DESCENDING)
    ], name="idx_txn_acc_time_compound")
    index_results["transactions"] = [
        "idx_txn_id_unique", "idx_txn_cust_id", "idx_txn_src_acc",
        "idx_txn_timestamp_desc", "idx_txn_transfer_grp", "idx_txn_acc_time_compound"
    ]

    # Transfer Links
    db.transfer_links.create_index([("transfer_link_id", pymongo.ASCENDING)], unique=True, name="idx_trl_id_unique")
    db.transfer_links.create_index([("transfer_group_id", pymongo.ASCENDING)], name="idx_trl_grp_id")
    index_results["transfer_links"] = ["idx_trl_id_unique", "idx_trl_grp_id"]

    # Risk Rules
    db.risk_rules.create_index([("rule_id", pymongo.ASCENDING)], unique=True, name="idx_rule_id_unique")
    db.risk_rules.create_index([("enabled", pymongo.ASCENDING)], name="idx_rule_enabled")
    index_results["risk_rules"] = ["idx_rule_id_unique", "idx_rule_enabled"]

    # Alerts
    db.alerts.create_index([("alert_id", pymongo.ASCENDING)], unique=True, name="idx_alert_id_unique")
    db.alerts.create_index([("alert_status", pymongo.ASCENDING)], name="idx_alert_status")
    db.alerts.create_index([("severity", pymongo.ASCENDING)], name="idx_alert_severity")
    db.alerts.create_index([("risk_score", pymongo.DESCENDING)], name="idx_alert_score_desc")
    db.alerts.create_index([("customer_id", pymongo.ASCENDING)], name="idx_alert_cust_id")
    index_results["alerts"] = ["idx_alert_id_unique", "idx_alert_status", "idx_alert_severity", "idx_alert_score_desc", "idx_alert_cust_id"]

    # Cases
    db.cases.create_index([("case_id", pymongo.ASCENDING)], unique=True, name="idx_case_id_unique")
    db.cases.create_index([("case_status", pymongo.ASCENDING)], name="idx_case_status")
    db.cases.create_index([("assigned_analyst_id", pymongo.ASCENDING)], name="idx_case_analyst")
    index_results["cases"] = ["idx_case_id_unique", "idx_case_status", "idx_case_analyst"]

    # Analyst Actions
    db.analyst_actions.create_index([("action_id", pymongo.ASCENDING)], unique=True, name="idx_act_id_unique")
    db.analyst_actions.create_index([("case_id", pymongo.ASCENDING)], name="idx_act_case_id")
    db.analyst_actions.create_index([("timestamp", pymongo.DESCENDING)], name="idx_act_time_desc")
    index_results["analyst_actions"] = ["idx_act_id_unique", "idx_act_case_id", "idx_act_time_desc"]

    # Audit Events
    db.audit_events.create_index([("event_id", pymongo.ASCENDING)], unique=True, name="idx_audit_id_unique")
    db.audit_events.create_index([("timestamp", pymongo.DESCENDING)], name="idx_audit_time_desc")
    db.audit_events.create_index([("entity_id", pymongo.ASCENDING)], name="idx_audit_entity_id")
    index_results["audit_events"] = ["idx_audit_id_unique", "idx_audit_time_desc", "idx_audit_entity_id"]

    # Users
    db.users.create_index([("username", pymongo.ASCENDING)], unique=True, name="idx_user_username_unique")
    db.users.create_index([("email", pymongo.ASCENDING)], unique=True, name="idx_user_email_unique")
    index_results["users"] = ["idx_user_username_unique", "idx_user_email_unique"]

    return index_results
