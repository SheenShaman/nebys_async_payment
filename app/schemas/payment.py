from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, AnyHttpUrl

from app.utils.enums import Currency, PaymentStatus


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: UUID
    amount: Decimal
    currency: Currency
    description: str
    meta_data: dict
    status: PaymentStatus
    idempotency_key: str
    webhook_url: AnyHttpUrl
    created_at: datetime
    processed_at: datetime | None


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: Currency
    description: str = Field(min_length=1, max_length=5000)
    metadata: dict = Field(default_factory=dict)
    webhook_url: AnyHttpUrl


class PaymentAccepted(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime
