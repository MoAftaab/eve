from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import db_session, get_current_user
from app.api.utils import not_found, page_query, pagination_params
from app.db.models import Booking, BookingStatus, User
from app.schemas import BookingCreate, BookingPage, BookingResponse
from app.services.booking_service import create_booking

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: BookingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    return create_booking(db, user, payload.test_id, payload.appointment_at)


@router.get("", response_model=BookingPage)
def list_mine(
    page_data: tuple[int, int] = Depends(pagination_params),
    booking_status: BookingStatus | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    page, page_size = page_data
    query = select(Booking).where(Booking.user_id == user.id).order_by(Booking.created_at.desc())
    if booking_status:
        query = query.where(Booking.status == booking_status)
    items, meta = page_query(db, query, page, page_size)
    return {"items": items, "meta": meta}


@router.get("/{booking_id}", response_model=BookingResponse)
def get_one(
    booking_id: str, user: User = Depends(get_current_user), db: Session = Depends(db_session)
):
    booking = db.get(Booking, booking_id)
    if not booking or booking.user_id != user.id:
        raise not_found("Booking")
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel(
    booking_id: str, user: User = Depends(get_current_user), db: Session = Depends(db_session)
):
    booking = db.get(Booking, booking_id)
    if not booking or booking.user_id != user.id:
        raise not_found("Booking")
    if booking.status in {BookingStatus.CONFIRMED, BookingStatus.FAILED, BookingStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Booking cannot be cancelled"
        )
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking
