# SentinelIQ — Security, Authentication & Access Control
**Intelligent Transaction Risk & Investigation Platform**  
*Tagline: Explainable Risk. Traceable Decisions.*

---

## 1. Logical Roles & Permissions Matrix

SentinelIQ enforces Role-Based Access Control (RBAC) server-side across all API routes and UI actions:

| Action / Capability | ADMIN | ANALYST | COMPLIANCE_REVIEWER | READ_ONLY |
|---|:---:|:---:|:---:|:---:|
| **View Dashboard, Transactions, Customers** | &check; | &check; | &check; | &check; |
| **Inspect Alerts & Evidence** | &check; | &check; | &check; | &check; |
| **Create Investigation Case** | &check; | &check; | &cross; | &cross; |
| **Record Analyst Notes / Status Changes** | &check; | &check; | &cross; | &cross; |
| **Submit Final Case Disposition** | &check; | &cross; | &check; | &cross; |
| **Modify Risk Rule Parameters / Thresholds** | &check; | &cross; | &cross; | &cross; |
| **Trigger Synthetic Dataset Generation** | &check; | &cross; | &cross; | &cross; |
| **Execute Validation & Evaluation Pipelines** | &check; | &cross; | &check; | &cross; |
| **Inspect Immutable Audit Trail** | &check; | &check; | &check; | &check; |

---

## 2. Authentication Architecture

- **Password Storage:** Passwords hashed with native `bcrypt` using 12 salt rounds. Plaintext passwords are never persisted.
- **JWT Tokens:** Signed using HMAC-SHA256 (`HS256`) with a configurable secret key (`SECRET_KEY`) and documented expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Session Cookies:** Dual token delivery supports both REST API clients (via `Authorization: Bearer <token>`) and browser server-rendered HTML pages (via secure `access_token` cookies with `SameSite=Lax`).
- **Zero Committed Secrets:** All credentials, keys, and database URIs are loaded strictly via environment variables.

---

## 3. Audit Trail Integrity

All state transitions, analyst notes, case creations, and rule updates are appended to the `audit_events` collection. No endpoint exists to alter or delete historical audit entries.
