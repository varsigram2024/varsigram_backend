from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'varsigram.settings')

app = Celery('varsigram')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure Celery Beat schedule for leaderboard management
app.conf.beat_schedule = {
    # Reset weekly leaderboard every Monday at 00:01 AM UTC
    'reset-weekly-leaderboard': {
        'task': 'postMang.tasks.recompute_points_weekly',
        'schedule': crontab(hour=0, minute=1, day_of_week=1),  # Every Monday at 00:01
        'args': (None,),  # Will use current date
    },
    
    # Recompute all-time leaderboard daily at 2:00 AM UTC
    # This ensures consistency even if Redis has issues
    'sync-alltime-leaderboard': {
        'task': 'postMang.tasks.recompute_points_alltime',
        'schedule': crontab(hour=2, minute=0),  # Every day at 2:00 AM
    },
    
    # Optional: Recompute monthly leaderboard on the 1st of each month
    'reset-monthly-leaderboard': {
        'task': 'postMang.tasks.recompute_points_monthly',
        'schedule': crontab(hour=0, minute=5, day_of_month=1),  # 1st day of month at 00:05
        'args': (None,),
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')