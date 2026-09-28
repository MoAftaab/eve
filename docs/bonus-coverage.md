# Bonus Coverage

| Bonus | Status | Evidence |
|---|---|---|
| Redis caching | Implemented | Read caching and invalidation in `backend/app/core/cache.py` and catalogue routes |
| Celery/background jobs | Implemented | `backend/app/tasks/` and Compose worker service |
| Docker/docker-compose | Implemented | Root `docker-compose.yml` and service Dockerfiles |
| Swagger/OpenAPI | Implemented | FastAPI-generated `/docs` and `/redoc` |
| Unit/integration tests | Implemented | Backend pytest suite and frontend Vitest suite |
| Structured logging | Implemented | JSON formatter and request middleware |
| Pagination | Implemented | Centres, tests, and bookings |
| Rate limiting | Implemented | Auth and payment request limiter |
| Webhook retry handling | Implemented | Celery retry task and event attempt fields |
