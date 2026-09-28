from celery import Celery

from app.core.config import get_settings

celery_app = Celery(
    "eve_healthcare", broker=get_settings().redis_url, backend=get_settings().redis_url
)
celery_app.conf.update(
    task_serializer="json", accept_content=["json"], result_serializer="json", task_acks_late=True
)
