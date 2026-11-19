from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import Payment, Subscription, User
from app.schemas.billing import (
    PaymentHistoryItem,
    PaymentResponse,
    PlanResponse,
    PurchaseInput,
    SubscriptionResponse,
)
from app.services.subscriptions import (
    get_active_subscription,
    list_plans,
    process_subscription_payment,
    subscription_response,
)

subscription_router = APIRouter(
    prefix="/api/v1/subscriptions",
    tags=["Abonelikler"],
)
payment_router = APIRouter(
    prefix="/api/v1/payments",
    tags=["Paycell Ödeme Simülasyonu"],
)


def _payment_response(
    payment: Payment,
    subscription: Subscription | None,
) -> PaymentResponse:
    succeeded = payment.status == "SUCCEEDED"
    return PaymentResponse(
        success=succeeded,
        transaction_id=payment.transaction_id,
        amount=payment.amount,
        status=payment.status,
        message="Ödeme başarılı." if succeeded else payment.failure_reason or "Ödeme başarısız.",
        created_at=payment.created_at,
        subscription=(
            subscription_response(subscription)
            if subscription is not None
            else None
        ),
    )


def _charge_and_update(
    payload: PurchaseInput,
    user: User,
    session: Session,
    *,
    changing_plan: bool,
) -> PaymentResponse:
    payment, subscription = process_subscription_payment(
        session,
        user,
        payload.plan_type,
        payload.card_number,
        changing_plan=changing_plan,
    )
    session.commit()
    return _payment_response(payment, subscription)


@subscription_router.get("/plans", response_model=list[PlanResponse])
def get_plans() -> list[PlanResponse]:
    return list_plans()


@subscription_router.post(
    "",
    response_model=PaymentResponse,
    summary="Öde ve abonelik başlat",
)
def create_subscription(
    payload: PurchaseInput,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PaymentResponse:
    return _charge_and_update(payload, user, session, changing_plan=False)


@subscription_router.get("/me", response_model=SubscriptionResponse)
def get_my_subscription(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SubscriptionResponse:
    subscription = get_active_subscription(session, user.id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aktif aboneliğiniz bulunmuyor.",
        )
    return subscription_response(subscription)


@subscription_router.patch(
    "/me",
    response_model=PaymentResponse,
    summary="Öde ve paketi değiştir",
)
def change_my_subscription(
    payload: PurchaseInput,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PaymentResponse:
    return _charge_and_update(payload, user, session, changing_plan=True)


@subscription_router.delete(
    "/me",
    response_model=SubscriptionResponse,
    summary="Aboneliği hemen iptal et",
)
def cancel_my_subscription(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SubscriptionResponse:
    subscription = get_active_subscription(session, user.id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İptal edilecek aktif aboneliğiniz bulunmuyor.",
        )
    subscription.status = "CANCELLED"
    subscription.remaining_credits = 0
    subscription.expires_at = datetime.now(timezone.utc)
    session.commit()
    return subscription_response(subscription)


@payment_router.post(
    "/process",
    response_model=PaymentResponse,
    summary="Paycell ödeme simülasyonu ile paket satın al",
)
def process_payment(
    payload: PurchaseInput,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PaymentResponse:
    return _charge_and_update(payload, user, session, changing_plan=False)


@payment_router.get("/history", response_model=list[PaymentHistoryItem])
def get_payment_history(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[PaymentHistoryItem]:
    payments = session.scalars(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
    ).all()
    return [
        PaymentHistoryItem(
            transaction_id=payment.transaction_id,
            plan_type=payment.plan_type,
            amount=payment.amount,
            status=payment.status,
            card_last_four=payment.card_last_four,
            failure_reason=payment.failure_reason,
            created_at=payment.created_at,
        )
        for payment in payments
    ]
