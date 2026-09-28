# Database migrations

The application creates tables on first startup for a zero-friction local demo. Alembic is included for production migration workflows; run migrations from the `backend` directory after configuring `DATABASE_URL`.

The schema is intentionally relational: users own bookings, tests belong to centres, bookings snapshot price/currency, payments are one-to-one with bookings, and webhook event IDs are unique for idempotency.
