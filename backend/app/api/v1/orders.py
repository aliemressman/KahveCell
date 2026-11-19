from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models import OrderStatus, User, UserRole
from app.schemas.orders import (
    OrderCreateInput,
    OrderDetailResponse,
    OrderStatusUpdateInput,
    OrderSummaryResponse,
    QRVerificationInput,
    QRVerificationResponse,
)
from app.services.orders import (
    create_order,
    get_order_detail,
    list_customer_orders,
    list_shop_owner_orders,
    next_order_status,
    order_detail_response,
    order_summary_response,
    qr_payload_is_valid,
)

router = APIRouter(prefix="/api/v1/orders", tags=["Siparişler"])


@router.post(
    "",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_order(
    payload: OrderCreateInput,
    user: User = Depends(require_roles(UserRole.CUSTOMER)),
    session: Session = Depends(get_db),
) -> OrderDetailResponse:
    response = create_order(session, user, payload)
    session.commit()
    return response


@router.get("/mine", response_model=list[OrderSummaryResponse])
def get_my_orders(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[OrderSummaryResponse]:
    return list_customer_orders(session, user.id)


@router.get("/shop", response_model=list[OrderSummaryResponse])
def get_shop_orders(
    user: User = Depends(require_roles(UserRole.SHOP_OWNER)),
    session: Session = Depends(get_db),
) -> list[OrderSummaryResponse]:
    return list_shop_owner_orders(session, user.id)


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(
    order_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> OrderDetailResponse:
    order, customer, shop, product = get_order_detail(session, order_id)
    if user.role != UserRole.ADMIN and order.user_id != user.id and shop.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu siparişi görüntüleme yetkiniz yok.",
        )
    response = order_detail_response(order, customer, shop, product)
    session.commit()
    return response


@router.patch("/{order_id}/status", response_model=OrderSummaryResponse)
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdateInput,
    user: User = Depends(require_roles(UserRole.SHOP_OWNER)),
    session: Session = Depends(get_db),
) -> OrderSummaryResponse:
    order, customer, shop, product = get_order_detail(session, order_id)
    if shop.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yalnızca kendi dükkânınızdaki siparişleri güncelleyebilirsiniz.",
        )

    expected_status = next_order_status(OrderStatus(order.status))
    if payload.status != expected_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bu sipariş için sıradaki durum {expected_status.value}.",
        )
    order.status = expected_status
    session.commit()
    return order_summary_response(order, customer, shop, product)


@router.post("/verify-qr", response_model=QRVerificationResponse)
def verify_order_qr(
    payload: QRVerificationInput,
    user: User = Depends(require_roles(UserRole.SHOP_OWNER)),
    session: Session = Depends(get_db),
) -> QRVerificationResponse:
    order, customer, shop, product = get_order_detail(
        session,
        payload.qr_code.order_id,
    )
    if shop.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu sipariş sizin dükkânınızda verilmemiş.",
        )
    if not qr_payload_is_valid(payload.qr_code, order, customer, shop):
        return QRVerificationResponse(
            valid=False,
            message="QR kod geçersiz veya değiştirilmiş.",
            order=order_summary_response(order, customer, shop, product),
        )
    if order.status != OrderStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="QR kod yalnızca sipariş hazır olduğunda teslim için kullanılabilir.",
        )

    order.status = OrderStatus.DELIVERED
    session.commit()
    return QRVerificationResponse(
        valid=True,
        message="QR kod doğrulandı; sipariş teslim edildi.",
        order=order_summary_response(order, customer, shop, product),
    )
