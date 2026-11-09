# How to use the CargoLens application flow

## 1. Start the application

Start the API from `backend/`:

```bash
uvicorn app.main:app --reload
```

Start the web application from `frontend/`:

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## 2. Sign in

Use one of the seeded demonstration accounts:

| Role | Email | Password |
| --- | --- | --- |
| Manager | `manager@cargolens.demo` | `demo-password` |
| Executive | `executive@cargolens.demo` | `demo-password` |

Managers can approve shipments and download exports. Executives can create, upload, review, and correct shipment data.

## 3. Review the dashboard

The dashboard lists seeded shipments. Select **Review** for a shipment to open the document-review workspace.

- `SHP-24811` is the complete synthetic demonstration shipment.
- `SHP-24812` is deliberately sparse: CargoLens must not infer facts that are absent from the source evidence.

## 4. Review extraction evidence

In the review workspace, inspect each field and its confidence score.

- Green indicates a high-confidence result.
- Amber/red indicates a low-confidence result that needs human confirmation.
- Edit a value only after checking the source document. Moving out of the edited field saves a correction and creates an audit record.

The current MVP shows a PDF preview placeholder. Documents are stored locally by the API, but a signed file-view endpoint is still needed to render uploaded PDFs directly in the browser.

## 5. Run reconciliation

Call the validation endpoint after documents or values change:

```bash
curl -X POST http://localhost:8000/api/shipments/SHIPMENT_ID/validate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

For `SHP-24811`, reconciliation identifies the intended high-severity discrepancy:

- Invoice gross weight: `3120 kg`
- Packing-list gross weight: `3165 kg`
- Difference: `45 kg`

The backend also checks invoice arithmetic, required fields, and container consistency. Missing evidence is kept open for review rather than treated as a pass.

## 6. Resolve issues and approve

Resolve or correct all high-severity results before approval. A manager then approves the shipment through:

```bash
curl -X POST http://localhost:8000/api/shipments/SHIPMENT_ID/approve \
  -H "Authorization: Bearer MANAGER_TOKEN"
```

The API rejects approval while any high-severity validation result remains open.

## 7. Export CSV

Once approved, a manager can export the validated fields:

```bash
curl http://localhost:8000/api/shipments/SHIPMENT_ID/export \
  -H "Authorization: Bearer MANAGER_TOKEN" \
  -o shipment.csv
```

Export is blocked until the shipment is approved and no required field remains both low-confidence and unverified.

## API login example

Use this to obtain a token for the API examples:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"manager@cargolens.demo","password":"demo-password"}'
```
