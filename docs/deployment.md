# SentinelIQ — Deployment & Operations Guide
**Intelligent Transaction Risk & Investigation Platform**  
*Tagline: Explainable Risk. Traceable Decisions.*

---

## 1. Hosting Architecture Overview

SentinelIQ is a Python-first, FastAPI-powered enterprise application designed for seamless deployment on both **Render** and **Vercel**:

- **Unified Web Platform on Render (Recommended for Full Workflows):**
  - Runs as an active Python ASGI web service (`uvicorn backend.app.main:app`).
  - Supports background database indexing, streaming exports, and long-running validation suites.
  - Deploys via one-click **Render Blueprint** (`render.yaml`) or Dockerfile.
  - Storage: In-memory fallback by default, or persistent MongoDB Atlas.

- **Serverless Web Platform on Vercel:**
  - Runs as a Python ASGI Serverless Function (`api/index.py` with `@vercel/python`).
  - Edge-cached static assets (`frontend/static/`).
  - Deploys via **Vercel Git Integration** (`https://github.com/ajayreddy510/sentineliq`) or `vercel` CLI.
  - Storage: In-memory pre-seeded storage or connected MongoDB Atlas.

---

## 2. Deploying on Render (Step-by-Step)

### Option A: 1-Click Render Blueprint (Fastest)

1. Go to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** &rarr; **Blueprint**.
3. Connect your GitHub repository:
   ```text
   https://github.com/ajayreddy510/sentineliq
   ```
4. Render will automatically read `render.yaml` from the root of the repository.
5. Click **Apply Blueprint**. Render will build and deploy the `sentineliq` web service on its free tier.
6. Once deployed, open your assigned URL: `https://sentineliq.onrender.com` (or similar).

### Option B: Manual Web Service Setup

If you prefer to configure the service manually on Render:
1. Go to **New +** &rarr; **Web Service**.
2. Select **Build and deploy from a Git repository** and pick `ajayreddy510/sentineliq`.
3. Fill in the service configuration:
   - **Name:** `sentineliq`
   - **Region:** `Oregon (US West)` or your preferred region
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 2`
   - **Instance Type:** `Free`
4. Add Environment Variables:
   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `PYTHON_VERSION` | `3.10.12` | Runtime version |
   | `APP_ENV` | `production` | Production mode |
   | `APP_STORAGE` | `memory` | In-memory with seed (or `mongodb` if using Atlas) |
   | `ENABLE_DEMO_USERS`| `true` | Enables pre-seeded demo accounts |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT session lifetime |
   | `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
   | `SECRET_KEY` | *(Click Generate)* | Secure JWT HMAC secret key |
5. Click **Create Web Service**.

---

## 3. Deploying on Vercel (Step-by-Step)

### Option A: Import via Vercel Dashboard (Recommended)

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** &rarr; **Project**.
3. Select your GitHub repository: `ajayreddy510/sentineliq`.
4. Vercel automatically detects the project root and `vercel.json`.
5. Keep **Framework Preset** as **Other**.
6. (Optional) Set Environment Variables if connecting MongoDB:
   - `APP_STORAGE`: `memory` (or `mongodb`)
   - `MONGODB_URI`: `<your_atlas_connection_string>` (optional)
7. Click **Deploy**.
8. Vercel compiles the `@vercel/python` serverless bundle and assigns a live domain:
   ```text
   https://sentineliq-*.vercel.app
   ```

### Option B: Deploy via Vercel CLI

From your local machine:
```bash
# 1. Login to Vercel
npx vercel login

# 2. Deploy to Preview
npx vercel

# 3. Deploy to Production
npx vercel --prod
```

---

## 4. Optional: MongoDB Atlas Database Setup

To persist data permanently across restarts on both Render and Vercel:

1. Create a free cluster at [cloud.mongodb.com](https://cloud.mongodb.com).
2. Create a database user with read/write privileges (e.g. `sentineliq_admin`).
3. Add `0.0.0.0/0` to Network Access IP Whitelist.
4. Copy the connection URI:
   ```text
   mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
   ```
5. In Render or Vercel dashboard:
   - Set `APP_STORAGE` = `mongodb`
   - Set `MONGODB_URI` = `<your connection string>`
6. Run the initial data seeder:
   ```bash
   python -m scripts.seed_database --export-dir ./exports
   ```

---

## 5. Live Production Verification Checklist

Once deployed to Render or Vercel, verify each endpoint:

| Verification Item | Endpoint | Expected Result |
| :--- | :--- | :--- |
| **1. Service Liveness** | `GET /health` | HTTP 200 `{"status": "healthy", ...}` |
| **2. Database Readiness** | `GET /health/ready` | HTTP 200 (database ping success) |
| **3. OpenAPI Docs** | `GET /docs` | Swagger interactive API docs |
| **4. Login Screen** | `GET /login` | SentinelIQ Sign-In with 4 demo accounts |
| **5. Admin Dashboard** | `GET /dashboard` | 4 metric cards, alerts table, audit stream |
| **6. Evaluation Benchmark**| `GET /evaluation` | 2x2 confusion matrix, F1 0.735, precision 68.8% |
| **7. Rules Engine** | `GET /rules` | Configurable rules, scenario simulator |
| **8. Integrity Suite** | `GET /validation` | 24 automated checks, 5 negative scenarios |
| **9. Data Exports** | `GET /api/v1/exports/customers.csv` | Streamed CSV with SHA-256 validation |
