from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    price: Decimal
    is_available: bool


class ShopListItemResponse(BaseModel):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    rating: float
    is_active: bool
    distance_km: float | None


class ShopDetailResponse(BaseModel):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    opening_hours: dict[str, Any]
    rating: float
    is_active: bool
    products: list[ProductResponse]
