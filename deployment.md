# CargoLens — Deployment & Operations Guide

## 1. Quick Local Setup (Step by Step)

### Prerequisites
- Python 3.10+
- Node.js 18+ (with npm or pnpm)
- SQLite3 (default for local development) or PostgreSQL 15+

---

### Step 1: Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Linux / macOS / WSL:
   source .venv/bin/activate
   # On Windows PowerShell:
   .venv\Scripts\Activate.ps1
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create an environment file `.env` in the `backend/` directory:
   ```env
   DATABASE_URL=sqlite:///./cargolens.db
   JWT_SECRET=super-secret-jwt-key-replace-in-production
   JWT_ALGORITHM=HS256
   STORAGE_PATH=./storage
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
   *(Note: If `GEMINI_API_KEY` is omitted or left blank, the application automatically falls back to the built-in deterministic customs extraction engine so the full review flow can be evaluated offline.)*

5. Run the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   *The database schema and sample shipment dossiers (`SHP-24811` and `SHP-24812`) will automatically initialize on startup.*

---

### Step 2: Frontend Setup

1. Open a second terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure frontend environment variables in `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   ```

4. Launch the Next.js development server:
   ```bash
   npm run dev
   ```

5. Access the application in your browser:
   ```
   http://localhost:3000
   ```

---

## 2. Docker Compose Deployment (Single Command)

To run both frontend, backend, and persistent storage in containers:
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API & OpenAPI Docs: `http://localhost:8000/docs`

---

## 3. Environment Variables Specification

*Per submission rules, only variable names are listed:*

### Backend Environment Variables
| Variable Name | Purpose | Default / Requirement |
|---|---|---|
| `DATABASE_URL` | Database connection string (PostgreSQL in production, SQLite in local dev) | Required |
| `JWT_SECRET` | Secret key used to sign and verify role-based JWT authentication tokens | Required |
| `JWT_ALGORITHM` | Cryptographic algorithm for JWT hashing (e.g. HS256) | Required |
| `STORAGE_PATH` | Local filesystem path or mount point for uploaded customs documents | Required |
| `GEMINI_API_KEY` | Google Gemini API key for multimodal vision document extraction | Optional (Fallback engine active if unset) |
| `ALLOWED_ORIGINS` | Comma-separated list of permitted CORS frontend domains | Optional |

### Frontend Environment Variables
| Variable Name | Purpose | Default / Requirement |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL pointing to the CargoLens backend API gateway | Required |

---

## 4. Production Cloud Deployment Architecture

- **Compute & Hosting:**
  - Backend deployed on managed container infrastructure (AWS ECS Fargate, GCP Cloud Run, or Railway) in the **AWS Mumbai (ap-south-1) / GCP Mumbai (asia-south1)** region to strictly comply with Indian data residency and the **Digital Personal Data Protection (DPDP) Act 2023**.
  - Frontend static assets and SSR hosted on Vercel or Cloudflare Pages with edge caching.
- **Database:** Managed PostgreSQL (AWS RDS / Supabase) with encrypted storage at rest (AES-256) and TLS 1.3 in transit.
- **Document Storage:** S3-compatible private bucket (AWS S3 Mumbai or Cloudflare R2) configured with bucket encryption and private pre-signed URLs.
- **Vision AI Engine:** Google Gemini 1.5 Flash via Enterprise API endpoint adhering to zero-data-retention (client documents are not used for public model training).

---

## 5. Reviewer Demo Credentials

Pre-seeded credentials for immediate evaluation:

| Role | Email | Password | Permissions & Scope |
|---|---|---|---|
| **Documentation Manager** | `manager@cargolens.demo` | `demo-password` | Full review access, document cross-check overrides, shipment final approval, ICEGATE/customs CSV export, accuracy reports. |
| **Documentation Executive** | `executive@cargolens.demo` | `demo-password` | Shipment creation, document upload (PDF), field correction, discrepancy resolution, manual verification. |

### Evaluation Workflow:
1. Log in as **Documentation Executive** or **Manager**.
2. Select pre-seeded shipment **`SHP-24811`** (LED Panel Lights from China).
3. Observe the side-by-side document viewer and the **45 kg gross weight mismatch** detected between the Commercial Invoice (3,120 kg) and Packing List (3,165 kg).
4. Review low-confidence fields (<80%) flagged with warnings.
5. Record an evidence resolution for the weight mismatch.
6. Switch or log in as **Manager** to approve the filing and export the customs filing CSV.
