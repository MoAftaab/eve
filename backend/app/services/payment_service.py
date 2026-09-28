import hashlib
import hmac
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Booking,
    BookingStatus,
    Payment,
    PaymentStatus,
    User,
    WebhookEvent,
    WebhookStatus,
)


def apply_payment_status(db: Session, payment: Payment, new_status: PaymentStatus) -> Payment:
    booking = db.scalar(select(Booking).where(Booking.id == payment.booking_id).with_for_update())
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if payment.status == new_status:
        return payment
    if payment.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Payment is already finalized"
        )
    if booking.status in {BookingStatus.CANCELLED, BookingStatus.CONFIRMED, BookingStatus.FAILED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Booking is already finalized"
        )
    payment.status = new_status
    booking.status = (
        BookingStatus.CONFIRMED if new_status == PaymentStatus.SUCCESS else BookingStatus.FAILED
    )
    return payment


def process_payment(
    db: Session, user: User, booking_id: str, idempotency_key: str, outcome: PaymentStatus | None
) -> Payment:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    existing = db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
    if existing:
        if existing.booking_id != booking_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Idempotency key already used"
            )
        return existing
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking cannot be paid")
    payment = Payment(
        booking_id=booking.id,
        idempotency_key=idempotency_key,
        provider_payment_id=f"sim_{uuid4().hex}",
        amount=booking.amount,
        currency=booking.currency,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.flush()
    selected = outcome or PaymentStatus.SUCCESS
    apply_payment_status(db, payment, selected)
    db.commit()
    db.refresh(payment)
    return payment


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    expected = hmac.new(
        get_settings().webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


def process_webhook(db: Session, payload: dict) -> tuple[WebhookEvent, bool]:
    event_id = payload["event_id"]
    existing_event = db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
    if existing_event:
        return existing_event, True
    event = WebhookEvent(
        event_id=event_id, event_type=payload["event_type"], payload=payload, attempts=1
    )
    db.add(event)
    payment = db.scalar(
        select(Payment)
        .where(Payment.provider_payment_id == payload["provider_payment_id"])
        .with_for_update()
    )
    if not payment or payment.booking_id != payload["booking_id"]:
        event.status = WebhookStatus.FAILED
        event.last_error = "Payment or booking reference not found"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment reference not found"
        )
    try:
        apply_payment_status(db, payment, PaymentStatus(payload["status"]))
        event.status = WebhookStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return event, False
    except HTTPException as exc:
        event.status = WebhookStatus.FAILED
        event.last_error = str(exc.detail)
        db.commit()
        raise
