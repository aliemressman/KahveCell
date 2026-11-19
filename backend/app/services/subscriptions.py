import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    UNLIMITED_CREDITS,
    Payment,
    Subscription,
    User,
)
from app.schemas.billing import PlanResponse, PlanType, SubscriptionResponse

PAYMENT_SUCCESS_CARD = "4242424242424242"
PAYMENT_DECLINED_CARD = "4000000000000002"


@dataclass(frozen=True)
class PlanDetails:
    name: str
    monthly_price: Decimal
    coffee_credits: int | None
    validity_days: int
    guest_credits: int
    priority: bool


PLAN_CATALOG = {
    PlanType.STARTER: PlanDetails(
        name="Starter",
        monthly_price=Decimal("89.99"),
        coffee_credits=10,
        validity_days=30,
        guest_credits=0,
        priority=False,
    ),
    PlanType.PREMIUM: PlanDetails(
        name="Premium",
        monthly_price=Decimal("149.99"),
        coffee_credits=20,
        validity_days=30,
        guest_credits=2,
        priority=False,
    ),
    PlanType.UNLIMITED: PlanDetails(
        name="Unlimited",
        monthly_price=Decimal("249.99"),
        coffee_credits=None,
        validity_days=30,
        guest_credits=5,
        priority=True,
    ),
}


def list_plans() -> list[PlanResponse]:
    return [
        PlanResponse(plan_type=plan_type, **details.__dict__)
        for plan_type, details in PLAN_CATALOG.items()
    ]


def get_active_subscription(session: Session, user_id: int) -> Subscription | None:
    return session.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "ACTIVE",
        )
        .order_by(Subscription.id.desc())
        .limit(1)
    )


def subscription_response(subscription: Subscription) -> SubscriptionResponse:
    plan_type = PlanType(subscription.plan_type)
    plan = PLAN_CATALOG[plan_type]
    credits = (
        None
        if plan.coffee_credits is None and subscription.status == "ACTIVE"
        else max(subscription.remaining_credits, 0)
    )
    return SubscriptionResponse(
        id=subscription.id,
        plan_type=plan_type,
        plan_name=plan.name,
        monthly_price=plan.monthly_price,
        remaining_credits=credits,
        status=subscription.status,
        started_at=subscription.started_at,
        expires_at=subscription.expires_at,
        guest_credits=plan.guest_credits,
        priority=plan.priority,
    )


def process_subscription_payment(
    session: Session,
    user: User,
    plan_type: PlanType,
    card_number: str,
    *,
    changing_plan: bool,
) -> tuple[Payment, Subscription | None]:
    active_subscription = get_active_subscription(session, user.id)
    if changing_plan and active_subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paket değiştirmek için aktif aboneliğiniz olmalı.",
        )
    if not changing_plan and active_subscription is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aktif aboneliğiniz var. Paket değiştirmek için PATCH kullanın.",
        )
    if (
        active_subscription is not None
        and active_subscription.plan_type == plan_type.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zaten bu pakete sahipsiniz.",
        )

    plan = PLAN_CATALOG[plan_type]
    card_digits = re.sub(r"\D", "", card_number)
    succeeded = card_digits == PAYMENT_SUCCESS_CARD
    if card_digits == PAYMENT_DECLINED_CARD:
        failure_reason = "Test kartı işlemi reddetti."
    elif succeeded:
        failure_reason = None
    else:
        failure_reason = "Kart simülasyon tarafından kabul edilmedi."

    now = datetime.now(timezone.utc)
    payment = Payment(
        transaction_id=str(uuid.uuid4()),
        user_id=user.id,
        plan_type=plan_type.value,
        amount=plan.monthly_price,
        status="SUCCEEDED" if succeeded else "FAILED",
        card_last_four=card_digits[-4:] if len(card_digits) >= 4 else None,
        failure_reason=failure_reason,
        created_at=now,
    )
    session.add(payment)

    if not succeeded:
        return payment, None

    remaining_credits = (
        UNLIMITED_CREDITS
        if plan.coffee_credits is None
        else plan.coffee_credits
    )
    if active_subscription is None:
        subscription = Subscription(
            user_id=user.id,
            plan_type=plan_type.value,
            remaining_credits=remaining_credits,
            status="ACTIVE",
            started_at=now,
            expires_at=now + timedelta(days=plan.validity_days),
        )
        session.add(subscription)
    else:
        subscription = active_subscription
        subscription.plan_type = plan_type.value
        subscription.remaining_credits = remaining_credits
        subscription.started_at = now
        subscription.expires_at = now + timedelta(days=plan.validity_days)

    session.flush()
    payment.subscription_id = subscription.id
    return payment, subscription
