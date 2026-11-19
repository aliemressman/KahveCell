from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.shops import (
    ProductResponse,
    ShopDetailResponse,
    ShopListItemResponse,
)
from app.services.shops import get_shop_detail, get_shop_menu, list_shops

router = APIRouter(prefix="/api/v1/shops", tags=["Dükkânlar"])


@router.get("", response_model=list[ShopListItemResponse])
def get_shops(
    search: str | None = Query(default=None, max_length=120),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=100),
    session: Session = Depends(get_db),
) -> list[ShopListItemResponse]:
    if (lat is None) != (lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Yakınlık araması için lat ve lng birlikte gönderilmelidir.",
        )
    if radius_km is not None and lat is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="radius_km yalnızca lat ve lng ile birlikte kullanılabilir.",
        )

    effective_radius = radius_km if radius_km is not None else 10.0
    return list_shops(
        session,
        search=search,
        latitude=lat,
        longitude=lng,
        radius_km=effective_radius if lat is not None else None,
    )


@router.get("/{shop_id}/menu", response_model=list[ProductResponse])
def get_menu(
    shop_id: int,
    session: Session = Depends(get_db),
) -> list[ProductResponse]:
    return get_shop_menu(session, shop_id)


@router.get("/{shop_id}", response_model=ShopDetailResponse)
def get_shop(
    shop_id: int,
    session: Session = Depends(get_db),
) -> ShopDetailResponse:
    return get_shop_detail(session, shop_id)
