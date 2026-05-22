from celery import shared_task

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 3})
def test_task(self):
    return "Redis + Celery fully working"
