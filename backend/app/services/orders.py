import base64
import hashlib
import hmac
import io
import json
from datetime import datetime, timezone
from uuid import UUID

import qrcode
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tokens import JWT_SECRET_KEY
from app.models import (
    UNLIMITED_CREDITS,
    Order,
    OrderStatus,
    Product,
    Shop,
    User,
)
from app.schemas.orders import (
    OrderCreateInput,
    OrderDetailResponse,
    OrderSummaryResponse,
    QRCodePayload,
)
from app.services.subscriptions import get_active_subscription

QR_SIGNING_KEY = hmac.new(
    JWT_SECRET_KEY.encode("ascii"),
    b"kahvecell/order-qr/v1",
    hashlib.sha256,
).digest()

NEXT_ORDER_STATUS = {
    OrderStatus.PENDING: OrderStatus.ACCEPTED,
    OrderStatus.ACCEPTED: OrderStatus.PREPARING,
    OrderStatus.PREPARING: OrderStatus.READY,
}


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _utc_datetime(value).isoformat(timespec="microseconds").replace(
        "+00:00",
        "Z",
    )


def _qr_fields(
    order_id: str,
    user_id: str,
    shop_id: str,
    created_at: datetime,
) -> dict[str, str]:
    return {
        "order_id": order_id,
        "user_id": user_id,
        "shop_id": shop_id,
        "created_at": _timestamp(created_at),
    }


def _sign_qr_fields(fields: dict[str, str]) -> str:
    message = json.dumps(
        fields,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(QR_SIGNING_KEY, message, hashlib.sha256).hexdigest()


def _qr_payload(order: Order, user: User, shop: Shop) -> QRCodePayload:
    fields = _qr_fields(
        order.public_id,
        user.public_id,
        shop.public_id,
        order.created_at,
    )
    signature = _sign_qr_fields(fields)
    if order.qr_signature != signature:
        order.qr_signature = signature
    return QRCodePayload(
        order_id=UUID(fields["order_id"]),
        user_id=UUID(fields["user_id"]),
        shop_id=UUID(fields["shop_id"]),
        created_at=_utc_datetime(order.created_at),
        signature=signature,
    )


def _qr_image(payload: QRCodePayload) -> str:
    encoded_payload = json.dumps(
        {
            "order_id": str(payload.order_id),
            "user_id": str(payload.user_id),
            "shop_id": str(payload.shop_id),
            "created_at": _timestamp(payload.created_at),
            "signature": payload.signature,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    image = qrcode.make(encoded_payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def order_summary_response(
    order: Order,
    user: User,
    shop: Shop,
    product: Product,
) -> OrderSummaryResponse:
    return OrderSummaryResponse(
        order_id=UUID(order.public_id),
        user_id=UUID(user.public_id),
        shop_id=UUID(shop.public_id),
        shop_name=shop.name,
        product_id=product.id,
        product_name=product.name,
        customizations=order.customizations,
        status=OrderStatus(order.status),
        created_at=_utc_datetime(order.created_at),
    )


def order_detail_response(
    order: Order,
    user: User,
    shop: Shop,
    product: Product,
) -> OrderDetailResponse:
    qr_payload = _qr_payload(order, user, shop)
    summary = order_summary_response(order, user, shop, product)
    return OrderDetailResponse(
        **summary.model_dump(),
        qr_code=qr_payload,
        qr_code_image=_qr_image(qr_payload),
    )


def qr_payload_is_valid(
    payload: QRCodePayload,
    order: Order,
    user: User,
    shop: Shop,
) -> bool:
    expected_fields = _qr_fields(
        order.public_id,
        user.public_id,
        shop.public_id,
        order.created_at,
    )
    submitted_fields = _qr_fields(
        str(payload.order_id),
        str(payload.user_id),
        str(payload.shop_id),
        payload.created_at,
    )
    if submitted_fields != expected_fields or order.qr_signature is None:
        return False
    expected_signature = _sign_qr_fields(expected_fields)
    return hmac.compare_digest(
        expected_signature,
        payload.signature,
    ) and hmac.compare_digest(order.qr_signature, payload.signature)


def _get_order_context(
    session: Session,
    order_public_id: UUID,
) -> tuple[Order, User, Shop, Product]:
    result = session.execute(
        select(Order, User, Shop, Product)
        .join(User, Order.user_id == User.id)
        .join(Shop, Order.shop_id == Shop.id)
        .join(Product, Order.product_id == Product.id)
        .where(Order.public_id == str(order_public_id))
    ).first()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sipariş bulunamadı.",
        )
    return result


def create_order(
    session: Session,
    user: User,
    payload: OrderCreateInput,
) -> OrderDetailResponse:
    now = datetime.now(timezone.utc)
    subscription = get_active_subscription(session, user.id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sipariş verebilmek için aktif aboneliğiniz olmalı.",
        )
    if subscription.expires_at is not None and _utc_datetime(subscription.expires_at) <= now:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aboneliğinizin süresi dolmuş. Yeni paket satın alın.",
        )
    if (
        subscription.remaining_credits != UNLIMITED_CREDITS
        and subscription.remaining_credits <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kahve hakkınız bitmiş. Yeni paket satın alın.",
        )

    shop = session.get(Shop, payload.shop_id)
    if shop is None or not shop.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dükkân bulunamadı veya şu anda hizmet vermiyor.",
        )
    product = session.get(Product, payload.product_id)
    if product is None or product.shop_id != shop.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seçilen ürün bu dükkânın menüsünde bulunamadı.",
        )
    if not product.is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seçilen ürün şu anda mevcut değil.",
        )

    order = Order(
        user_id=user.id,
        shop_id=shop.id,
        product_id=product.id,
        customizations=payload.model_dump(
            include={"size", "sugar_level", "milk_type", "extra_shot"}
        ),
        status=OrderStatus.PENDING,
        created_at=now,
    )
    if subscription.remaining_credits != UNLIMITED_CREDITS:
        subscription.remaining_credits -= 1
    session.add(order)
    session.flush()
    return order_detail_response(order, user, shop, product)


def get_order_detail(
    session: Session,
    order_public_id: UUID,
) -> tuple[Order, User, Shop, Product]:
    return _get_order_context(session, order_public_id)


def list_customer_orders(
    session: Session,
    user_id: int,
) -> list[OrderSummaryResponse]:
    rows = session.execute(
        select(Order, User, Shop, Product)
        .join(User, Order.user_id == User.id)
        .join(Shop, Order.shop_id == Shop.id)
        .join(Product, Order.product_id == Product.id)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()
    return [
        order_summary_response(order, user, shop, product)
        for order, user, shop, product in rows
    ]


def list_shop_owner_orders(
    session: Session,
    owner_id: int,
) -> list[OrderSummaryResponse]:
    rows = session.execute(
        select(Order, User, Shop, Product)
        .join(User, Order.user_id == User.id)
        .join(Shop, Order.shop_id == Shop.id)
        .join(Product, Order.product_id == Product.id)
        .where(Shop.owner_id == owner_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()
    return [
        order_summary_response(order, user, shop, product)
        for order, user, shop, product in rows
    ]


def next_order_status(current_status: OrderStatus) -> OrderStatus:
    next_status = NEXT_ORDER_STATUS.get(current_status)
    if next_status is None:
        if current_status == OrderStatus.READY:
            detail = "Teslim edildi durumuna geçiş için QR kodu doğrulayın."
        else:
            detail = "Bu siparişin durumu artık değiştirilemez."
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
    return next_status
