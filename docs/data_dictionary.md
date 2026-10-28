# SentinelIQ — Data Dictionary & Entity Reference
**Intelligent Transaction Risk & Investigation Platform**  
*Tagline: Explainable Risk. Traceable Decisions.*

---

## 1. Domain Entities & Schemas

### 1.1 Customer (`customers`)
| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `customer_id` | String (PK) | Yes | Unique synthetic identifier | `CUS-000001` |
| `first_name` | String | Yes | Synthetic given name | `Alexander` |
| `last_name` | String | Yes | Synthetic family name | `Sterling` |
| `date_of_birth` | String (Date) | Yes | YYYY-MM-DD birthdate | `1985-04-12` |
| `customer_type` | Enum | Yes | `INDIVIDUAL` or `BUSINESS` | `INDIVIDUAL` |
| `risk_profile` | Enum | Yes | `LOW`, `MEDIUM`, `HIGH` | `LOW` |
| `country_code` | String (2) | Yes | ISO 3166-1 alpha-2 code | `US` |
| `customer_status` | Enum | Yes | `ACTIVE`, `SUSPENDED`, `CLOSED` | `ACTIVE` |
| `created_at` | String (ISO) | Yes | UTC Onboarding timestamp | `2026-01-15T10:00:00Z` |
| `updated_at` | String (ISO) | Yes | UTC Last updated timestamp | `2026-01-15T10:00:00Z` |

---

### 1.2 Account (`accounts`)
| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `account_id` | String (PK) | Yes | Unique account identifier | `ACC-CUS-000001-01` |
| `customer_id` | String (FK) | Yes | References `Customer.customer_id` | `CUS-000001` |
| `account_type` | Enum | Yes | `CHECKING`, `SAVINGS`, `BUSINESS`, `INVESTMENT` | `CHECKING` |
| `currency` | String (3) | Yes | ISO 4217 Currency Code | `USD` |
| `opening_balance` | Float | Yes | Initial deposit balance | `12500.00` |
| `current_balance` | Float | Yes | Current ledger balance | `9840.50` |
| `overdraft_limit` | Float | Yes | Authorized overdraft threshold | `1000.00` |
| `account_status` | Enum | Yes | `OPEN`, `RESTRICTED`, `CLOSED` | `OPEN` |
| `opened_at` | String (ISO) | Yes | Account opening timestamp | `2026-01-15T10:00:00Z` |
| `closed_at` | String (ISO) | No | Closure timestamp (required if CLOSED) | `2026-02-20T14:30:00Z` |
| `created_at` | String (ISO) | Yes | Record creation timestamp | `2026-01-15T10:00:00Z` |
| `updated_at` | String (ISO) | Yes | Record update timestamp | `2026-01-15T10:00:00Z` |

---

### 1.3 Merchant (`merchants`)
| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `merchant_id` | String (PK) | Yes | Unique merchant identifier | `MER-00001` |
| `merchant_name` | String | Yes | Synthetic merchant trading name | `Crown Casino Resort #001` |
| `merchant_category` | Enum | Yes | `RETAIL`, `TRAVEL`, `GAMBLING`, `CRYPTO`, `ELECTRONICS`, `DINING`, `SERVICES` | `GAMBLING` |
| `merchant_country` | String (2) | Yes | ISO country code | `US` |
| `merchant_risk_level` | Enum | Yes | `LOW`, `MEDIUM`, `HIGH` | `HIGH` |
| `created_at` | String (ISO) | Yes | Merchant registration timestamp | `2026-01-01T00:00:00Z` |

---

### 1.4 Device (`devices`)
| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `device_id` | String (PK) | Yes | Unique device identifier | `DEV-000001` |
| `device_fingerprint` | String (64) | Yes | SHA-256 deterministic hardware fingerprint | `4c265fec...` |
| `device_type` | Enum | Yes | `MOBILE`, `DESKTOP`, `TABLET` | `MOBILE` |
| `operating_system` | Enum | Yes | `IOS`, `ANDROID`, `WINDOWS`, `MACOS`, `LINUX` | `IOS` |
| `ip_country` | String (2) | Yes | Country code of gateway IP | `US` |
| `first_seen_at` | String (ISO) | Yes | First telemetry registration | `2026-01-10T08:00:00Z` |
| `device_status` | Enum | Yes | `TRUSTED`, `UNTRUSTED`, `FLAGGED` | `TRUSTED` |

---

### 1.5 Transaction (`transactions`)
| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `transaction_id` | String (PK) | Yes | Unique ledger transaction ID | `TXN-2026-00000001` |
| `source_account_id` | String (FK) | Yes | Originating debit account | `ACC-CUS-000001-01` |
| `destination_account_id` | String (FK) | No | Destination account (transfers only) | `ACC-CUS-000002-01` |
| `customer_id` | String (FK) | Yes | Initiating customer ID | `CUS-000001` |
| `merchant_id` | String (FK) | No | Counterparty merchant ID | `MER-00001` |
| `device_id` | String (FK) | No | Executing device ID | `DEV-000001` |
| `transaction_type` | Enum | Yes | `CARD_PAYMENT`, `PURCHASE`, `CASH_WITHDRAWAL`, `DEPOSIT`, `ACCOUNT_TRANSFER`, `BANK_TRANSFER`, `REFUND` | `CARD_PAYMENT` |
| `amount` | Float | Yes | Positive decimal amount (> 0.0) | `1450.75` |
| `currency` | String (3) | Yes | Currency code | `USD` |
| `transaction_status` | Enum | Yes | `COMPLETED`, `PENDING`, `FAILED`, `REVERSED` | `COMPLETED` |
| `transaction_timestamp` | String (ISO) | Yes | UTC posting timestamp | `2026-02-18T14:22:10Z` |
| `channel` | Enum | Yes | `MOBILE_APP`, `WEB_PORTAL`, `ATM`, `POS`, `BRANCH` | `POS` |
| `reference_id` | String | Yes | Payment gateway external reference | `REF-2026-000001` |
| `transfer_group_id` | String | No | Reciprocal transfer link ID | `GRP-2026-00000001` |
| `balance_before` | Float | No | Ledger balance prior to settlement | `5200.00` |
| `balance_after` | Float | No | Ledger balance after settlement | `3749.25` |
| `created_at` | String (ISO) | Yes | Ingestion timestamp | `2026-02-18T14:22:10Z` |

---

### 1.6 Alert (`alerts`)
| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `alert_id` | String (PK) | Yes | Unique alert identifier | `ALT-2026-000001` |
| `alert_type` | Enum | Yes | `SUSPICIOUS_ACTIVITY` or `DATA_INTEGRITY` | `SUSPICIOUS_ACTIVITY` |
| `title` | String | Yes | Human-readable alert headline | `High Value Transaction Alert` |
| `description` | String | Yes | Primary rule rationale | `Single transaction amount exceeded threshold.` |
| `severity` | Enum | Yes | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | `HIGH` |
| `risk_score` | Float | Yes | Numeric risk score (0.0 to 100.0) | `75.5` |
| `alert_status` | Enum | Yes | `NEW`, `UNDER_REVIEW`, `ESCALATED`, `CLOSED` | `NEW` |
| `triggered_transaction_ids` | List[String] | Yes | Triggering transaction references | `["TXN-2026-00000042"]` |
| `customer_id` | String (FK) | Yes | Affected customer ID | `CUS-000042` |
| `account_ids` | List[String] | Yes | Associated account IDs | `["ACC-CUS-000042-01"]` |
| `triggered_rule_ids` | List[String] | Yes | Breached risk rule IDs | `["RULE-HIGH-VALUE"]` |
| `reason_codes` | List[String] | Yes | Standard reason codes | `["THRESHOLD_HIGH_VALUE_EXCEEDED"]` |
| `explanation` | String | Yes | Synthesized decision narrative | Full paragraph explanation |
| `evidence` | Dict | Yes | Structured runtime metrics snapshot | JSON evidence object |
| `created_at` | String (ISO) | Yes | Alert generation timestamp | `2026-02-18T14:22:10Z` |
| `updated_at` | String (ISO) | Yes | Last status change timestamp | `2026-02-18T14:22:10Z` |

---

### 1.7 Case (`cases`)
| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `case_id` | String (PK) | Yes | Unique case dossier ID | `CASE-2026-000001` |
| `case_title` | String | Yes | Case dossier headline | `Investigation: High Value Alert ALT-2026-000001` |
| `description` | String | Yes | Initial investigation summary | Narrative summary |
| `case_status` | Enum | Yes | `OPEN`, `IN_PROGRESS`, `PENDING_REVIEW`, `CLOSED` | `IN_PROGRESS` |
| `priority` | Enum | Yes | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | `HIGH` |
| `alert_ids` | List[String] | Yes | Attached alert references | `["ALT-2026-000001"]` |
| `customer_id` | String (FK) | Yes | Subject customer ID | `CUS-000042` |
| `assigned_analyst_id` | String | No | Assigned user ID | `USR-ANALYST-01` |
| `disposition` | Enum | No | `CONFIRMED_SUSPICIOUS`, `FALSE_POSITIVE`, `INCONCLUSIVE`, `ESCALATED` | `CONFIRMED_SUSPICIOUS` |
| `disposition_reason` | String | No | Compliance rationale | Detailed finding |
| `created_at` | String (ISO) | Yes | Case opening timestamp | `2026-02-18T16:00:00Z` |
| `updated_at` | String (ISO) | Yes | Last activity timestamp | `2026-02-20T10:00:00Z` |
| `closed_at` | String (ISO) | No | Closure timestamp (required if CLOSED) | `2026-02-20T10:00:00Z` |
