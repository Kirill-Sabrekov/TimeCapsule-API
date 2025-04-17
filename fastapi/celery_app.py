from celery import Celery

app = Celery('time_capsule', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

import tasks