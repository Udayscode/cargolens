# CargoLens — Customs AI Document Extraction & 3-Way Cross-Check Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js 15](https://img.shields.io/badge/Frontend-Next.js%2015-black?logo=next.js)](https://nextjs.org)
[![Gemini Vision](https://img.shields.io/badge/AI-Gemini%201.5%20Flash-4285F4?logo=google)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-Proprietary-blue.svg)]()

> **Submission for Customs Broker Take-Home Challenge**  
> **Repository:** [https://github.com/Udayscode/cargolens.git](https://github.com/Udayscode/cargolens.git)  
> **Documentation:** [Technical Design Document (TDD)](TDD.md) | [Deployment & Operations Guide](deployment.md)

---

## 1. Problem & Context

**Client:** Company A, Navi Mumbai (Freight Forwarder & Customs Broker at Nhava Sheva / JNPT Port).  
**Scale:** 1,100 import shipments/month, 14 documentation staff.

### The Bottleneck:
- Importers email invoices, packing lists, and bills of lading as PDFs or photos.
- Staff spend **45 minutes per shipment** manually typing data into Excel and customs filing software (**₹34.65 lakh/year** in labor cost).
- A **3% mismatch rate** leads to 396 amended Bills of Entry per year, triggering port delays and demurrage (**₹35.64 lakh/year**).
- **Total Annual Cost of Error & Delay:** **₹70.29 lakh / year**.

### The Solution:
**CargoLens** ingests the three core shipping documents, extracts structured data using multimodal vision AI with confidence scores, runs deterministic 3-way reconciliation (invoice arithmetic, weight discrepancies, and container conflicts), and provides a side-by-side verification interface before exporting clean CSV files directly into existing customs filing software.

---

## 2. Core Capabilities

1. **Multimodal AI Extraction (Google Gemini 1.5 Flash + Fallback Engine):**
   - Automatically extracts parties, invoice number/date, currency, Incoterms, gross/net weights, packages, container numbers, and itemized line items with confidence scores ($0.00 - 1.00$) and page numbers.
   - Built-in offline fallback engine guarantees complete functionality during local evaluation without requiring external API keys.
2. **Reliable 3-Way Deterministic Cross-Checks:**
   - **Weight Reconciliation:** Catches discrepancies across Commercial Invoice, Packing List, and Bill of Lading (e.g. automatically flags the 45 kg mismatch on seeded shipment `SHP-24811`).
   - **Invoice Arithmetic:** Verifies that line item sums match the declared invoice grand total.
   - **Container Consistency:** Validates container numbers across shipping documents.
   - **Completeness:** Flags missing mandatory customs filing fields.
3. **Side-by-Side Review Workspace:**
   - Embedded PDF viewer beside extracted fields.
   - Low-confidence fields ($< 80\%$) highlighted with amber warning badges requiring human-in-the-loop verification.
   - Single-click inline editing with automatic correction logging.
4. **Accuracy & Supplier Telemetry:**
   - Real-time accuracy metrics tracked per field and per supplier to evaluate OCR reliability over time.
   - Complete audit trail of manual adjustments.
5. **Strict Role-Based Access Control (RBAC):**
   - **Documentation Executive:** Data entry, PDF uploads, field verification, discrepancy resolution.
   - **Documentation Manager:** Final sign-off, validation overrides, and ICEGATE CSV export.

---

## 3. Quick Start (Run Locally)

### Option A: Using Local Environment

#### 1. Backend (FastAPI + SQLite)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*API is accessible at `http://localhost:8000` (Interactive docs at `http://localhost:8000/docs`).*

#### 2. Frontend (Next.js 15)
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
*Web application opens at `http://localhost:3000`.*

---

### Option B: Docker Compose (Single Command)

```bash
docker compose up --build
```

---

## 4. Demo Login Credentials

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Documentation Manager** | `manager@cargolens.demo` | `demo-password` | Full review, validation overrides, approval & export |
| **Documentation Executive** | `executive@cargolens.demo` | `demo-password` | Document upload, field corrections, discrepancy resolution |

---

## 5. Sample Data & Test Scenarios

The database is pre-seeded with realistic shipments based on the brief:

1. **`SHP-24811` (Company B, China — LED Panel Lights):**
   - **Seeded Discrepancy:** Commercial Invoice declares gross weight **3,120 kg**, but the Packing List declares **3,165 kg** (**45 kg mismatch**).
   - **Low-Confidence Flag:** Container number `MSCU1234567` has confidence 74% and requires confirmation.
   - **Result:** Export is blocked until the mismatch is resolved and verified.
2. **`SHP-24812` (Company C, Sweden — Steel Ball Valves):**
   - Invoiced at EUR 42.50 × 180 = EUR 7,650.00.
   - Clean, matched dossier ready for manager sign-off and export.

---

## 6. Project Structure

```
cargolens/
├── backend/
│   ├── app/
│   │   ├── api/             # Routes, auth, dependency injection
│   │   ├── core/            # Config, JWT security, password hashing
│   │   ├── models/          # SQLAlchemy entities & database connection
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # AI extraction (Gemini + fallback) & cross-check validation
│   │   └── main.py          # FastAPI application & database seeding
│   ├── tests/               # Pytest test suite for validation & API flows
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── shipments/[id]/  # Side-by-side review workspace with embedded PDF
│   │   ├── layout.tsx       # Root layout
│   │   ├── page.tsx         # Operations dashboard & accuracy report
│   │   └── globals.css      # Custom styling (minimalist palette)
│   └── package.json
├── deployment.md            # Deployment and operations documentation
├── TDD.md                   # Technical Design Document
├── generate_submission.py   # Script to package submission zip and Word doc
└── README.md
```

---

## 7. Running Tests & Code Quality

```bash
# Run backend test suite:
cd backend
pytest

# Format backend:
black app/

# Format frontend:
cd ../frontend
npm run format
```

---

## 8. Submission Artifacts

To create the final evaluation package:
```bash
python3 generate_submission.py
```
This generates **`cargolens_submission.zip`** containing:
1. `Technical_Design_Document.docx` (and `TDD.md`)
2. `deployment.md`
