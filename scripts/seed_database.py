"""
SentinelIQ MongoDB Atlas Database Seeder
Idempotently loads generated synthetic export records into live MongoDB collections.
Creates unique and compound indexes without dropping database.
"""
import os
import json
import argparse
from datetime import datetime
from backend.app.config import settings
from backend.app.database.mongodb import get_mongo_client, get_database, check_database_health
from backend.app.database.indexes import create_all_indexes


COLLECTIONS = [
    ("customers", "customer_id"),
    ("accounts", "account_id"),
    ("merchants", "merchant_id"),
    ("devices", "device_id"),
    ("transactions", "transaction_id"),
    ("transfer_links", "transfer_link_id"),
    ("risk_rules", "rule_id"),
    ("alerts", "alert_id"),
    ("cases", "case_id"),
    ("analyst_actions", "action_id"),
    ("audit_events", "event_id")
]


def seed_database(export_dir: str = "./exports"):
    print("=" * 70)
    print("SentinelIQ — MongoDB Database Seeder")
    print("=" * 70)

    healthy, msg, details = check_database_health()
    if not healthy:
        print(f"[!] Cannot seed database: {msg}")
        print(f"    Advice: {details.get('actionable_advice')}")
        return False

    db = get_database()
    print(f"[*] Connected to database: {db.name}")

    print("[*] Creating explicit MongoDB indexes...")
    index_map = create_all_indexes(db)
    for col_name, idxs in index_map.items():
        print(f"    - {col_name}: {len(idxs)} indexes verified.")

    total_upserted = 0
    for col_name, id_field in COLLECTIONS:
        json_path = os.path.join(export_dir, f"{col_name}.json")
        if not os.path.isfile(json_path):
            print(f"[-] Skipping {col_name}: {json_path} not found.")
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        if not records:
            continue

        print(f"[*] Ingesting {len(records):,} records into '{col_name}'...")
        col = db[col_name]
        
        # Batch upsert via pymongo replace_one with upsert=True
        operations = []
        for r in records:
            doc_id = r.get(id_field)
            if doc_id:
                col.update_one({id_field: doc_id}, {"$set": r}, upsert=True)
                total_upserted += 1

        print(f"    [OK] Ingested '{col_name}'. Collection count: {col.count_documents({}):,}")

    print("=" * 70)
    print(f"[SUCCESS] MongoDB Seeding Completed! {total_upserted:,} records processed.")
    print("=" * 70)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelIQ MongoDB Seeder")
    parser.add_argument("--export-dir", type=str, default="./exports")
    args = parser.parse_args()
    seed_database(args.export_dir)
