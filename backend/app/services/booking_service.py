from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Booking, BookingStatus, DiagnosticCentre, DiagnosticTest, User


def create_booking(db: Session, user: User, test_id: str, appointment_at: datetime) -> Booking:
    if appointment_at.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Appointment must be in the future",
        )
    test = db.scalar(
        select(DiagnosticTest).where(
            DiagnosticTest.id == test_id, DiagnosticTest.is_active.is_(True)
        )
    )
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic test not found"
        )
    centre = db.scalar(
        select(DiagnosticCentre).where(
            DiagnosticCentre.id == test.centre_id, DiagnosticCentre.is_active.is_(True)
        )
    )
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Diagnostic centre is unavailable"
        )
    duplicate = db.scalar(
        select(Booking).where(
            Booking.user_id == user.id,
            Booking.test_id == test.id,
            Booking.appointment_at == appointment_at,
            Booking.status != BookingStatus.CANCELLED,
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A matching booking already exists"
        )
    booking = Booking(
        user_id=user.id,
        test_id=test.id,
        centre_id=centre.id,
        appointment_at=appointment_at,
        amount=test.price,
        currency=test.currency,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
