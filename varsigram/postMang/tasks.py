from celery import shared_task
from django.db.models import Sum
from django.conf import settings
import redis
from .models import RewardPointTransaction
from .leaderboard_utils import key_daily, key_weekly, key_monthly, key_alltime
from datetime import datetime, timedelta, timezone as dt_timezone
import os
import logging

logger = logging.getLogger(__name__)

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

    qs = RewardPointTransaction.objects.filter(
        created_at__date=target
    ).values('post_author').annotate(score=Sum('points'))
    
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
    
    logger.info(f"Recomputed daily leaderboard for {target}: {len(qs)} users")


@shared_task
def recompute_points_alltime():
    """Recompute the all-time leaderboard."""
    qs = RewardPointTransaction.objects.values('post_author').annotate(score=Sum('points'))
    r = _get_redis()
    key = key_alltime('points')
    pipe = r.pipeline()
    pipe.delete(key)
    if qs:
        mapping = {str(item['post_author']): float(item['score']) for item in qs}
        pipe.zadd(key, mapping)
    pipe.execute()
    
    logger.info(f"Recomputed all-time leaderboard: {len(qs)} users")


@shared_task(bind=True)
def recompute_points_weekly(self, date_iso: str = None):
    """
    Recompute the weekly leaderboard for the ISO week that contains date_iso (YYYY-MM-DD).
    If date_iso is None, uses the current week.
    
    Example: date_iso='2025-11-11' will recompute leaderboard for the ISO week containing 2025-11-11.
    """
    try:
        if date_iso:
            target = datetime.fromisoformat(date_iso).date()
        else:
            # Use current date if none provided
            target = datetime.now(dt_timezone.utc).date()
    except Exception as e:
        raise ValueError(f"Invalid date_iso: {date_iso}")

    # Determine ISO week start (Monday) and end (Sunday)
    iso_year, iso_week, _ = target.isocalendar()
    
    # Python 3.8+ supports fromisocalendar
    try:
        week_start = datetime.fromisocalendar(iso_year, iso_week, 1).date()
    except Exception:
        # Fallback: compute approximate start
        week_start = target - timedelta(days=target.weekday())

    week_end = week_start + timedelta(days=6)

    # Query transactions for this week
    qs = RewardPointTransaction.objects.filter(
        created_at__date__gte=week_start,
        created_at__date__lte=week_end,
    ).values('post_author').annotate(score=Sum('points'))

    r = _get_redis()
    key = key_weekly('points', week_start)
    pipe = r.pipeline()
    pipe.delete(key)  # Clear the old week's data
    if qs:
        mapping = {str(item['post_author']): float(item['score']) for item in qs}
        pipe.zadd(key, mapping)
    # Keep weekly snapshots for 180 days
    pipe.expire(key, 60 * 60 * 24 * 180)
    pipe.execute()
    
    logger.info(f"Recomputed weekly leaderboard for week {iso_year}-W{iso_week:02d} ({week_start} to {week_end}): {len(qs)} users")


@shared_task(bind=True)
def recompute_points_monthly(self, date_iso: str = None):
    """Recompute the monthly leaderboard for the month containing date_iso."""
    try:
        if date_iso:
            target = datetime.fromisoformat(date_iso).date()
        else:
            target = datetime.now(dt_timezone.utc).date()
    except Exception as e:
        raise ValueError(f"Invalid date_iso: {date_iso}")

    # Get first and last day of the month
    month_start = target.replace(day=1)
    if target.month == 12:
        month_end = target.replace(year=target.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = target.replace(month=target.month + 1, day=1) - timedelta(days=1)

    qs = RewardPointTransaction.objects.filter(
        created_at__date__gte=month_start,
        created_at__date__lte=month_end,
    ).values('post_author').annotate(score=Sum('points'))

    r = _get_redis()
    key = key_monthly('points', target)
    pipe = r.pipeline()
    pipe.delete(key)
    if qs:
        mapping = {str(item['post_author']): float(item['score']) for item in qs}
        pipe.zadd(key, mapping)
    pipe.expire(key, 60 * 60 * 24 * 180)
    pipe.execute()
    
    logger.info(f"Recomputed monthly leaderboard for {target.year}-{target.month:02d}: {len(qs)} users")