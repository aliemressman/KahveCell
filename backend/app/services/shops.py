import unicodedata
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, Shop
from app.schemas.shops import (
    ProductResponse,
    ShopDetailResponse,
    ShopListItemResponse,
)

EARTH_RADIUS_KM = 6371.0088


def _normalize_search(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return without_marks.replace("ı", "i")


def haversine_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def list_shops(
    session: Session,
    *,
    search: str | None,
    latitude: float | None,
    longitude: float | None,
    radius_km: float | None,
) -> list[ShopListItemResponse]:
    query = search.strip() if search else ""
    normalized_query = _normalize_search(query)
    shops = list(session.scalars(select(Shop)).all())
    if normalized_query:
        shops = [
            shop
            for shop in shops
            if normalized_query in _normalize_search(shop.name)
            or normalized_query in _normalize_search(shop.address)
        ]
    results: list[tuple[ShopListItemResponse, float | None]] = []
    for shop in shops:
        distance = None
        if latitude is not None and longitude is not None:
            distance = haversine_distance_km(
                latitude,
                longitude,
                shop.latitude,
                shop.longitude,
            )
            if radius_km is not None and distance > radius_km:
                continue

        results.append(
            (
                ShopListItemResponse(
                    id=shop.id,
                    name=shop.name,
                    address=shop.address,
                    latitude=shop.latitude,
                    longitude=shop.longitude,
                    rating=shop.rating,
                    is_active=shop.is_active,
                    distance_km=round(distance, 2) if distance is not None else None,
                ),
                distance,
            )
        )

    if latitude is not None and longitude is not None:
        results.sort(key=lambda result: (result[1] is None, result[1] or 0))
    else:
        results.sort(key=lambda result: result[0].name.casefold())
    return [result[0] for result in results]


def get_shop_detail(session: Session, shop_id: int) -> ShopDetailResponse:
    shop = session.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dükkân bulunamadı.",
        )

    products = session.scalars(
        select(Product)
        .where(Product.shop_id == shop.id)
        .order_by(Product.name)
    ).all()
    return ShopDetailResponse(
        id=shop.id,
        name=shop.name,
        address=shop.address,
        latitude=shop.latitude,
        longitude=shop.longitude,
        opening_hours=shop.opening_hours,
        rating=shop.rating,
        is_active=shop.is_active,
        products=[
            ProductResponse(
                id=product.id,
                name=product.name,
                category=product.category,
                price=product.price,
                is_available=product.is_available,
            )
            for product in products
        ],
    )


def get_shop_menu(session: Session, shop_id: int) -> list[ProductResponse]:
    if session.get(Shop, shop_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dükkân bulunamadı.",
        )
    products = session.scalars(
        select(Product)
        .where(Product.shop_id == shop_id)
        .order_by(Product.name)
    ).all()
    return [
        ProductResponse(
            id=product.id,
            name=product.name,
            category=product.category,
            price=product.price,
            is_available=product.is_available,
        )
        for product in products
    ]
