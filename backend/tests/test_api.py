from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import Booking, Payment, WebhookEvent


def auth(client, email="user@example.com", password="PatientPass123"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_signup_validation_and_duplicate_email(client, seed):
    invalid = client.post(
        "/api/v1/auth/signup", json={"email": "not-an-email", "full_name": "A", "password": "short"}
    )
    assert invalid.status_code == 422
    duplicate = client.post(
        "/api/v1/auth/signup",
        json={"email": "user@example.com", "full_name": "Another User", "password": "Password123"},
    )
    assert duplicate.status_code == 409


def test_login_and_protected_access(client, seed):
    assert client.get("/api/v1/bookings").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "password": "wrong-password"}
        ).status_code
        == 401
    )
    headers = auth(client)
    assert client.get("/api/v1/auth/me", headers=headers).json()["email"] == "user@example.com"


def test_catalog_admin_authorization_and_pagination(client, seed):
    user_headers = auth(client)
    denied = client.post(
        "/api/v1/centres", headers=user_headers, json={"name": "Nope", "location": "Nowhere"}
    )
    assert denied.status_code == 403
    admin_headers = auth(client, "admin@example.com", "AdminPass123")
    created = client.post(
        "/api/v1/centres", headers=admin_headers, json={"name": "City Lab", "location": "Main Road"}
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/centres?page=1&page_size=1")
    assert listed.status_code == 200
    assert listed.json()["meta"]["page_size"] == 1


def test_booking_validates_future_time_ownership_and_price(client, seed):
    headers = auth(client)
    past = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={
            "test_id": seed["test"],
            "appointment_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
    )
    assert past.status_code == 422
    appointment = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    booking = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={"test_id": seed["test"], "appointment_at": appointment},
    )
    assert booking.status_code == 201
    assert booking.json()["amount"] == "550.00"
    duplicate = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={"test_id": seed["test"], "appointment_at": appointment},
    )
    assert duplicate.status_code == 409


def test_payment_success_is_idempotent(client, seed, db):
    headers = auth(client)
    appointment = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    booking = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={"test_id": seed["test"], "appointment_at": appointment},
    ).json()
    first = client.post(
        "/api/v1/payments/",
        headers=headers,
        json={
            "booking_id": booking["id"],
            "idempotency_key": "idem-success-1",
            "outcome": "SUCCESS",
        },
    )
    second = client.post(
        "/api/v1/payments/",
        headers=headers,
        json={
            "booking_id": booking["id"],
            "idempotency_key": "idem-success-1",
            "outcome": "FAILED",
        },
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["status"] == "SUCCESS"
    assert db.scalar(select(Booking).where(Booking.id == booking["id"])).status.value == "CONFIRMED"
    assert len(db.scalars(select(Payment)).all()) == 1


def test_failed_payment_and_invalid_booking(client, seed):
    headers = auth(client)
    missing = client.post(
        "/api/v1/payments/",
        headers=headers,
        json={"booking_id": "missing", "idempotency_key": "idem-missing", "outcome": "FAILED"},
    )
    assert missing.status_code == 404
    booking = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={
            "test_id": seed["test"],
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
        },
    ).json()
    payment = client.post(
        "/api/v1/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "idempotency_key": "idem-failed", "outcome": "FAILED"},
    )
    assert payment.json()["status"] == "FAILED"
    assert (
        client.get(f"/api/v1/bookings/{booking['id']}", headers=headers).json()["status"]
        == "FAILED"
    )


def test_cross_user_access_and_idempotency_key_conflict(client, seed):
    owner_headers = auth(client)
    other = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "other@example.com",
            "full_name": "Other Patient",
            "password": "OtherPass123",
        },
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    first = client.post(
        "/api/v1/bookings",
        headers=owner_headers,
        json={
            "test_id": seed["test"],
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=6)).isoformat(),
        },
    ).json()
    second = client.post(
        "/api/v1/bookings",
        headers=owner_headers,
        json={
            "test_id": seed["test"],
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        },
    ).json()
    assert client.get(f"/api/v1/bookings/{first['id']}", headers=other_headers).status_code == 404
    assert (
        client.post(
            "/api/v1/payments/",
            headers=owner_headers,
            json={
                "booking_id": first["id"],
                "idempotency_key": "shared-idempotency-key",
                "outcome": "SUCCESS",
            },
        ).status_code
        == 200
    )
    conflict = client.post(
        "/api/v1/payments/",
        headers=owner_headers,
        json={
            "booking_id": second["id"],
            "idempotency_key": "shared-idempotency-key",
            "outcome": "SUCCESS",
        },
    )
    assert conflict.status_code == 409


def test_cancellation_and_out_of_order_webhook_are_rejected(client, seed, db):
    headers = auth(client)
    booking = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={
            "test_id": seed["test"],
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(),
        },
    ).json()
    cancelled = client.post(f"/api/v1/bookings/{booking['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    payment_after_cancel = client.post(
        "/api/v1/payments/",
        headers=headers,
        json={
            "booking_id": booking["id"],
            "idempotency_key": "cancelled-payment",
            "outcome": "SUCCESS",
        },
    )
    assert payment_after_cancel.status_code == 409

    active = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={
            "test_id": seed["test"],
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=9)).isoformat(),
        },
    ).json()
    payment = client.post(
        "/api/v1/payments/",
        headers=headers,
        json={
            "booking_id": active["id"],
            "idempotency_key": "out-of-order-payment",
            "outcome": "SUCCESS",
        },
    ).json()
    out_of_order = client.post(
        "/api/v1/payments/webhook/",
        json={
            "event_id": "evt-out-of-order",
            "event_type": "payment.failed",
            "provider_payment_id": payment["provider_payment_id"],
            "booking_id": active["id"],
            "status": "FAILED",
        },
    )
    assert out_of_order.status_code == 409
    assert db.scalar(select(Booking).where(Booking.id == active["id"])).status.value == "CONFIRMED"


def test_webhook_is_idempotent_and_rejects_unknown_reference(client, seed, db):
    headers = auth(client)
    booking = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={
            "test_id": seed["test"],
            "appointment_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
    ).json()
    payment = client.post(
        "/api/v1/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "idempotency_key": "idem-hook", "outcome": "SUCCESS"},
    ).json()
    payload = {
        "event_id": "evt-duplicate-1",
        "event_type": "payment.succeeded",
        "provider_payment_id": payment["provider_payment_id"],
        "booking_id": booking["id"],
        "status": "SUCCESS",
    }
    first = client.post("/api/v1/payments/webhook/", json=payload)
    second = client.post("/api/v1/payments/webhook/", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert len(db.scalars(select(WebhookEvent)).all()) == 1
    unknown = client.post(
        "/api/v1/payments/webhook/",
        json={**payload, "event_id": "evt-unknown", "provider_payment_id": "missing-provider"},
    )
    assert unknown.status_code == 404


def test_webhook_signature_required_in_production(monkeypatch, client, seed):
    monkeypatch.setenv("EVE_ENVIRONMENT", "production")
    get_settings.cache_clear()
    # The route must reject unsigned events before attempting lookup.
    response = client.post(
        "/api/v1/payments/webhook/",
        json={
            "event_id": "evt-secure",
            "event_type": "payment.succeeded",
            "provider_payment_id": "provider",
            "booking_id": "booking",
            "status": "SUCCESS",
        },
    )
    assert response.status_code == 401
    monkeypatch.delenv("EVE_ENVIRONMENT", raising=False)
    get_settings.cache_clear()
