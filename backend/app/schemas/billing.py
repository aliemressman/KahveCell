from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class PlanType(str, Enum):
    STARTER = "STARTER"
    PREMIUM = "PREMIUM"
    UNLIMITED = "UNLIMITED"


class PlanResponse(BaseModel):
    plan_type: PlanType
    name: str
    monthly_price: Decimal
    coffee_credits: int | None
    validity_days: int
    guest_credits: int
    priority: bool


class PurchaseInput(BaseModel):
    plan_type: PlanType
    card_number: str = Field(
        min_length=16,
        max_length=23,
        description="Simülasyon kartı: 4242-4242-4242-4242 başarılı; 4000-0000-0000-0002 başarısız.",
        examples=["4242-4242-4242-4242"],
    )


class SubscriptionResponse(BaseModel):
    id: int
    plan_type: PlanType
    plan_name: str
    monthly_price: Decimal
    remaining_credits: int | None
    status: str
    started_at: datetime
    expires_at: datetime | None
    guest_credits: int
    priority: bool


class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str
    amount: Decimal
    currency: str = "TRY"
    status: str
    message: str
    created_at: datetime
    subscription: SubscriptionResponse | None


class PaymentHistoryItem(BaseModel):
    transaction_id: str
    plan_type: PlanType
    amount: Decimal
    status: str
    card_last_four: str | None
    failure_reason: str | None
    created_at: datetime
