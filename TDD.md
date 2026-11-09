# CargoLens — Technical Design Document (TDD)
**Project Repository:** [https://github.com/Udayscode/cargolens.git](https://github.com/Udayscode/cargolens.git)  
**Author:** Software Engineering Candidate  
**Client:** Company A, Freight Forwarder & Customs Broker, Nhava Sheva (JNPT), Navi Mumbai  
**Date:** November 2026  

---

## 1. Executive Summary & Client Context

Company A handles approximately **1,100 import shipments per month** through the Nhava Sheva port with a documentation team of 14 executives and managers. Today, executives spend 45 minutes per shipment manually retyping unstructured data from PDFs, scanned papers, and camera photos into Excel checklists before re-entering them into customs filing software.

### The Financial & Operational Cost:
- **Direct Labor Drain:** 1,100 shipments × 0.75 hours × 12 months = 9,900 staff hours = **₹34.65 lakh/year** (at ₹350/hour).
- **Error Penalties & Demurrage:** A 3% document mismatch rate leads to 396 amended Bills of Entry per year. At an average penalty, staff time, and demurrage cost of ₹9,000 per incident, this burns **₹35.64 lakh/year**.
- **Total Annual Loss:** **₹70.29 lakh per year**.

**CargoLens** is purpose-built to eliminate manual retyping, catch multi-document discrepancies prior to filing, and export directly in the filing software’s format without altering existing customs filing workflows.

---

## 2. Explicit Assumptions

- **[Assumption 1: Core Document Trio]** Every sea import shipment relies on three foundational source documents: the **Commercial Invoice**, the **Packing List**, and the **Bill of Lading (B/L)**.
- **[Assumption 2: Source File Types]** Importers provide source files primarily as digital or scanned PDFs. Scans may exhibit rotation, skew, or bilingual headers (e.g., English and Mandarin).
- **[Assumption 3: Filing Software Ingestion]** The existing customs filing software accepts standard structured CSV/Excel imports for Bill of Entry (BoE) generation; direct ICEGATE API integration is neither supported nor desired by the client.
- **[Assumption 4: Data Privacy & Residency]** Under the **Digital Personal Data Protection (DPDP) Act 2023**, consignee/importer details, commercial invoices, and tariff data are sensitive. All server instances, databases, and document object stores must reside within the territory of India (e.g., AWS Mumbai `ap-south-1`).
- **[Assumption 5: AI Model Training Policy]** The vision AI provider must offer enterprise-grade zero-data-retention commitments ensuring client commercial invoice pricing is never utilized for public foundational model training.
- **[Assumption 6: Human Verification Threshold]** Extracted fields with a confidence score below **80% (0.80)**, or fields implicated in cross-check discrepancies, must undergo mandatory human verification before export eligibility is granted.

---

## 3. System Architecture & Rationale

```
  ┌─────────────────────────────────────────────────────────────┐
  │                 Next.js 15 Desktop UI                       │
  │   - Dossier Dashboard     - Side-by-Side Review Workspace   │
  │   - Discrepancy Alerts    - Accuracy & Audit Telemetry      │
  └──────────────┬──────────────────────────────▲───────────────┘
                 │ REST API / JWT                │
                 ▼                               │
  ┌─────────────────────────────────────────────────────────────┐
  │                   FastAPI Backend Gateway                   │
  │  ┌───────────────────┐  ┌──────────────────┐  ┌───────────┐ │
  │  │ RBAC (Exec/Mgr)   │  │ Validation Engine│  │ Audit Log │ │
  │  └───────────────────┘  └──────────────────┘  └───────────┘ │
  └──────────────┬──────────────────────────────┬───────────────┘
                 │                              │
                 ▼                              ▼
  ┌──────────────────────────────┐ ┌────────────────────────────┐
  │   Extraction Engine Provider │ │       Data Persistence     │
  │  ┌──────────────────────────┐│ │  - SQLite (Local Dev)      │
  │  │ Google Gemini 1.5 Flash  ││ │  - PostgreSQL (Production) │
  │  └──────────────────────────┘│ │  - Secure Local / S3 Vault │
  │  ┌──────────────────────────┐│ └────────────────────────────┘
  │  │ Heuristic Fallback Engine││
  │  └──────────────────────────┘│
  └──────────────────────────────┘
```

### Architectural Choices:
1. **FastAPI (Python 3.11):** Chosen for native async IO, strict Pydantic type validation, and seamless integration with document processing and data manipulation libraries.
2. **Next.js 15 & React 19:** Enables a fast, responsive desktop interface tailored for documentation operators who spend 8+ hours a day in high-density review tables.
3. **Provider Boundary Pattern for Vision AI:** Document extraction is abstracted behind an `ExtractionProvider` interface. If `GEMINI_API_KEY` is present, it uses Gemini 1.5 Flash multimodal extraction. If absent or during offline network conditions, it smoothly falls back to a deterministic rule-based extractor so reviewer tests never fail.
4. **Deterministic Validation Engine:** AI is used strictly for extraction, **never** for business rule verification. Arithmetic balances and multi-document weight cross-checks are executed deterministically in Python to prevent hallucinated reconciliations.

---

## 4. Data Model & Entity Schema

The database is structured around immutable auditability and relational traceability:

- **`User`**: Supports role-based access control (`executive` vs. `manager`).
- **`Shipment`**: Central dossier tracking supplier, country of origin, approval status (`pending`, `approved`), and operational status.
- **`Document`**: Represents uploaded PDFs (`invoice`, `packing_list`, `bill_of_lading`) with storage paths and extraction states.
- **`ExtractedField`**: Key-value pairs (`invoice_number`, `gross_weight`, `container_number`, `incoterm`, etc.) tied to specific documents, accompanied by a numeric confidence score ($0.00 - 1.00$), source page number, and boolean `verified` flag.
- **`LineItem`**: Granular invoice rows storing item descriptions, quantities, unit prices, and extended amounts.
- **`ValidationResult`**: Output of automated cross-checks (`rule`, `severity`: `high`/`medium`/`low`, `status`: `open`/`resolved`, `details`, `resolution`).
- **`FieldCorrection`**: Complete audit record logging `old_value`, `new_value`, user ID, and timestamp when an executive edits an AI-extracted field.
- **`ApprovalRecord` & `ExportRecord`**: Cryptographic-grade audit trails tracking manager sign-offs and file exports.

---

## 5. Main Workflows & AI Pipeline

### 5.1 Document Ingestion & Vision AI Extraction
1. The operator uploads a PDF for any of the 3 required document kinds.
2. The file is written to secure encrypted storage.
3. The extraction engine evaluates the document:
   - For Gemini Vision API: Sends base64-encoded PDF pages to `gemini-1.5-flash` with a strict JSON schema prompt instructing it to extract parties, dates, weights, package counts, container numbers, and individual line items with confidence scores.
   - For Fallback/Offline Mode: Parses text and maps known customs document templates.
4. Extracted fields and line items are populated into the database.

### 5.2 Deterministic Multi-Document Cross-Checks
Upon completion of extraction or manual field edit, the validation engine triggers four critical cross-checks:
1. **Invoice Arithmetic Check:** $\left|\text{Invoice Grand Total} - \sum (\text{Line Item Quantities} \times \text{Unit Prices})\right| \le 0.01$. Catches rounding errors or unstated freight/insurance additions.
2. **Multi-Document Gross Weight Reconciliation:** Compares extracted gross weight values across the Commercial Invoice, Packing List, and Bill of Lading. A variance $> 1\text{ kg}$ raises a `HIGH` severity mismatch.
   - *Example in sample data:* `SHP-24811` Commercial Invoice declares **3,120 kg**, while the Packing List declares **3,165 kg**. The system immediately flags a **45 kg discrepancy**.
3. **Container Consistency Check:** Verifies container numbers (e.g., `MSCU1234567`) across the Packing List and Bill of Lading to prevent customs mismatch rejections.
4. **Mandatory Completeness Check:** Confirms presence of mandatory fields (`invoice_number`, `gross_weight`, `package_count`).

### 5.3 Human-in-the-Loop Review & Export Gate
- **Low-Confidence Highlighting:** Any field with confidence $< 0.80$ is rendered with a prominent amber alert badge.
- **Resolution of Discrepancies:** Documentation executives can edit values inline. Edits are recorded in `field_corrections` with justification. Open high-severity validation results must have an explanatory resolution recorded.
- **Enforced Export Gate:** The manager approval endpoint (`POST /shipments/{id}/approve`) and export endpoint (`GET /shipments/{id}/export`) strictly check `can_approve()` and `can_export()`. **No shipment can be approved or exported while high-severity violations or unverified required low-confidence fields remain.**

---

## 6. UI & UX Design Decisions

The user interface was crafted in accordance with the client’s request for **good, minimal design** with high information density:

1. **Operations Overview Dashboard (`/`):**
   - High-level metric cards: Active Shipments, Pending Review, and AI Extraction Accuracy.
   - Quick-action "New Shipment" modal for rapid file initiation.
   - Searchable, clear table showing status badges (`review`, `approved`, `awaiting_documents`).
2. **Dedicated Accuracy & Supplier Report Tab:**
   - Visual breakdown of model accuracy by individual field (e.g. `gross_weight`: 96%, `container_number`: 91%).
   - Supplier-level accuracy rankings (highlighting suppliers with messy scans).
   - Real-time audit log of manual corrections.
3. **Side-by-Side Review Workspace (`/shipments/[id]`):**
   - **Left Pane:** Embedded interactive PDF viewer displaying the actual source document with page controls.
   - **Right Pane:** Categorized extracted fields with confidence badges, page indicators, and inline edit controls.
   - **Cross-Check Alert Header:** Prominently highlights weight and container mismatches with direct one-click resolution prompts.

---

## 7. Scope Cuts & Future Roadmap

### What Was Cut for the MVP Slice:
- **Direct ICEGATE EDI Portal Filing:** Customs brokers at Nhava Sheva utilize specialized desktop software; auto-filing without broker review introduces substantial regulatory liability.
- **Automated HSN Tariff Code Classification:** Customs duty classification involves complex Indian Customs Tariff interpretations; kept out of scope to prioritize extraction fidelity.
- **Multi-Factor Authentication (MFA):** Simplified to JWT role-based access for the take-home build.

### Next Steps for Version 2:
1. **Interactive Bounding Box Overlay:** Rendering OCR bounding boxes directly over the PDF canvas on field hover.
2. **WhatsApp / Email Ingestion Webhook:** Automatically creating shipment dossiers when importers email documents to a dedicated forwarder address.
3. **Supplier OCR Learning Profiles:** Auto-learning custom coordinate templates for repeat suppliers (e.g. Company B China).
