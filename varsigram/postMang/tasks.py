from celery import shared_task
from django.db.models import Sum
from django.conf import settings
import redis
from .models import RewardPointTransaction
from .leaderboard_utils import key_daily, key_weekly, key_monthly, key_alltime
from datetime import datetime
import os

_r = None
def _get_redis():
    global _r
    if _r is None:
        redis_url = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
        _r = redis.Redis.from_url(redis_url)
    return _r


@shared_task(bind=True)
def recompute_points_daily(self, date_iso: str):
    """Recompute the daily leaderboard for a specific date (YYYY-MM-DD)."""
    try:
        target = datetime.fromisoformat(date_iso).date()
    except Exception as e:
        raise ValueError(f"Invalid date_iso: {date_iso}")

    qs = RewardPointTransaction.objects.filter(created_at__date=target).values('post_author').annotate(score=Sum('points'))
    r = _get_redis()
    key = key_daily('points', target)
    pipe = r.pipeline()
    pipe.delete(key)
    if qs:
        mapping = {str(item['post_author']): float(item['score']) for item in qs}
        pipe.zadd(key, mapping)
    # Keep for 180 days
    pipe.expire(key, 60 * 60 * 24 * 180)
    pipe.execute()


@shared_task
def recompute_points_alltime():
    qs = RewardPointTransaction.objects.values('post_author').annotate(score=Sum('points'))
    r = _get_redis()
    key = key_alltime('points')
    pipe = r.pipeline()
    pipe.delete(key)
    if qs:
        mapping = {str(item['post_author']): float(item['score']) for item in qs}
        pipe.zadd(key, mapping)
    pipe.execute()
