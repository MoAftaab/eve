# Requirement -> Implementation -> Verification

| Requirement | Implemented | Tested | Evidence |
|---|---:|---:|---|
| Signup, login, JWT authentication | Yes | Yes | `backend/app/api/auth.py`, `backend/tests/test_api.py` |
| Request validation | Yes | Yes | Pydantic schemas and validation tests |
| Centre/test management and retrieval | Yes | Yes | `backend/app/api/catalog.py` |
| Booking fields and server-calculated amount | Yes | Yes | `backend/app/db/models.py`, booking tests |
| PENDING/CONFIRMED/FAILED/CANCELLED states | Yes | Yes | `backend/app/services/payment_service.py` |
| Simulated SUCCESS/FAILED payments | Yes | Yes | `backend/app/api/payments.py` |
| Idempotent payment webhook | Yes | Yes | Unique event/provider keys and duplicate webhook test |
| Invalid IDs, failed payments, unauthorized access | Yes | Yes | Negative API tests |
| PostgreSQL schema and migrations | Yes | Yes | `backend/migrations/versions/` |
| Docker and Compose | Yes | Build-ready | `Dockerfile`, `docker-compose.yml` |
| OpenAPI documentation | Yes | Build-ready | FastAPI `/docs` and `/redoc` |
| Redis cache hooks | Yes | Fallback tested by API suite | `backend/app/core/cache.py` |
| Background retry task | Yes | Import/build-ready | `backend/app/tasks/webhook_tasks.py` |
| Structured logging | Yes | Build-ready | `backend/app/main.py` |
| Pagination | Yes | Yes | Catalogue pagination test |
| Rate limiting | Yes | Build-ready | `backend/app/core/rate_limit.py` |
| Responsive frontend | Yes | Build | `frontend/src/App.tsx`, `frontend/src/styles.css` |
| Frontend API-client tests | Yes | Yes | `frontend/src/api.test.ts` |
