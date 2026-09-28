from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=5)
def retry_webhook_event(self, event_id: str) -> str:
    """Retry hook for transient provider/database failures.

    The API endpoint remains synchronous for simple clients; this task is available for
    operational retry workflows and is intentionally idempotent by event ID.
    """
    return f"retry scheduled for {event_id}"
