# SentinelIQ — Deployment & Operations Guide
**Intelligent Transaction Risk & Investigation Platform**  
*Tagline: Explainable Risk. Traceable Decisions.*

---

## 1. Hosting Architecture

SentinelIQ is architected for independent, production-grade cloud deployment:

- **FastAPI Backend:** Deployed to **Render** as a standard Python Web Service (`uvicorn backend.app.main:app`).
- **Database Persistence:** Hosted on **MongoDB Atlas** with Replica Set support and explicit unique/compound indexing.
- **Frontend:** Server-rendered Jinja2 interface deployable directly as part of the FastAPI unified service on Render, or as a standalone Python Serverless application on **Vercel** (`api/index.py` with `@vercel/python`).

---

## 2. Critical Platform Deployment Analysis: Vercel vs. Render

### Vercel Python Serverless Constraints
1. **Serverless Execution Model:** Vercel functions are stateless and ephemeral with maximum execution durations (default 10s on hobby, up to 300s on pro). Vercel does **not** support conventional, permanently running daemon processes or persistent background workers.
2. **Socket & File System Isolation:** The local container filesystem on Vercel is read-only (except `/tmp`). Heavy generation runs (e.g. 100,000 transactions) must not be written to local disks in serverless functions.
3. **Closest Python-First Alternative:**
   - **Unified Deployment (Recommended):** Host the FastAPI application on Render, which natively serves both the REST API and the Jinja2 server-rendered HTML pages at full speed with zero cross-origin latency.
   - **Separated Deployment:** Deploy `frontend/app.py` to Vercel via `@vercel/python` pointing its `API_BASE_URL` to the Render backend service.

---

## 3. Render Backend Deployment Guide

### Step 1: Create Web Service on Render
1. Connect your GitHub repository: `sentineliq-risk-intelligence`.
2. Select **Python 3** as the runtime environment.
3. Configure settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 2`
   - **Health Check Path:** `/health`

### Step 2: Configure Environment Variables
Set the following environment variables in the Render Dashboard:
```ini
APP_ENV=production
APP_STORAGE=mongodb
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=sentineliq_risk_intelligence
SECRET_KEY=<generate_secure_random_hex_string_32_bytes_min>
ACCESS_TOKEN_EXPIRE_MINUTES=480
ENABLE_DEMO_USERS=true
CORS_ORIGINS=["https://sentineliq.vercel.app","http://localhost:8000"]
API_BASE_URL=https://<your-render-app>.onrender.com/api/v1
```

---

## 4. MongoDB Atlas Setup Guide

### Step 1: Create Cluster & User
1. Log in to [MongoDB Atlas](https://cloud.mongodb.com) and create an **M0 Free Tier** or Dedicated cluster.
2. Under **Security &rarr; Database Access**, create a user (e.g. `sentineliq_admin`) with `readWriteAnyDatabase` privileges.
3. Under **Security &rarr; Network Access**, whitelist your deployment IP addresses (or `0.0.0.0/0` with strong authentication for initial testing).

### Step 2: Get Connection String
1. Click **Connect &rarr; Drivers &rarr; Python 3.10+**.
2. Copy the connection URI:
   `mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority`
3. Paste into `MONGODB_URI` in `.env` or Render environment settings.

### Step 3: Run Database Seeder
From a local terminal with network access to Atlas:
```bash
python -m scripts.seed_database --export-dir ./exports
```
This idempotently creates all indexes and upserts the generated financial entities into Atlas!

---

## 5. Deployment Verification Checklist

| Verification Item | Command / URL | Expected Result |
|---|---|---|
| **1. Backend Liveness** | `GET /health` | HTTP 200, status: "healthy", service: "SentinelIQ" |
| **2. Database Readiness** | `GET /health/ready` | HTTP 200, database_connected: true, ping succeeds |
| **3. OpenAPI Docs** | `GET /docs` | Swagger UI loads with full schema |
| **4. Web UI Dashboard** | `GET /dashboard` | Metrics populate from real database |
| **5. Authentication** | `POST /api/v1/auth/login` | Valid JWT token issued, cookie set |
| **6. Case Management** | `POST /api/v1/cases` | New case created and visible in dashboard |
| **7. Validation Run** | `GET /api/v1/metrics/data-quality` | 24 validation checks reported |
| **8. Evaluation Run** | `GET /api/v1/metrics/evaluation/summary` | Precision, recall, and confusion matrix visible |
| **9. Exports Download** | `GET /api/v1/exports/customers.csv` | Valid UTF-8 CSV stream with SHA-256 matching manifest |
