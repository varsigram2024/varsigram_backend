from celery import shared_task
from django.db.models import Sum
from django.conf import settings
import redis
from .models import RewardPointTransaction
from .leaderboard_utils import key_daily, key_weekly, key_monthly, key_alltime
from datetime import datetime, timedelta, timezone as dt_timezone
import os
import logging
from postMang.apps import get_firestore_db

logger = logging.getLogger(__name__)

_r = None
def _get_redis():
    global _r
    if _r is None:
        redis_url = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
        _r = redis.Redis.from_url(redis_url)
    return _r


@shared_task(bind=True)
def fanout_post_to_followers(self, author_user_id: int, post_id: str, score_ts: float = None):
    """Push a newly created post ID into followers' Redis feeds (push-on-write).

    This task is safe to retry and will not raise on errors (logs instead).
    """
    try:
        r = _get_redis()
    except Exception:
        logger.exception('Failed to get redis client for fanout')
        return

    try:
        from .models import Student, Organization, Follow
        from django.contrib.contenttypes.models import ContentType
        student_ct = ContentType.objects.get(model='student')
        org_ct = ContentType.objects.get(model='organization')

        follower_user_ids = []
        # find followers of author's profile
        try:
            user_id = int(author_user_id)
        except Exception:
            user_id = None

        # Try student profile
        student_qs = Student.objects.filter(user_id=author_user_id)
        if student_qs.exists():
            profile = student_qs.first()
            follows = Follow.objects.filter(
                followee_content_type=student_ct,
                followee_object_id=profile.id
            )
        else:
            org_qs = Organization.objects.filter(user_id=author_user_id)
            if org_qs.exists():
                profile = org_qs.first()
                follows = Follow.objects.filter(
                    followee_content_type=org_ct,
                    followee_object_id=profile.id
                )
            else:
                follows = Follow.objects.none()

        student_follow_ids = [f.follower_object_id for f in follows.filter(follower_content_type=student_ct)]
        org_follow_ids = [f.follower_object_id for f in follows.filter(follower_content_type=org_ct)]
        if student_follow_ids:
            follower_user_ids.extend(list(Student.objects.filter(id__in=student_follow_ids).values_list('user_id', flat=True)))
        if org_follow_ids:
            follower_user_ids.extend(list(Organization.objects.filter(id__in=org_follow_ids).values_list('user_id', flat=True)))

        # include the author themselves
        try:
            follower_user_ids.append(int(author_user_id))
        except Exception:
            pass

        score = score_ts or datetime.now(dt_timezone.utc).timestamp()
        MAX_FEED_ITEMS = getattr(settings, 'REDIS_FEED_MAX_ITEMS', 500)
        # Chunking to avoid huge single Celery tasks when an author has many followers
        CHUNK_SIZE = getattr(settings, 'FANOUT_CHUNK_SIZE', 5000)

        all_uids = list({int(u) for u in follower_user_ids if u is not None})
        try:
            if len(all_uids) <= CHUNK_SIZE:
                # Small enough to do in this task
                pipe = r.pipeline()
                for uid in all_uids:
                    key = f"feed:{uid}"
                    pipe.zadd(key, {str(post_id): score})
                    pipe.zremrangebyrank(key, 0, -MAX_FEED_ITEMS-1)
                pipe.execute()
            else:
                # Dispatch chunked subtasks to handle fanout in parallel
                chunks = [all_uids[i:i+CHUNK_SIZE] for i in range(0, len(all_uids), CHUNK_SIZE)]
                for chunk in chunks:
                    try:
                        fanout_post_chunk.delay(chunk, post_id, score)
                    except Exception:
                        # Fallback to local execution for this chunk
                        fa = fanout_post_chunk
                        fa(chunk, post_id, score)
                try:
                    # Metric: count dispatched chunks
                    r.incr('metrics:fanout:dispatched_chunks')
                except Exception:
                    pass
        except Exception:
            logger.exception('Error while performing chunked fanout')
    except Exception:
        logger.exception('fanout_post_to_followers failed')



@shared_task(bind=True)
def fanout_post_chunk(self, follower_user_ids, post_id: str, score_ts: float = None):
    """Subtask to write a post id into a chunk of follower feeds."""
    try:
        r = _get_redis()
    except Exception:
        logger.exception('Failed to get redis client for fanout chunk')
        return

    score = score_ts or datetime.now(dt_timezone.utc).timestamp()
    MAX_FEED_ITEMS = getattr(settings, 'REDIS_FEED_MAX_ITEMS', 500)
    try:
        pipe = r.pipeline()
        for uid in set(follower_user_ids):
            try:
                key = f"feed:{int(uid)}"
            except Exception:
                key = f"feed:{uid}"
            pipe.zadd(key, {str(post_id): score})
            pipe.zremrangebyrank(key, 0, -MAX_FEED_ITEMS-1)
        pipe.execute()
        try:
            r.incr('metrics:fanout:chunks')
        except Exception:
            pass
    except Exception:
        logger.exception('fanout_post_chunk failed')


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


@shared_task
def recompute_posts_alltime(populate_redis: bool = True):
    """Recompute the all-time leaderboard for post counts from Firestore.

    If `populate_redis` is True, writes the sorted set to Redis key `leaderboard:posts:alltime`.
    """
    try:
        db = get_firestore_db()
    except Exception as e:
        logger.exception('Failed to get Firestore client')
        return

    counts = {}
    try:
        posts_ref = db.collection('posts')
        for doc in posts_ref.stream():
            data = doc.to_dict()
            author_id = data.get('author_id')
            if not author_id:
                continue
            counts[str(author_id)] = counts.get(str(author_id), 0) + 1
    except Exception:
        logger.exception('Failed scanning Firestore posts for post counts')
        return

    # Optionally populate Redis
    if populate_redis:
        try:
            r = _get_redis()
            key = 'leaderboard:posts:alltime'
            pipe = r.pipeline()
            pipe.delete(key)
            if counts:
                # zadd expects mapping of member:score
                mapping = {uid: int(cnt) for uid, cnt in counts.items()}
                pipe.zadd(key, mapping)
            pipe.execute()
        except Exception:
            logger.exception('Failed to write posts leaderboard to Redis')

    logger.info(f"Recomputed posts all-time leaderboard: {len(counts)} authors")