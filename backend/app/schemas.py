from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.db.models import BookingStatus, PaymentStatus, Role, WebhookStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(ORMModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse


class CentreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    location: str = Field(min_length=2, max_length=240)


class CentreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    location: str | None = Field(default=None, min_length=2, max_length=240)
    is_active: bool | None = None


class CentreResponse(ORMModel):
    id: str
    name: str
    location: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TestCreate(BaseModel):
    centre_id: str
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class TestUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    is_active: bool | None = None


class TestResponse(ORMModel):
    id: str
    centre_id: str
    name: str
    description: str
    price: Decimal
    currency: str
    is_active: bool
    created_at: datetime


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class CentrePage(BaseModel):
    items: list[CentreResponse]
    meta: PageMeta


class TestPage(BaseModel):
    items: list[TestResponse]
    meta: PageMeta


class BookingCreate(BaseModel):
    test_id: str
    appointment_at: datetime

    @field_validator("appointment_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("appointment_at must include a timezone")
        return value


class BookingResponse(ORMModel):
    id: str
    user_id: str
    test_id: str
    centre_id: str
    appointment_at: datetime
    amount: Decimal
    currency: str
    status: BookingStatus
    created_at: datetime
    updated_at: datetime


class BookingPage(BaseModel):
    items: list[BookingResponse]
    meta: PageMeta


class PaymentCreate(BaseModel):
    booking_id: str
    idempotency_key: str = Field(min_length=8, max_length=100)
    outcome: PaymentStatus | None = None


class PaymentResponse(ORMModel):
    id: str
    booking_id: str
    idempotency_key: str
    provider_payment_id: str | None
    amount: Decimal
    currency: str
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime


class WebhookRequest(BaseModel):
    event_id: str = Field(min_length=8, max_length=120)
    event_type: Literal["payment.succeeded", "payment.failed"]
    provider_payment_id: str = Field(min_length=3, max_length=100)
    booking_id: str
    status: Literal["SUCCESS", "FAILED"]


class WebhookResponse(BaseModel):
    event_id: str
    status: WebhookStatus
    duplicate: bool = False
