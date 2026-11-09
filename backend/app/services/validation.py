import json
from sqlalchemy.orm import Session
from app.models.entities import Shipment, ExtractedField, LineItem, ValidationResult

REQUIRED_FIELDS = {"invoice_number", "gross_weight", "package_count"}


def get_field_values(
    db: Session, shipment_id: str
) -> dict[str, list[tuple[str | None, str | None]]]:
    """Retrieve all extracted fields for a shipment grouped by field name."""
    rows = db.query(ExtractedField).filter_by(shipment_id=shipment_id).all()
    grouped = {}
    for row in rows:
        grouped.setdefault(row.field_name, []).append((row.value, row.document_id))
    return grouped


def validate_shipment(db: Session, shipment: Shipment) -> list[ValidationResult]:
    """
    Executes deterministic 3-way cross-checks:
    1. Invoice arithmetic (line item total vs declared invoice total)
    2. Multi-document weight comparison (Commercial Invoice vs Packing List vs B/L)
    3. Container consistency across shipping documents
    4. Required field completeness
    """
    # Clean previous validation records for fresh evaluation
    db.query(ValidationResult).filter_by(shipment_id=shipment.id).delete()
    values = get_field_values(db, shipment.id)
    results = []

    def record_check(rule: str, severity: str, status: str, details: dict):
        results.append(
            ValidationResult(
                shipment_id=shipment.id,
                rule=rule,
                severity=severity,
                status=status,
                details=json.dumps(details),
            )
        )

    # 1. Invoice Arithmetic Cross-Check
    items = db.query(LineItem).filter_by(shipment_id=shipment.id).all()
    grand_totals = values.get("invoice_grand_total", [])
    if grand_totals and items:
        try:
            declared = float(
                str(grand_totals[0][0]).replace(",", "").replace("$", "").strip()
            )
            calculated = round(sum(x.amount for x in items), 2)
            passed = abs(declared - calculated) <= 0.05
            record_check(
                "invoice_arithmetic",
                severity="high",
                status="pass" if passed else "open",
                details={
                    "declared_total": declared,
                    "calculated_line_sum": calculated,
                    "delta": round(declared - calculated, 2),
                },
            )
        except (ValueError, TypeError):
            record_check(
                "invoice_arithmetic",
                "high",
                "open",
                {"reason": "Non-numeric invoice total format"},
            )
    else:
        record_check(
            "invoice_arithmetic",
            "medium",
            "open",
            {"reason": "Missing invoice total or line items for audit"},
        )

    # 2. Multi-Document Gross Weight Cross-Check
    weights = values.get("gross_weight", [])
    numeric_weights = []
    for val, doc_id in weights:
        try:
            clean_str = (
                str(val)
                .lower()
                .replace("kg", "")
                .replace("kgs", "")
                .replace(",", "")
                .strip()
            )
            numeric_weights.append((float(clean_str), doc_id))
        except (ValueError, TypeError):
            pass

    if len(numeric_weights) < 2:
        record_check(
            "weight_comparison",
            "medium",
            "open",
            {"reason": "Requires at least 2 source documents with declared weight"},
        )
    else:
        max_wt = max(w[0] for w in numeric_weights)
        min_wt = min(w[0] for w in numeric_weights)
        discrepancy_kg = round(max_wt - min_wt, 2)

        # Any discrepancy > 1.0 kg is a high-severity mismatch requiring broker confirmation
        is_mismatch = discrepancy_kg > 1.0
        record_check(
            "weight_comparison",
            severity="high" if is_mismatch else "low",
            status="open" if is_mismatch else "pass",
            details={
                "recorded_weights": [w[0] for w in numeric_weights],
                "discrepancy_kg": discrepancy_kg,
                "note": (
                    "Mismatch detected across invoice / packing list / B/L"
                    if is_mismatch
                    else "Weights match"
                ),
            },
        )

    # 3. Mandatory Fields Completeness
    for req_field in REQUIRED_FIELDS:
        if not values.get(req_field):
            record_check(
                "required_field_completeness",
                severity="high",
                status="open",
                details={"missing_field": req_field},
            )

    # 4. Container Number Consistency
    containers = {x[0] for x in values.get("container_number", []) if x[0]}
    if len(containers) > 1:
        record_check(
            "container_consistency",
            severity="high",
            status="open",
            details={"conflicting_containers": sorted(list(containers))},
        )
    elif len(containers) == 1:
        record_check(
            "container_consistency",
            severity="low",
            status="pass",
            details={"container_number": list(containers)[0]},
        )

    db.add_all(results)
    db.commit()
    return results


def can_approve(db: Session, shipment_id: str) -> bool:
    """Manager can only approve if all high-severity cross-check discrepancies are resolved."""
    open_high_violations = (
        db.query(ValidationResult)
        .filter_by(shipment_id=shipment_id, status="open", severity="high")
        .count()
    )
    return open_high_violations == 0


def can_export(db: Session, shipment_id: str) -> bool:
    """Cannot export until approved and all low-confidence required fields are verified."""
    if not can_approve(db, shipment_id):
        return False
    unverified_low_conf = (
        db.query(ExtractedField)
        .filter(
            ExtractedField.shipment_id == shipment_id,
            ExtractedField.field_name.in_(REQUIRED_FIELDS),
            ExtractedField.confidence < 0.80,
            ExtractedField.verified == False,
        )
        .count()
    )
    return unverified_low_conf == 0
