from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import redis
from .models import RewardPointTransaction
from .leaderboard_utils import period_keys
from datetime import datetime
import os

# Create Redis client lazily
_redis = None

def get_redis_client():
    global _redis
    if _redis is None:
        redis_url = os.environ.get('CELERY_BROKER_URL', None)
        if not redis_url:
            # Fall back to local redis
            redis_url = 'redis://localhost:6379/0'
        _redis = redis.Redis.from_url(redis_url)
    return _redis


@receiver(post_save, sender=RewardPointTransaction)
def on_rewardpoint_created(sender, instance, created, **kwargs):
    """When a RewardPointTransaction is created, increment Redis leaderboard scores.

    Uses `post_author` as the beneficiary of points.
    """
    if not created:
        return

    try:
        user_id = str(instance.post_author_id)
        points = float(getattr(instance, 'points', 1))
    except Exception:
        return

    r = get_redis_client()
    keys = period_keys('points')
    pipe = r.pipeline()
    for key in keys:
        pipe.zincrby(key, points, user_id)
        # Optionally trim to keep only top N members (uncomment if desired)
        # pipe.zremrangebyrank(key, 0, -100001)  # keep top 100k
    # set TTL for period keys (daily/weekly/monthly) - keep 180 days
    pipe.expire(keys[1], 60 * 60 * 24 * 180)
    pipe.expire(keys[2], 60 * 60 * 24 * 180)
    pipe.expire(keys[3], 60 * 60 * 24 * 365)
    pipe.execute()
