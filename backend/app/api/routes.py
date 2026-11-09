import csv
import io
import json
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import get_db
from app.models.entities import (
    User,
    Shipment,
    Document,
    ExtractedField,
    LineItem,
    ValidationResult,
    FieldCorrection,
    ApprovalRecord,
    AuditLog,
    ExportRecord,
)
from app.schemas.api import LoginRequest, ShipmentCreate, FieldUpdate, Resolution
from app.core.security import verify_password, create_token
from app.core.config import settings
from app.api.deps import current_user, manager
from app.services.validation import validate_shipment, can_approve, can_export
from app.services.extraction import provider

router = APIRouter(prefix="/api")


@router.post("/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {
        "access_token": create_token(user.id, user.role),
        "role": user.role,
        "email": user.email,
    }


@router.get("/shipments")
def shipments(
    q: str = "", db: Session = Depends(get_db), _: User = Depends(current_user)
):
    query = db.query(Shipment)
    if q:
        query = query.filter(
            (Shipment.reference.contains(q)) | (Shipment.supplier_name.contains(q))
        )
    return [
        {
            "id": s.id,
            "reference": s.reference,
            "supplier": s.supplier_name,
            "supplier_country": s.supplier_country,
            "status": s.status,
            "approval_status": s.approval_status,
            "documents": len(s.documents),
            "updated_at": s.updated_at,
        }
        for s in query.order_by(Shipment.updated_at.desc()).all()
    ]


@router.post("/shipments")
def create(
    body: ShipmentCreate, db: Session = Depends(get_db), _: User = Depends(current_user)
):
    s = Shipment(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "reference": s.reference}


@router.get("/shipments/{shipment_id}")
def detail(
    shipment_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)
):
    s = db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")

    docs = s.documents
    fields = db.query(ExtractedField).filter_by(shipment_id=s.id).all()
    validations = db.query(ValidationResult).filter_by(shipment_id=s.id).all()
    line_items = db.query(LineItem).filter_by(shipment_id=s.id).all()

    return {
        "id": s.id,
        "reference": s.reference,
        "supplier": s.supplier_name,
        "supplier_country": s.supplier_country,
        "status": s.status,
        "approval_status": s.approval_status,
        "documents": [
            {
                "id": d.id,
                "kind": d.kind,
                "filename": d.filename,
                "extraction_status": d.extraction_status,
                "created_at": d.created_at,
            }
            for d in docs
        ],
        "fields": [
            {
                "id": f.id,
                "document_id": f.document_id,
                "name": f.field_name,
                "value": f.value,
                "confidence": round(f.confidence, 2),
                "page": f.page,
                "verified": f.verified,
            }
            for f in fields
        ],
        "line_items": [
            {
                "id": item.id,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.amount,
            }
            for item in line_items
        ],
        "validations": [
            {
                "id": v.id,
                "rule": v.rule,
                "severity": v.severity,
                "status": v.status,
                "details": json.loads(v.details) if v.details else {},
                "resolution": v.resolution,
            }
            for v in validations
        ],
    }


@router.get("/documents/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    file_path = Path(doc.path)
    if not file_path.exists():
        # Fallback to sample document if local synthetic document exists
        fallback = Path(f"sample_data/{file_path.name}")
        if fallback.exists():
            file_path = fallback
        else:
            raise HTTPException(404, "File not found on storage")
    return FileResponse(
        path=str(file_path), media_type="application/pdf", filename=doc.filename
    )


@router.post("/shipments/{shipment_id}/documents")
async def upload(
    shipment_id: str,
    kind: str,
    document: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    if kind not in {"invoice", "packing_list", "bill_of_lading"}:
        raise HTTPException(422, "Unsupported document kind")
    if document.content_type not in {
        "application/pdf",
        "application/x-pdf",
        "binary/octet-stream",
    }:
        raise HTTPException(422, "PDF required")

    s = db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")

    target = Path(settings.storage_path) / shipment_id
    target.mkdir(parents=True, exist_ok=True)
    file_path = target / f"{kind}.pdf"
    with file_path.open("wb") as out:
        shutil.copyfileobj(document.file, out)

    # Clean existing doc for this kind if replacing
    old = db.query(Document).filter_by(shipment_id=shipment_id, kind=kind).first()
    if old:
        # Also clean previously extracted fields for this document
        db.query(ExtractedField).filter_by(document_id=old.id).delete()
        db.delete(old)
        db.flush()

    d = Document(
        shipment_id=shipment_id,
        kind=kind,
        filename=document.filename,
        path=str(file_path),
        extraction_status="processing",
    )
    db.add(d)
    db.flush()

    # Trigger AI Extraction
    try:
        extraction_res = await provider.extract(str(file_path), kind)
        extracted_fields = extraction_res.get("fields", {})
        line_items = extraction_res.get("line_items", [])

        for fname, val_obj in extracted_fields.items():
            db.add(
                ExtractedField(
                    shipment_id=s.id,
                    document_id=d.id,
                    field_name=fname,
                    value=(
                        str(val_obj.get("value"))
                        if val_obj.get("value") is not None
                        else None
                    ),
                    confidence=float(val_obj.get("confidence", 0.5)),
                    page=val_obj.get("page", 1),
                    verified=False,
                )
            )

        if kind == "invoice" and line_items:
            db.query(LineItem).filter_by(shipment_id=s.id).delete()
            for item in line_items:
                db.add(
                    LineItem(
                        shipment_id=s.id,
                        description=item.get("description", "Import Item"),
                        quantity=float(item.get("quantity", 0)),
                        unit_price=float(item.get("unit_price", 0)),
                        amount=float(item.get("amount", 0)),
                    )
                )

        d.extraction_status = "complete"
    except Exception as e:
        d.extraction_status = "manual_review"

    s.status = "review"
    db.commit()

    # Automatically recalculate cross-checks
    validate_shipment(db, s)

    return {"id": d.id, "status": d.extraction_status}


@router.patch("/fields/{field_id}")
def correct(
    field_id: str,
    body: FieldUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    field = db.get(ExtractedField, field_id)
    if not field:
        raise HTTPException(404, "Field not found")

    old_val = field.value
    field.value = body.value
    field.verified = True
    db.add(
        FieldCorrection(
            field_id=field.id,
            user_id=user.id,
            old_value=old_val,
            new_value=body.value,
            reason=body.reason or "Manual correction",
        )
    )
    db.commit()

    # Re-run validations
    shipment = db.get(Shipment, field.shipment_id)
    if shipment:
        validate_shipment(db, shipment)

    return {"ok": True, "verified": True}


@router.post("/shipments/{shipment_id}/validate")
def validate(
    shipment_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)
):
    s = db.get(Shipment, shipment_id)
    if not s:
        raise HTTPException(404, "Shipment not found")
    results = validate_shipment(db, s)
    return [
        {"rule": x.rule, "status": x.status, "severity": x.severity} for x in results
    ]


@router.post("/validations/{validation_id}/resolve")
def resolve(
    validation_id: str,
    body: Resolution,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    result = db.get(ValidationResult, validation_id)
    if not result:
        raise HTTPException(404, "Validation result not found")
    if not body.resolution.strip():
        raise HTTPException(422, "Resolution is required")
    result.status = "resolved"
    result.resolution = body.resolution.strip()
    db.add(
        AuditLog(
            shipment_id=result.shipment_id,
            user_id=user.id,
            action="validation_resolved",
            detail=f"Resolved '{result.rule}': {body.resolution.strip()}",
        )
    )
    db.commit()
    return {"status": "resolved"}


@router.post("/shipments/{shipment_id}/approve")
def approve(
    shipment_id: str, db: Session = Depends(get_db), user: User = Depends(manager)
):
    s = db.get(Shipment, shipment_id)
    if not s or not can_approve(db, shipment_id):
        raise HTTPException(
            409, "Unresolved high-severity validation prevents approval"
        )
    s.approval_status = "approved"
    s.status = "approved"
    db.add(ApprovalRecord(shipment_id=s.id, user_id=user.id, action="approved"))
    db.commit()
    return {"status": "approved"}


@router.get("/shipments/{shipment_id}/export")
def export(
    shipment_id: str, db: Session = Depends(get_db), user: User = Depends(manager)
):
    s = db.get(Shipment, shipment_id)
    if not s or s.approval_status != "approved" or not can_export(db, shipment_id):
        raise HTTPException(
            409,
            "Shipment is not eligible for export (pending verification or approvals)",
        )

    stream = io.StringIO()
    writer = csv.writer(stream)
    # Customs Filing Software standard flat schema
    writer.writerow(
        [
            "BE_Type",
            "Shipment_Ref",
            "Supplier",
            "Country",
            "Invoice_No",
            "Invoice_Date",
            "Currency",
            "Incoterm",
            "Item_Description",
            "Quantity",
            "Unit_Price",
            "Line_Amount",
            "Gross_Weight_Kg",
            "Packages",
            "Container_No",
        ]
    )

    fields = {
        f.field_name: f.value
        for f in db.query(ExtractedField).filter_by(shipment_id=shipment_id)
    }
    items = db.query(LineItem).filter_by(shipment_id=shipment_id).all()

    inv_no = fields.get("invoice_number", "")
    inv_date = fields.get("invoice_date", "")
    currency = fields.get("currency", "USD")
    incoterm = fields.get("incoterm", "FOB")
    gross_wt = fields.get("gross_weight", "")
    pkgs = fields.get("package_count", "")
    cntr = fields.get("container_number", "")

    if items:
        for it in items:
            writer.writerow(
                [
                    "HOME_CONSUMPTION",
                    s.reference,
                    s.supplier_name,
                    s.supplier_country or "IN",
                    inv_no,
                    inv_date,
                    currency,
                    incoterm,
                    it.description,
                    it.quantity,
                    it.unit_price,
                    it.amount,
                    gross_wt,
                    pkgs,
                    cntr,
                ]
            )
    else:
        writer.writerow(
            [
                "HOME_CONSUMPTION",
                s.reference,
                s.supplier_name,
                s.supplier_country or "IN",
                inv_no,
                inv_date,
                currency,
                incoterm,
                "General Cargo",
                1,
                fields.get("invoice_grand_total", "0"),
                fields.get("invoice_grand_total", "0"),
                gross_wt,
                pkgs,
                cntr,
            ]
        )

    db.add(ExportRecord(shipment_id=s.id, user_id=user.id, format="csv"))
    db.commit()
    return Response(
        stream.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=customs_filing_{s.reference}.csv"
        },
    )


@router.get("/reports/accuracy")
def get_accuracy_report(db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Accuracy metrics per field and supplier based on correction audit logs."""
    total_fields = db.query(ExtractedField).count()
    corrections_count = db.query(FieldCorrection).count()
    overall_accuracy = round(
        ((total_fields - corrections_count) / max(total_fields, 1)) * 100, 1
    )

    # Group by field
    field_stats = {}
    all_fields = db.query(ExtractedField).all()
    for f in all_fields:
        field_stats.setdefault(f.field_name, {"total": 0, "corrected": 0})
        field_stats[f.field_name]["total"] += 1

    corrections = db.query(FieldCorrection).all()
    for c in corrections:
        cf = db.get(ExtractedField, c.field_id)
        if cf and cf.field_name in field_stats:
            field_stats[cf.field_name]["corrected"] += 1

    field_report = []
    for fname, st in field_stats.items():
        acc = round(((st["total"] - st["corrected"]) / max(st["total"], 1)) * 100, 1)
        field_report.append(
            {
                "field": fname,
                "total_extracted": st["total"],
                "corrected": st["corrected"],
                "accuracy_percent": acc,
            }
        )

    # Group by supplier
    suppliers = db.query(Shipment.supplier_name).distinct().all()
    supplier_report = []
    for (sname,) in suppliers:
        shp_ids = [
            s.id for s in db.query(Shipment).filter_by(supplier_name=sname).all()
        ]
        s_total = (
            db.query(ExtractedField)
            .filter(ExtractedField.shipment_id.in_(shp_ids))
            .count()
        )
        s_corr = (
            db.query(FieldCorrection)
            .join(ExtractedField)
            .filter(ExtractedField.shipment_id.in_(shp_ids))
            .count()
        )
        acc = round(((s_total - s_corr) / max(s_total, 1)) * 100, 1)
        supplier_report.append(
            {
                "supplier": sname,
                "shipments": len(shp_ids),
                "total_fields": s_total,
                "corrections": s_corr,
                "accuracy_percent": acc,
            }
        )

    recent_corrections = [
        {
            "id": c.id,
            "old_value": c.old_value,
            "new_value": c.new_value,
            "reason": c.reason,
            "timestamp": c.created_at,
        }
        for c in db.query(FieldCorrection)
        .order_by(FieldCorrection.created_at.desc())
        .limit(15)
        .all()
    ]

    return {
        "overall_accuracy_percent": overall_accuracy,
        "total_fields_extracted": total_fields,
        "total_corrections": corrections_count,
        "by_field": field_report,
        "by_supplier": supplier_report,
        "recent_audit": recent_corrections,
    }
