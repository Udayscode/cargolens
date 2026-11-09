from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import Base, engine, SessionLocal
from app.models.entities import User, Shipment, Document, ExtractedField, LineItem
from app.core.security import hash_password
from app.api.routes import router

app = FastAPI(title="CargoLens Customs AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        # 1. Seed demo user accounts
        if not db.query(User).filter_by(email="manager@cargolens.demo").first():
            db.add_all(
                [
                    User(
                        email="manager@cargolens.demo",
                        password_hash=hash_password("demo-password"),
                        role="manager",
                    ),
                    User(
                        email="executive@cargolens.demo",
                        password_hash=hash_password("demo-password"),
                        role="executive",
                    ),
                ]
            )
            db.flush()

        # 2. Seed SHP-24811 (China LED shipment with 45kg invoice vs packing list discrepancy)
        if not db.query(Shipment).filter_by(reference="SHP-24811").first():
            s = Shipment(
                reference="SHP-24811",
                supplier_name="Company B (China)",
                supplier_country="China",
                status="review",
                approval_status="pending",
            )
            db.add(s)
            db.flush()

            docs = []
            for kind in ["invoice", "packing_list", "bill_of_lading"]:
                docs.append(
                    Document(
                        shipment_id=s.id,
                        kind=kind,
                        filename=f"synthetic_{kind}.pdf",
                        path=f"sample_data/synthetic_{kind}.pdf",
                        extraction_status="complete",
                    )
                )
            db.add_all(docs)
            db.flush()

            bykind = {d.kind: d for d in docs}
            # Line item: LED panel light 40W, 2400 @ 6.80 USD = 16320
            db.add(
                LineItem(
                    shipment_id=s.id,
                    description="LED panel light 40W",
                    quantity=2400,
                    unit_price=6.8,
                    amount=16320.0,
                )
            )

            db.add_all(
                [
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["invoice"].id,
                        field_name="invoice_number",
                        value="INV-B-8841",
                        confidence=0.98,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["invoice"].id,
                        field_name="invoice_date",
                        value="2026-10-14",
                        confidence=0.97,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["invoice"].id,
                        field_name="currency",
                        value="USD",
                        confidence=0.99,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["invoice"].id,
                        field_name="incoterm",
                        value="FOB Shanghai",
                        confidence=0.92,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["invoice"].id,
                        field_name="invoice_grand_total",
                        value="16320",
                        confidence=0.98,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["invoice"].id,
                        field_name="gross_weight",
                        value="3120",
                        confidence=0.96,
                        page=1,
                        verified=False,
                    ),
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["packing_list"].id,
                        field_name="gross_weight",
                        value="3165",
                        confidence=0.99,
                        page=1,
                        verified=False,
                    ),
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["packing_list"].id,
                        field_name="package_count",
                        value="120",
                        confidence=0.94,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s.id,
                        document_id=bykind["bill_of_lading"].id,
                        field_name="container_number",
                        value="MSCU1234567",
                        confidence=0.74,
                        page=1,
                        verified=False,
                    ),
                ]
            )

        # 3. Seed SHP-24812 (Sweden Ball Valve shipment from sample data)
        if not db.query(Shipment).filter_by(reference="SHP-24812").first():
            s2 = Shipment(
                reference="SHP-24812",
                supplier_name="Company C (Sweden)",
                supplier_country="Sweden",
                status="review",
                approval_status="pending",
            )
            db.add(s2)
            db.flush()

            doc_inv = Document(
                shipment_id=s2.id,
                kind="invoice",
                filename="synthetic_invoice_se.pdf",
                path="sample_data/synthetic_invoice.pdf",
                extraction_status="complete",
            )
            db.add(doc_inv)
            db.flush()

            # Line item: Steel ball valve DN50, 180 @ 42.50 EUR = 7650
            db.add(
                LineItem(
                    shipment_id=s2.id,
                    description="Steel ball valve DN50",
                    quantity=180,
                    unit_price=42.50,
                    amount=7650.0,
                )
            )

            db.add_all(
                [
                    ExtractedField(
                        shipment_id=s2.id,
                        document_id=doc_inv.id,
                        field_name="invoice_number",
                        value="INV-SE-9041",
                        confidence=0.98,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s2.id,
                        document_id=doc_inv.id,
                        field_name="invoice_date",
                        value="2026-10-18",
                        confidence=0.96,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s2.id,
                        document_id=doc_inv.id,
                        field_name="currency",
                        value="EUR",
                        confidence=0.99,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s2.id,
                        document_id=doc_inv.id,
                        field_name="incoterm",
                        value="CIF",
                        confidence=0.93,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s2.id,
                        document_id=doc_inv.id,
                        field_name="invoice_grand_total",
                        value="7650",
                        confidence=0.98,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s2.id,
                        document_id=doc_inv.id,
                        field_name="gross_weight",
                        value="1460",
                        confidence=0.95,
                        page=1,
                        verified=True,
                    ),
                    ExtractedField(
                        shipment_id=s2.id,
                        document_id=doc_inv.id,
                        field_name="package_count",
                        value="45",
                        confidence=0.92,
                        page=1,
                        verified=True,
                    ),
                ]
            )

        db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "CargoLens Customs API"}
