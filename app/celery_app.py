import os

try:
    from celery import Celery
except ImportError:  # pragma: no cover - fallback for environments without Celery installed
    class Celery:  # minimal stub to keep app importable during tests
        def __init__(self, *args, **kwargs):
            self.conf = {}

        def autodiscover_tasks(self, *args, **kwargs):
            return None

        def send_task(self, *args, **kwargs):
            raise RuntimeError("Celery is not installed. Please install celery to run background jobs.")

celery = Celery(
    "devops_logs",
    broker=os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL")),
    backend=os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL")),
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    broker_transport_options={"visibility_timeout": 3600},
)

if os.getenv("REDIS_URL", "").startswith("rediss://"):
    celery.conf.broker_use_ssl = {"ssl_cert_reqs": "none"}
    celery.conf.result_backend_transport_options = {"retry_on_timeout": True}

# auto-discover tasks in app.tasks
celery.autodiscover_tasks(["app"])
