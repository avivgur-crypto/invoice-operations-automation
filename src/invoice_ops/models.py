"""Domain models independent of any API or spreadsheet provider."""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentType(StrEnum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CREDIT_NOTE = "credit_note"
    REFUND = "refund"


class Invoice(BaseModel):
    """Canonical invoice representation used throughout the pipeline."""

    model_config = ConfigDict(frozen=True)

    external_id: str = Field(min_length=1)
    document_date: date
    vendor: str = Field(min_length=1)
    amount: Decimal
    tax: Decimal = Decimal("0")
    currency: str = Field(min_length=3, max_length=3)
    category: str = ""
    business_unit: str = ""
    document_number: str = ""
    document_type: DocumentType = DocumentType.INVOICE
    source_updated_at: datetime | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("amount", "tax")
    @classmethod
    def normalize_money(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    def signed_amount(self) -> Decimal:
        if self.document_type in {DocumentType.CREDIT_NOTE, DocumentType.REFUND}:
            return -abs(self.amount)
        return self.amount

    def to_sheet_row(self, status: str = "", review_reason: str = "") -> list[str]:
        updated = self.source_updated_at or datetime.now(timezone.utc)
        return [
            self.document_date.strftime("%B %Y"),
            self.document_date.isoformat(),
            self.vendor,
            str(self.signed_amount()),
            str(self.tax),
            self.document_type.value,
            self.currency,
            self.category,
            self.business_unit,
            self.document_number,
            self.external_id,
            updated.isoformat(),
            status,
            review_reason,
        ]
