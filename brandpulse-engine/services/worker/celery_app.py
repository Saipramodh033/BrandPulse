"""
Celery Application Configuration
================================
Configures the Celery worker for asynchronous task processing.
"""

import os
from celery import Celery

# Redis connection string
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

app = Celery(
    'brandpulse_worker',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['services.worker.tasks.ideation_task']
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    broker_connection_retry_on_startup=True
)

# Celery Beat Schedule
app.conf.beat_schedule = {
    'queue-due-companies': {
        'task': 'services.worker.tasks.ideation_task.queue_generation_tasks',
        'schedule': 60.0,  # every 1 minute
    }
}
