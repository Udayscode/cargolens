from pydantic import BaseModel, Field
from typing import Literal


class LoginRequest(BaseModel):
    email: str
    password: str


class ShipmentCreate(BaseModel):
    reference: str = Field(min_length=3)
    supplier_name: str
    supplier_country: str | None = None


class FieldUpdate(BaseModel):
    value: str
    reason: str | None = None


class Resolution(BaseModel):
    resolution: str


class ExtractionValue(BaseModel):
    value: str | None
    confidence: float = Field(ge=0, le=1)
    page: int | None = None


class ExtractionResponse(BaseModel):
    fields: dict[str, ExtractionValue]
