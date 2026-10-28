# SentinelIQ — REST API Reference & Specification
**Intelligent Transaction Risk & Investigation Platform**  
*Tagline: Explainable Risk. Traceable Decisions.*

---

## 1. Base URL & OpenAPI

- **Version:** v1
- **Base Path:** `/api/v1`
- **Interactive OpenAPI Documentation:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 2. Authentication & Headers

Protected routes require an Authorization Bearer token:
```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```
Or a valid HTTP-only `access_token` session cookie.

---

## 3. Endpoints Overview

### 3.1 Health & System
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/health` | Service liveness, product version, environment | None |
| `GET` | `/health/ready` | Database ping check (honestly reports MongoDB status) | None |

### 3.2 Authentication
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate with username/password, issue JWT | None |
| `POST` | `/api/v1/auth/logout` | Revoke session cookie | None |
| `GET` | `/api/v1/auth/me` | Current authenticated user profile | Yes |

### 3.3 Metrics & Observability
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/metrics/overview` | Real database counts for customers, txns, alerts | None |
| `GET` | `/api/v1/metrics/alerts` | Alert distributions across severity & status | None |
| `GET` | `/api/v1/metrics/cases` | Case distributions across lifecycle states | None |
| `GET` | `/api/v1/metrics/data-quality` | Latest 24-check validation summary | None |
| `GET` | `/api/v1/metrics/evaluation/summary` | Detection quality metrics against ground truth | None |

### 3.4 Customers & Accounts
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/customers` | Paginated customer list with risk filtering | None |
| `GET` | `/api/v1/customers/{id}` | Customer detail with linked accounts | None |
| `GET` | `/api/v1/customers/{id}/transactions` | Ledger transactions for specific customer | None |
| `GET` | `/api/v1/customers/{id}/alerts` | Alerts generated for specific customer | None |
| `GET` | `/api/v1/accounts` | Paginated accounts inventory | None |
| `GET` | `/api/v1/accounts/{id}` | Account detail and balance info | None |
| `GET` | `/api/v1/accounts/{id}/transactions` | Account ledger posting history | None |

### 3.5 Transactions
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/transactions` | Paginated transactions with search & type filters | None |
| `GET` | `/api/v1/transactions/{id}` | Transaction detail with linked party profiles | None |
| `GET` | `/api/v1/transactions/{id}/related` | Transfer group reciprocal counterpart legs | None |
| `GET` | `/api/v1/transactions/{id}/alerts` | Alerts triggered by this transaction | None |

### 3.6 Alerts
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/alerts` | Filter alerts by severity and status | None |
| `GET` | `/api/v1/alerts/{id}` | Alert detail with triggering transactions | None |
| `GET` | `/api/v1/alerts/{id}/evidence` | Audit-proof evidence payload & reason codes | None |
| `GET` | `/api/v1/alerts/{id}/history` | State change audit history | None |
| `PATCH` | `/api/v1/alerts/{id}/status` | Update alert status (`UNDER_REVIEW`, etc.) | Analyst / Admin |

### 3.7 Investigation Cases
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/cases` | Filter cases by status and priority | None |
| `POST` | `/api/v1/cases` | Create investigation dossier from alert | Analyst / Admin |
| `GET` | `/api/v1/cases/{id}` | Case detail, attached alerts, and timeline | None |
| `POST` | `/api/v1/cases/{id}/actions` | Append immutable analyst note or state change | Analyst / Admin |
| `POST` | `/api/v1/cases/{id}/disposition` | Record formal disposition outcome | Compliance / Admin |

### 3.8 Risk Rules
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/rules` | List all 12 configurable detection rules | None |
| `GET` | `/api/v1/rules/{id}` | Retrieve specific rule configuration | None |
| `PATCH` | `/api/v1/rules/{id}` | Update rule threshold, weight, or enabled flag | Admin |
| `POST` | `/api/v1/rules/{id}/test` | Test rule evaluation against synthetic input | None |

### 3.9 Operations & Exports
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/generation-runs` | Trigger deterministic dataset generation | Admin |
| `POST` | `/api/v1/validation-runs` | Execute 24-check referential validation suite | Compliance / Admin |
| `POST` | `/api/v1/evaluation-runs` | Compute evaluation metrics against ground truth | Compliance / Admin |
| `GET` | `/api/v1/exports` | List available export files with SHA-256 | None |
| `GET` | `/api/v1/exports/{filename}` | Download CSV, JSON, or SQL export file | None |
| `GET` | `/api/v1/audit` | Paginated immutable compliance audit trail | None |
