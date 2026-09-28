from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import db_session, get_current_user
from app.core.config import get_settings
from app.core.rate_limit import enforce_rate_limit
from app.db.models import User
from app.schemas import PaymentCreate, PaymentResponse, WebhookRequest, WebhookResponse
from app.services.payment_service import process_payment, process_webhook, verify_webhook_signature

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentResponse)
def create_payment(
    payload: PaymentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    enforce_rate_limit(f"payment:{user.id}", get_settings().rate_limit_per_minute)
    return process_payment(db, user, payload.booking_id, payload.idempotency_key, payload.outcome)


@router.post("/webhook/", response_model=WebhookResponse)
async def webhook(
    request: Request,
    payload: WebhookRequest,
    x_webhook_signature: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_webhook_signature):
        # Local development clients may omit the signature; production requires it.
        from app.core.config import get_settings

        if get_settings().environment == "production":
            from fastapi import HTTPException

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
            )
    event, duplicate = process_webhook(db, payload.model_dump())
    return WebhookResponse(event_id=event.event_id, status=event.status, duplicate=duplicate)
