from app.services.validation import validate_shipment, can_export
from app.models.entities import Shipment, ExtractedField, LineItem, ValidationResult


def make(db):
    s = Shipment(reference="T-1", supplier_name="Test")
    db.add(s)
    db.flush()
    return s


def test_invoice_arithmetic_failure(db):
    s = make(db)
    db.add(
        LineItem(
            shipment_id=s.id, description="x", quantity=2, unit_price=10, amount=20
        )
    )
    db.add(
        ExtractedField(
            shipment_id=s.id, field_name="invoice_grand_total", value="19", confidence=1
        )
    )
    db.commit()
    validate_shipment(db, s)
    assert (
        db.query(ValidationResult)
        .filter_by(rule="invoice_arithmetic", status="open")
        .count()
        == 1
    )


def test_weight_discrepancy(db):
    s = make(db)
    db.add_all(
        [
            ExtractedField(
                shipment_id=s.id, field_name="gross_weight", value="3120", confidence=1
            ),
            ExtractedField(
                shipment_id=s.id, field_name="gross_weight", value="3165", confidence=1
            ),
        ]
    )
    db.commit()
    validate_shipment(db, s)
    assert (
        "45.0"
        in db.query(ValidationResult)
        .filter_by(rule="weight_comparison")
        .first()
        .details
    )


def test_low_confidence_blocks_export(db):
    s = make(db)
    db.add(
        ExtractedField(
            shipment_id=s.id, field_name="invoice_number", value="x", confidence=0.4
        )
    )
    db.commit()
    assert not can_export(db, s.id)
