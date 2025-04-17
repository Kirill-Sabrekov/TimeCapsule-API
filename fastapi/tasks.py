from celery_app import app
from celery.schedules import crontab
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.task
def send_open_notification(capsule_id: int, username: str):
    try:
        logger.info(f"Starting task: send_open_notification for capsule {capsule_id}")
        message = f"Notification: Capsule {capsule_id} is now open for {username} at {datetime.utcnow()}"
        logger.info(message)
        print(message)  # Дополнительно выводим в консоль
        return message
    except Exception as e:
        logger.error(f"Error in send_open_notification: {str(e)}")
        raise

@app.task
def check_capsules():
    from database import SessionLocal
    from models import Capsule, User
    logger.info("Starting periodic check of capsules")
    db = SessionLocal()
    try:
        capsules = db.query(Capsule).filter(Capsule.date_open <= datetime.utcnow()).all()
        logger.info(f"Found {len(capsules)} capsules to check")
        for capsule in capsules:
            user = db.query(User).filter(User.id == capsule.author_id).first()
            if user:
                logger.info(f"Periodic check: Capsule {capsule.id} is open for {user.username}")
                send_open_notification.delay(capsule.id, user.username)
    except Exception as e:
        logger.error(f"Error in check_capsules: {str(e)}")
        raise
    finally:
        db.close()

app.conf.beat_schedule = {
    'check-capsules-every-10-minutes': {
        'task': 'tasks.check_capsules',
        'schedule': crontab(minute='*/10'),
    },
}