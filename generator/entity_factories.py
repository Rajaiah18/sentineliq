"""
SentinelIQ Synthetic Entity Factories
Generates realistic, deterministic financial entities:
Customers, Accounts, Merchants, Devices, and baseline Transactions.
"""
import random
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple


FIRST_NAMES = [
    "Alexander", "Beatrix", "Charles", "Diana", "Edward", "Fiona", "George", "Helena",
    "Ian", "Julia", "Kenneth", "Louisa", "Marcus", "Nadia", "Oliver", "Penelope",
    "Quentin", "Rachel", "Sebastian", "Theresa", "Ulysses", "Valerie", "William", "Xanthe",
    "Yusuf", "Zara", "Aiden", "Brianna", "Caleb", "Danielle", "Ethan", "Gabriella"
]

LAST_NAMES = [
    "Sterling", "Vanguard", "Kensington", "Blackwood", "Montague", "Fairchild", "Hastings", "Sinclair",
    "Waverly", "Pembroke", "Cavendish", "Rothschild", "Ellington", "Ashford", "Kingsley", "Prescott",
    "Somerset", "Langley", "Thornton", "Harrington", "Whitmore", "Radcliffe", "Stirling", "Montgomery",
    "Chambers", "Fitzgerald", "Huntington", "Mercer", "Callahan", "Donovan", "Greystone", "Vanderbilt"
]

COUNTRY_CODES = ["US", "GB", "DE", "FR", "SG", "CH", "JP", "CA", "AU", "NL"]
CURRENCIES = ["USD", "EUR", "GBP", "CAD"]

MERCHANT_CATEGORIES = [
    ("RETAIL", "LOW"),
    ("DINING", "LOW"),
    ("SERVICES", "LOW"),
    ("ELECTRONICS", "MEDIUM"),
    ("TRAVEL", "MEDIUM"),
    ("GAMBLING", "HIGH"),
    ("CRYPTO", "HIGH")
]

DEVICE_TYPES = ["MOBILE", "DESKTOP", "TABLET"]
OPERATING_SYSTEMS = ["IOS", "ANDROID", "WINDOWS", "MACOS", "LINUX"]
CHANNELS = ["MOBILE_APP", "WEB_PORTAL", "ATM", "POS", "BRANCH"]
TRANSACTION_TYPES = ["CARD_PAYMENT", "PURCHASE", "CASH_WITHDRAWAL", "DEPOSIT", "ACCOUNT_TRANSFER", "BANK_TRANSFER", "REFUND"]


class EntityFactory:
    def __init__(self, seed: int = 20261022):
        self.seed = seed
        self.rng = random.Random(seed)
        self.base_date = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def generate_customers(self, count: int) -> List[Dict[str, Any]]:
        """Generate deterministic Customer records."""
        customers = []
        for i in range(1, count + 1):
            cust_id = f"CUS-{i:06d}"
            fn = self.rng.choice(FIRST_NAMES)
            ln = self.rng.choice(LAST_NAMES)

            # Age 21 to 75
            birth_year = 2026 - self.rng.randint(21, 75)
            birth_month = self.rng.randint(1, 12)
            birth_day = self.rng.randint(1, 28)
            dob = f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}"

            cust_type = "BUSINESS" if self.rng.random() < 0.15 else "INDIVIDUAL"
            risk_roll = self.rng.random()
            if risk_roll < 0.70:
                risk_prof = "LOW"
            elif risk_roll < 0.92:
                risk_prof = "MEDIUM"
            else:
                risk_prof = "HIGH"

            country = self.rng.choice(COUNTRY_CODES)
            status = "ACTIVE"
            if self.rng.random() < 0.03:
                status = "SUSPENDED"

            created_offset = self.rng.randint(0, 180)
            created_dt = self.base_date + timedelta(days=created_offset, hours=self.rng.randint(0, 23))
            created_iso = created_dt.isoformat()

            customers.append({
                "customer_id": cust_id,
                "first_name": fn,
                "last_name": ln,
                "date_of_birth": dob,
                "customer_type": cust_type,
                "risk_profile": risk_prof,
                "country_code": country,
                "customer_status": status,
                "created_at": created_iso,
                "updated_at": created_iso
            })
        return customers

    def generate_accounts(self, customers: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
        """
        Generate target_count Accounts linked to existing customers.
        Every customer gets at least one primary checking account;
        remaining accounts distributed to customers.
        """
        accounts = []
        acc_counter = 1

        # Phase 1: 1 primary checking account per customer
        for cust in customers:
            if acc_counter > target_count:
                break
            cust_id = cust["customer_id"]
            acc_id = f"ACC-{cust_id}-01"
            open_bal = round(self.rng.uniform(1000.0, 50000.0), 2)
            overdraft = 5000.0 if cust["customer_type"] == "BUSINESS" else (1000.0 if cust["risk_profile"] == "LOW" else 0.0)

            opened_iso = cust["created_at"]
            currency = "USD" if cust["country_code"] in ("US", "SG") else ("EUR" if cust["country_code"] in ("DE", "FR", "NL") else "GBP")

            accounts.append({
                "account_id": acc_id,
                "customer_id": cust_id,
                "account_type": "CHECKING" if cust["customer_type"] == "INDIVIDUAL" else "BUSINESS",
                "currency": currency,
                "opening_balance": open_bal,
                "current_balance": open_bal,
                "overdraft_limit": overdraft,
                "account_status": "OPEN",
                "opened_at": opened_iso,
                "closed_at": None,
                "created_at": opened_iso,
                "updated_at": opened_iso
            })
            acc_counter += 1

        # Phase 2: Distribute remaining accounts (savings, investment, second checking)
        cust_idx = 0
        sub_counter = 2
        while acc_counter <= target_count:
            cust = customers[cust_idx % len(customers)]
            cust_id = cust["customer_id"]
            acc_id = f"ACC-{cust_id}-{sub_counter:02d}"

            acc_type = self.rng.choice(["SAVINGS", "INVESTMENT", "CHECKING"])
            open_bal = round(self.rng.uniform(500.0, 100000.0), 2)
            overdraft = 0.0

            opened_iso = cust["created_at"]
            currency = accounts[cust_idx % len(accounts)]["currency"]

            accounts.append({
                "account_id": acc_id,
                "customer_id": cust_id,
                "account_type": acc_type,
                "currency": currency,
                "opening_balance": open_bal,
                "current_balance": open_bal,
                "overdraft_limit": overdraft,
                "account_status": "OPEN",
                "opened_at": opened_iso,
                "closed_at": None,
                "created_at": opened_iso,
                "updated_at": opened_iso
            })
            acc_counter += 1
            cust_idx += 1
            if cust_idx % len(customers) == 0:
                sub_counter += 1

        return accounts

    def generate_merchants(self, count: int) -> List[Dict[str, Any]]:
        """Generate diverse synthetic Merchant records."""
        merchants = []
        categories_cycle = [
            ("Apex Global Retail", "RETAIL", "LOW"),
            ("AeroVoyage International", "TRAVEL", "MEDIUM"),
            ("Quantum Electro Hub", "ELECTRONICS", "MEDIUM"),
            ("Crown Casino Resort", "GAMBLING", "HIGH"),
            ("BlockLedger Exchange", "CRYPTO", "HIGH"),
            ("Grand Bistro Dining", "DINING", "LOW"),
            ("CloudMatrix SaaS Services", "SERVICES", "LOW"),
            ("Oasis Luxury Resorts", "TRAVEL", "MEDIUM"),
            ("Fortune Spin Wagering", "GAMBLING", "HIGH"),
            ("PrimeBit Liquidity", "CRYPTO", "HIGH"),
        ]

        for i in range(1, count + 1):
            m_id = f"MER-{i:05d}"
            base_name, cat, risk = categories_cycle[(i - 1) % len(categories_cycle)]
            name = f"{base_name} #{i:03d}"
            country = self.rng.choice(COUNTRY_CODES)
            created_dt = self.base_date + timedelta(days=self.rng.randint(0, 30))

            merchants.append({
                "merchant_id": m_id,
                "merchant_name": name,
                "merchant_category": cat,
                "merchant_country": country,
                "merchant_risk_level": risk,
                "created_at": created_dt.isoformat()
            })
        return merchants

    def generate_devices(self, count: int) -> List[Dict[str, Any]]:
        """Generate safe synthetic Device records with deterministic fingerprints."""
        devices = []
        for i in range(1, count + 1):
            dev_id = f"DEV-{i:06d}"
            dev_type = self.rng.choice(DEVICE_TYPES)
            os_name = self.rng.choice(OPERATING_SYSTEMS)
            country = self.rng.choice(COUNTRY_CODES)
            raw_fingerprint = f"device-seed-{self.seed}-{dev_id}-{dev_type}-{os_name}"
            fp_hash = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()

            status = "TRUSTED"
            if self.rng.random() < 0.06:
                status = "FLAGGED" if self.rng.random() < 0.3 else "UNTRUSTED"

            first_seen = self.base_date + timedelta(days=self.rng.randint(0, 60))

            devices.append({
                "device_id": dev_id,
                "device_fingerprint": fp_hash,
                "device_type": dev_type,
                "operating_system": os_name,
                "ip_country": country,
                "first_seen_at": first_seen.isoformat(),
                "device_status": status
            })
        return devices
