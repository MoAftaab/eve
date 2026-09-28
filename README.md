# EVE Healthcare

Production-oriented diagnostic test booking service with JWT authentication, PostgreSQL persistence, simulated payments, idempotent payment webhooks, and a responsive React frontend.

## What is included

- FastAPI REST API under `/api/v1`
- PostgreSQL schema with Alembic migration
- JWT signup/login and role-based authorization
- Diagnostic-centre and test catalogue management
- Authenticated bookings with price snapshots and state transitions
- Deterministic simulated SUCCESS/FAILED payments
- Idempotent payment webhook processing
- Pagination, Redis cache hooks, rate limiting, structured logs, and Celery retry task
- React/Vite frontend with responsive layouts, loading/error/empty/success states
- Unit/integration tests for authentication, permissions, validation, pricing, booking conflicts, payments, webhook idempotency, and security

## Run locally with Docker

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

Seed local demo data from another terminal:

```bash
docker compose exec api python scripts/seed_demo.py
```

Demo accounts:

- Patient: `patient@example.com` / `PatientPass123`
- Admin: `admin@example.com` / `AdminPass123`

Do not use those credentials outside local development.

## Run without Docker

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -e ".[dev]"
copy ..\.env.example .env   # Windows
python scripts/seed_demo.py
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

If the browser shows `Unable to reach the API`, make sure the backend is running on port 8000. The frontend derives the API host from the current browser host, so both `localhost:5173` and `127.0.0.1:5173` are supported.

For native execution, set `EVE_DATABASE_URL` to a reachable PostgreSQL database or use the default SQLite development database.

## API overview

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/signup` | Create patient account | Public |
| POST | `/api/v1/auth/login` | Obtain JWT | Public |
| GET | `/api/v1/auth/me` | Current user | JWT |
| GET | `/api/v1/centres` | Paginated active centres | Public |
| POST/PATCH/DELETE | `/api/v1/centres` | Manage centres | Admin |
| GET | `/api/v1/tests` | Paginated tests | Public |
| POST/PATCH/DELETE | `/api/v1/tests` | Manage tests | Admin |
| POST | `/api/v1/bookings` | Create booking | JWT |
| GET | `/api/v1/bookings` | List own bookings | JWT |
| POST | `/api/v1/bookings/{id}/cancel` | Cancel own pending booking | JWT |
| POST | `/api/v1/payments/` | Simulate payment | JWT |
| POST | `/api/v1/payments/webhook/` | Apply provider event | Provider signature in production |

Example booking:

```json
{
  "test_id": "<test-id>",
  "appointment_at": "2030-05-12T10:30:00+05:30"
}
```

Example payment:

```json
{
  "booking_id": "<booking-id>",
  "idempotency_key": "booking-payment-001",
  "outcome": "SUCCESS"
}
```

The server calculates the amount from the test catalogue. Clients cannot override prices.

## How to test the APIs manually

Open Swagger at `http://127.0.0.1:8000/docs`.

1. Execute `POST /api/v1/auth/signup` or `POST /api/v1/auth/login`.
2. Copy the returned `access_token`.
3. Click **Authorize** in Swagger and paste the token.
4. Execute `GET /api/v1/tests` and copy a test ID.
5. Execute `POST /api/v1/bookings` with a future timezone-aware appointment.
6. Execute `POST /api/v1/payments/` with an idempotency key and `SUCCESS` or `FAILED` outcome.
7. Repeat the exact payment request. It must return the same payment instead of creating another one.
8. Repeat a webhook event. The second response must contain `duplicate: true`.

Expected negative checks:

- `GET /api/v1/bookings` without a token -> `401`
- Patient attempting `POST /api/v1/centres` -> `403`
- Invalid request body -> `422`
- Unknown booking ID -> `404`
- Reusing a payment idempotency key for another booking -> `409`
- Applying an incompatible payment state transition -> `409`

For local demo data, run `python -m scripts.seed_demo` from `backend` first. The frontend uses the same flow: signup/login, browse tests, book, simulate payment success/failure, view bookings, and cancel pending bookings. Admin catalogue management is intentionally API-only because it was not part of the PDF’s required frontend.

## Verifying Redis and rate limiting

Redis is used by `app/core/cache.py` for catalogue caching and by `app/core/rate_limit.py` for distributed request counters. Start Redis with Docker, then run the API with `EVE_REDIS_URL=redis://localhost:6379/0`.

After requesting `/api/v1/centres` twice, inspect Redis with:

```bash
redis-cli --scan --pattern "centres:*"
redis-cli --scan --pattern "eve:rate-limit:*"
```

For an easy rate-limit test, restart the API with `EVE_RATE_LIMIT_PER_MINUTE=3`, make four login requests from the same client, and expect the fourth request to return `429`. If Redis is unavailable, the code falls back to an in-memory limiter for local development.

## Database design

- `users`: patient/admin identity and password hash
- `diagnostic_centres`: centre name, location, active flag
- `diagnostic_tests`: centre-owned tests and current price
- `bookings`: user/test/centre relationship, appointment, price snapshot, status
- `payments`: one idempotent logical payment per booking
- `webhook_events`: unique provider event IDs, processing status, attempts, and error details

Indexes cover email, catalogue relationships, booking owner/status/date, payment idempotency keys, provider IDs, and webhook event IDs. Booking and payment updates are handled transactionally.

## Tests and quality checks

```bash
cd backend
python -m pytest
uvx ruff check app tests
uvx ruff format --check app tests

cd ../frontend
npm test
npm run build
```

## Assumptions

- Public users can read active centres/tests; only admins can mutate the catalogue.
- Signup always creates a patient account.
- The PDF does not define capacity or operating hours, so the service validates future appointments and prevents duplicate user/test/time bookings.
- Currency is stored explicitly and defaults to the configurable `EVE_DEFAULT_CURRENCY`.
- A booking has one logical payment; repeated idempotency keys return the original payment.
- Webhook signatures are optional in development and required in production.

## Production improvements

- Use a managed PostgreSQL/Redis service and a secrets manager.
- Replace the local in-memory rate-limit fallback with Redis-only enforcement in multi-instance deployments.
- Add centre operating hours, capacity/slot inventory, refresh-token rotation, email notifications, audit trails, and distributed tracing.
- Run the frontend behind a TLS reverse proxy with a restrictive Content Security Policy.
