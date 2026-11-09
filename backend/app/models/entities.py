import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Float,
    Integer,
    Boolean,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.database import Base


def uid() -> str:
    return str(uuid.uuid4())


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class User(Timestamped, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="executive")


class Shipment(Timestamped, Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    reference: Mapped[str] = mapped_column(String, unique=True, index=True)
    supplier_name: Mapped[str] = mapped_column(String, index=True)
    supplier_country: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="review")
    approval_status: Mapped[str] = mapped_column(String, default="pending")

    documents: Mapped[list["Document"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )


class Document(Timestamped, Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    kind: Mapped[str] = mapped_column(String)  # invoice, packing_list, bill_of_lading
    filename: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    extraction_status: Mapped[str] = mapped_column(String, default="pending")

    shipment: Mapped[Shipment] = relationship(back_populates="documents")

    __table_args__ = (
        UniqueConstraint("shipment_id", "kind", name="uq_shipment_document_kind"),
    )


class ExtractedField(Timestamped, Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(String, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class LineItem(Timestamped, Base):
    __tablename__ = "line_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), index=True)
    description: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)


class ValidationResult(Timestamped, Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), index=True)
    rule: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)  # high, medium, low
    status: Mapped[str] = mapped_column(String)  # open, resolved, pass
    details: Mapped[str] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)


class FieldCorrection(Timestamped, Base):
    __tablename__ = "field_corrections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    field_id: Mapped[str] = mapped_column(ForeignKey("extracted_fields.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ApprovalRecord(Timestamped, Base):
    __tablename__ = "approval_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String)


class AuditLog(Timestamped, Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    shipment_id: Mapped[str | None] = mapped_column(
        ForeignKey("shipments.id"), nullable=True
    )
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String)
    detail: Mapped[str] = mapped_column(Text)


class ExportRecord(Timestamped, Base):
    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    format: Mapped[str] = mapped_column(String)
