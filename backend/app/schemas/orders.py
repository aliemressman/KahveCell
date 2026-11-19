from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import OrderStatus


class OrderCreateInput(BaseModel):
    shop_id: int
    product_id: int
    size: Literal["S", "M", "L"] = "M"
    sugar_level: int = Field(default=0, ge=0, le=5)
    milk_type: Literal[
        "none",
        "whole",
        "lactose_free",
        "oat",
        "almond",
        "soy",
    ] = "whole"
    extra_shot: bool = False


class QRCodePayload(BaseModel):
    order_id: UUID
    user_id: UUID
    shop_id: UUID
    created_at: datetime
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")


class OrderStatusUpdateInput(BaseModel):
    status: OrderStatus


class OrderSummaryResponse(BaseModel):
    order_id: UUID
    user_id: UUID
    shop_id: UUID
    shop_name: str
    product_id: int
    product_name: str
    customizations: dict[str, Any]
    status: OrderStatus
    created_at: datetime


class OrderDetailResponse(OrderSummaryResponse):
    qr_code: QRCodePayload
    qr_code_image: str


class QRVerificationInput(BaseModel):
    qr_code: QRCodePayload


class QRVerificationResponse(BaseModel):
    valid: bool
    message: str
    order: OrderSummaryResponse
