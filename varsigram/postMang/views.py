import redis
from rest_framework import generics, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import firestore
from postMang.apps import get_firestore_db  # Import the Firestore client from the app config
from .models import (User, Follow, Student, Organization, RewardPointTransaction)
from .serializer import FirestoreCommentSerializer, FirestoreLikeOutputSerializer, FirestorePostCreateSerializer, FirestorePostUpdateSerializer, FirestorePostOutputSerializer, GenericFollowSerializer, RewardPointSerializer, PrivatePointsProfileSerializer
from .utils import get_exclusive_org_user_ids, get_student_user_ids
import logging
import random
import hashlib
import os
import uuid
from datetime import datetime, timezone, timedelta
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Sum
from django.conf import settings
from .leaderboard_utils import key_weekly, key_monthly, key_alltime
from rest_framework_simplejwt.authentication import JWTAuthentication
from notifications_app.tasks import notify_all_users_new_post
from rest_framework.mixins import CreateModelMixin
from notifications_app.utils import send_push_notification
from .signals import get_redis_client
from .tasks import recompute_posts_alltime

# TTLs and keys
REDIS_AUTHOR_TTL = getattr(settings, 'REDIS_AUTHOR_TTL', 60 * 60 * 24)  # 24 hours
REDIS_LIKES_TTL = getattr(settings, 'REDIS_LIKES_TTL', 60 * 60 * 24 * 7)  # 7 days


def batch_has_liked(user_id, post_ids):
    """Return a set of post_ids that `user_id` has liked by checking Redis sets.

    Falls back to empty set if Redis unavailable.
    """
    try:
        r = get_redis_client()
        key = f"user:likes:{user_id}"
        pipe = r.pipeline()
        for pid in post_ids:
            pipe.sismember(key, str(pid))
        results = pipe.execute()
        liked = {str(pid) for pid, res in zip(post_ids, results) if res}
        return liked
    except Exception:
        return set()


def hydrate_authors_map(author_ids):
    """Fetch author metadata from Redis hash cache, fall back to DB for misses, and populate cache."""
    authors_map = {}
    if not author_ids:
        return authors_map
    try:
        r = get_redis_client()
        pipe = r.pipeline()
        keys = [f"user:meta:{aid}" for aid in author_ids]
        for k in keys:
            pipe.hgetall(k)
        cached = pipe.execute()
        misses = []
        for aid, data in zip(author_ids, cached):
            if data:
                # decode bytes to strings if necessary
                if isinstance(data, dict):
                    decoded = {}
                    for kk, vv in data.items():
                        k = kk.decode() if isinstance(kk, bytes) else kk
                        v = vv.decode() if isinstance(vv, bytes) else vv
                        decoded[k] = v
                    authors_map[str(aid)] = {
                        'id': int(aid),
                        'email': decoded.get('email'),
                        'profile_pic_url': decoded.get('profile_pic_url'),
                        'name': decoded.get('name'),
                        'display_name_slug': decoded.get('display_name_slug'),
                        'is_verified': decoded.get('is_verified') == 'True',
                        'exclusive': decoded.get('exclusive') == 'True',
                        'faculty': decoded.get('faculty'),
                        'department': decoded.get('department'),
                    }
            else:
                misses.append(aid)

        if misses:
            # Query DB for misses
            authors_from_db = User.objects.filter(id__in=misses)
            pipe = r.pipeline()
            for author in authors_from_db:
                author_name = None
                display_name_slug = None
                exclusive = False
                author_faculty = None
                author_department = None
                if hasattr(author, 'student'):
                    author_name = author.student.name
                    display_name_slug = getattr(author.student, 'display_name_slug', None)
                    author_faculty = getattr(author.student, 'faculty', None)
                    author_department = getattr(author.student, 'department', None)
                elif hasattr(author, 'organization'):
                    author_name = author.organization.organization_name
                    display_name_slug = getattr(author.organization, 'display_name_slug', None)
                    exclusive = getattr(author.organization, 'exclusive', False)

                authors_map[str(author.id)] = {
                    "id": author.id,
                    "email": author.email,
                    "profile_pic_url": author.profile_pic_url,
                    "name": author_name,
                    "display_name_slug": display_name_slug,
                    "is_verified": author.is_verified,
                    "exclusive": exclusive,
                    "faculty": author_faculty,
                    "department": author_department,
                }
                # write-back to redis
                meta_key = f"user:meta:{author.id}"
                pipe.hset(meta_key, mapping={
                    'email': author.email or '',
                    'profile_pic_url': author.profile_pic_url or '',
                    'name': author_name or '',
                    'display_name_slug': display_name_slug or '',
                    'is_verified': str(author.is_verified),
                    'exclusive': str(exclusive),
                    'faculty': author_faculty or '',
                    'department': author_department or '',
                })
                pipe.expire(meta_key, REDIS_AUTHOR_TTL)
            try:
                pipe.execute()
            except Exception:
                pass
    except Exception:
        # On any redis issue, fallback to DB-only hydration
        authors_from_db = User.objects.filter(id__in=author_ids)
        for author in authors_from_db:
            author_name = None
            display_name_slug = None
            exclusive = False
            author_faculty = None
            author_department = None
            if hasattr(author, 'student'):
                author_name = author.student.name
                display_name_slug = getattr(author.student, 'display_name_slug', None)
                author_faculty = getattr(author.student, 'faculty', None)
                author_department = getattr(author.student, 'department', None)
            elif hasattr(author, 'organization'):
                author_name = author.organization.organization_name
                display_name_slug = getattr(author.organization, 'display_name_slug', None)
                exclusive = getattr(author.organization, 'exclusive', False)

            authors_map[str(author.id)] = {
                "id": author.id,
                "email": author.email,
                "profile_pic_url": author.profile_pic_url,
                "name": author_name,
                "display_name_slug": display_name_slug,
                "is_verified": author.is_verified,
                "exclusive": exclusive,
                "faculty": author_faculty,
                "department": author_department,
            }

    return authors_map


def get_session_rng(session_id):
    """Return a local Random instance seeded by session_id (safe for concurrency)."""
    try:
        return random.Random(str(session_id))
    except Exception:
        return random.Random()


def session_rank_score(seed, post_id, timestamp=None, engagement_score=0.0, recency_weight=0.7, engagement_weight=0.15):
    """Deterministic per-post pseudo-random score combined with optional recency bias.

    - `seed`: session identifier
    - `post_id`: unique post id
    - `timestamp`: datetime (UTC) or None
    - `engagement_score`: numeric score based on views and comments
    - `recency_weight`: 0..1 weight for recency (higher favors newer posts)
    - `engagement_weight`: 0..1 weight for engagement
    Returns a float score where larger is better.
    """
    try:
        key = f"{seed}:{post_id}"
        h = hashlib.sha256(key.encode()).hexdigest()
        rand = int(h, 16) / float(2 ** 256)
    except Exception:
        rand = random.random()

    recency = 0.0
    if timestamp:
        try:
            now = datetime.now(timezone.utc)
            # If timestamp is a Firestore timestamp object, try to coerce
            if hasattr(timestamp, 'timestamp') and callable(getattr(timestamp, 'timestamp')):
                ts = timestamp
            else:
                ts = timestamp
            age = max(0.0, (now - ts).total_seconds())
            # Normalize recency: newer -> closer to 1. Use 7-day scale by default.
            recency = 1.0 / (1.0 + (age / (7 * 24 * 3600)))
        except Exception:
            recency = 0.0

    # Normalize engagement: smooth curve where 0 -> 0, 1000 -> ~0.66, etc.
    norm_engagement = 1.0 - (1.0 / (1.0 + (engagement_score / 500.0)))

    random_weight = max(0.0, 1.0 - recency_weight - engagement_weight)

    return (recency_weight * recency) + (engagement_weight * norm_engagement) + (random_weight * rand)


def session_sort_posts(posts, session_id, recency_weight=0.7, engagement_weight=0.15, timestamp_key='timestamp'):
    """Sort posts in-place by deterministic session score (descending).

    Each post should be a dict with an `id` and optionally `timestamp`.
    """
    if not posts:
        return posts
    seed = str(session_id)
    scores = {}
    for p in posts:
        pid = str(p.get('id'))
        ts = p.get(timestamp_key)
        
        # Calculate raw engagement score (1 view = 1, 1 comment = 10)
        views = p.get('view_count', 0)
        comments = p.get('comment_count', 0)
        raw_engagement = float(views) + (float(comments) * 10.0)

        scores[pid] = session_rank_score(
            seed, pid, ts, 
            engagement_score=raw_engagement, 
            recency_weight=recency_weight,
            engagement_weight=engagement_weight
        )

    posts.sort(key=lambda x: scores.get(str(x.get('id')), 0.0), reverse=True)
    return posts

# Initialize Firestore client
db = get_firestore_db()  # Get the Firestore client from the app config

class IsVerified(permissions.BasePermission):
    """
    Allows access only to verified users.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_verified", False))



class GenericFollowView(generics.CreateAPIView):
    serializer_class = GenericFollowSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

class GenericUnfollowView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        follower_type = request.data.get('follower_type')
        follower_user_id = request.data.get('follower_id')  # This is user.id from frontend
        followee_type = request.data.get('followee_type')
        followee_user_id = request.data.get('followee_id')  # This is user.id from frontend

        if not all([follower_type, follower_user_id, followee_type, followee_user_id]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        follower_content_type = ContentType.objects.get(model=follower_type.lower())
        followee_content_type = ContentType.objects.get(model=followee_type.lower())

        # Resolve profile IDs from user IDs
        try:
            if follower_type.lower() == 'student':
                follower_profile_id = Student.objects.get(user_id=follower_user_id).id
            elif follower_type.lower() == 'organization':
                follower_profile_id = Organization.objects.get(user_id=follower_user_id).id
            else:
                return Response({"error": "Invalid follower_type."}, status=status.HTTP_400_BAD_REQUEST)

            if followee_type.lower() == 'student':
                followee_profile_id = Student.objects.get(user_id=followee_user_id).id
            elif followee_type.lower() == 'organization':
                followee_profile_id = Organization.objects.get(user_id=followee_user_id).id
            else:
                return Response({"error": "Invalid followee_type."}, status=status.HTTP_400_BAD_REQUEST)
        except (Student.DoesNotExist, Organization.DoesNotExist):
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            follow = Follow.objects.get(
                follower_content_type=follower_content_type,
                follower_object_id=follower_profile_id,
                followee_content_type=followee_content_type,
                followee_object_id=followee_profile_id,
            )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Follow.DoesNotExist:
            return Response({"error": "Follow relationship does not exist."}, status=status.HTTP_404_NOT_FOUND)

class ListFollowersView(generics.ListAPIView):
    serializer_class = GenericFollowSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        followee_type = self.request.query_params.get('followee_type')
        followee_user_id = self.request.query_params.get('followee_id')  # This is user.id from frontend
        if not followee_type or not followee_user_id:
            return Follow.objects.none()
        followee_content_type = ContentType.objects.get(model=followee_type.lower())
        # Resolve profile id from user id
        if followee_type.lower() == 'student':
            try:
                followee_profile_id = Student.objects.get(user_id=followee_user_id).id
            except Student.DoesNotExist:
                return Follow.objects.none()
        elif followee_type.lower() == 'organization':
            try:
                followee_profile_id = Organization.objects.get(user_id=followee_user_id).id
            except Organization.DoesNotExist:
                return Follow.objects.none()
        else:
            return Follow.objects.none()
        return Follow.objects.filter(
            followee_content_type=followee_content_type,
            followee_object_id=followee_profile_id
        )

class ListFollowingView(generics.ListAPIView):
    serializer_class = GenericFollowSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        follower_type = self.request.query_params.get('follower_type')
        follower_user_id = self.request.query_params.get('follower_id')  # This is user.id from frontend
        if not follower_type or not follower_user_id:
            return Follow.objects.none()
        follower_content_type = ContentType.objects.get(model=follower_type.lower())
        # Resolve profile id from user id
        if follower_type.lower() == 'student':
            try:
                follower_profile_id = Student.objects.get(user_id=follower_user_id).id
            except Student.DoesNotExist:
                return Follow.objects.none()
        elif follower_type.lower() == 'organization':
            try:
                follower_profile_id = Organization.objects.get(user_id=follower_user_id).id
            except Organization.DoesNotExist:
                return Follow.objects.none()
        else:
            return Follow.objects.none()
        return Follow.objects.filter(
            follower_content_type=follower_content_type,
            follower_object_id=follower_profile_id
        )
logger = logging.getLogger(__name__)

def chunk_list(lst, chunk_size=10):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

class FeedView(APIView):
    """
    Generates a randomized, paginated, and category-based feed with dynamic weighting
    based on the user's profile type (Student or Organization).
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_feed_ratios(self, user_profile):
        """
        Returns the correct post distribution ratios based on the user's profile.
        """
        if isinstance(user_profile, Student):
            # Default ratios for a student user
            return {
                'followed': 3,
                'not_followed_rel': 2,
                'not_followed_no_rel': 2,
                'org_not_exclusive': 1,
                'org_followed': 2,
            }
        else:
            # Ratios for an organization user (or other non-student types)
            # Redistributes the 'not_followed_rel' posts (2) to other categories
            return {
                'followed': 4, # +1 from 'not_followed_rel'
                'not_followed_rel': 0,
                'not_followed_no_rel': 3, # +1 from 'not_followed_rel'
                'org_not_exclusive': 1,
                'org_followed': 2,
            }

    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            session_id = request.query_params.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
            rng = get_session_rng(session_id)

            current_user = request.user
            # Try to serve from precomputed Redis feed first (push-on-write)
            try:
                r = get_redis_client()
                feed_key = f"feed:{current_user.id}"

                # Support score-based cursor pagination: client may send `cursor=score:post_id`
                cursor = request.query_params.get('cursor')
                redis_post_ids = []
                redis_with_scores = []

                # Metrics: measure Redis read latency
                import time
                start_t = time.time()

                if cursor:
                    # Parse cursor and use ZREVRANGEBYSCORE to fetch items with score < last_score
                    try:
                        parts = cursor.split(':', 1)
                        last_score = float(parts[0])
                        # subtract a tiny epsilon to avoid returning the same score again
                        max_score = last_score - 1e-6
                    except Exception:
                        max_score = '+inf'
                    try:
                        # returns list of (member, score) when withscores=True
                        redis_with_scores = r.zrevrangebyscore(feed_key, max_score, '-inf', start=0, num=page_size, withscores=True)
                    except Exception:
                        redis_with_scores = []
                else:
                    # Fallback to legacy page-based zrevrange for compatibility
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size - 1
                    try:
                        members = r.zrevrange(feed_key, start_idx, end_idx)
                        redis_with_scores = [(m, None) for m in members]
                    except Exception:
                        redis_with_scores = []

                elapsed_ms = int((time.time() - start_t) * 1000)
                try:
                    # Increment simple counters and record latency (trim list to last 1000 entries)
                    r.incr('metrics:feed:reads')
                    if redis_with_scores:
                        r.incr('metrics:feed:redis_hits')
                    else:
                        r.incr('metrics:feed:redis_misses')
                    r.lpush('metrics:feed:latencies', elapsed_ms)
                    r.ltrim('metrics:feed:latencies', 0, 999)
                except Exception:
                    pass

                if redis_with_scores:
                    # Fetch posts from Firestore for these ids and return quickly
                    posts = []
                    author_ids = set()
                    # Batch document fetch to reduce Firestore read overhead
                    doc_refs = []
                    id_map = []
                    # normalize members and capture scores for cursor
                    post_scores = []
                    for member, score in redis_with_scores:
                        pid_str = member.decode() if isinstance(member, bytes) else str(member)
                        doc_refs.append(db.collection('posts').document(pid_str))
                        id_map.append(pid_str)
                        post_scores.append((pid_str, score))

                    try:
                        docs = list(db.get_all(doc_refs))
                    except Exception:
                        docs = []

                    post_ids_in_order = []
                    # Build a mapping of doc.id -> doc for stable ordering
                    docs_map = {doc.id: doc for doc in docs if doc.exists}
                    for pid_str, scr in post_scores:
                        doc = docs_map.get(pid_str)
                        if not doc:
                            continue
                        post_data = doc.to_dict()
                        post_data['id'] = doc.id
                        post_data['view_count'] = post_data.get('view_count', 0)
                        post_data['like_count'] = post_data.get('like_count', 0)
                        # set default; will fill via batch
                        post_data['has_liked'] = False
                        posts.append(post_data)
                        post_ids_in_order.append(doc.id)
                        if 'author_id' in post_data:
                            author_ids.add(str(post_data['author_id']))

                    # Build next_cursor if we have a full page
                    next_cursor = None
                    try:
                        if len(post_scores) == page_size:
                            last_pid, last_score = post_scores[-1]
                            if last_score is not None:
                                next_cursor = f"{float(last_score)}:{last_pid}"
                    except Exception:
                        next_cursor = None

                    # Batch resolve has_liked using Redis and hydrate authors via cache
                    if post_ids_in_order and current_user:
                        try:
                            liked = batch_has_liked(str(current_user.id), post_ids_in_order)
                        except Exception:
                            liked = set()
                        for p in posts:
                            if str(p.get('id')) in liked:
                                p['has_liked'] = True

                    authors_map = {}
                    if author_ids:
                        try:
                            authors_map = hydrate_authors_map(list(author_ids))
                        except Exception:
                            # fallback to DB fetch
                            authors_from_postgres = User.objects.filter(id__in=author_ids)
                            for author in authors_from_postgres:
                                author_name = display_name_slug = None
                                exclusive = False
                                author_faculty = None
                                author_department = None
                                if hasattr(author, 'student'):
                                    author_name = author.student.name
                                    display_name_slug = getattr(author.student, 'display_name_slug', None)
                                    author_faculty = getattr(author.student, 'faculty', None)
                                    author_department = getattr(author.student, 'department', None)
                                elif hasattr(author, 'organization'):
                                    author_name = author.organization.organization_name
                                    display_name_slug = getattr(author.organization, 'display_name_slug', None)
                                    exclusive = getattr(author.organization, 'exclusive', False)
                                authors_map[str(author.id)] = {
                                    "id": author.id,
                                    "email": author.email,
                                    "profile_pic_url": author.profile_pic_url,
                                    "name": author_name,
                                    "display_name_slug": display_name_slug,
                                    "is_verified": author.is_verified,
                                    "exclusive": exclusive,
                                    "faculty": author_faculty,
                                    "department": author_department,
                                }

                    serializer = FirestorePostOutputSerializer(posts, many=True, context={'authors_map': authors_map})
                    has_next_page = False
                    # If using cursors, determine has_next from next_cursor, else estimate by zcard
                    if cursor:
                        has_next_page = bool(next_cursor)
                    else:
                        try:
                            total = r.zcard(feed_key)
                            has_next_page = end_idx + 1 < total
                        except Exception:
                            has_next_page = False

                    response_payload = {
                        "results": serializer.data,
                        "session_id": session_id,
                        "page": page,
                        "page_size": page_size,
                        "has_next": has_next_page,
                    }
                    if cursor:
                        response_payload['next_cursor'] = next_cursor

                    return Response(response_payload, status=status.HTTP_200_OK)
            except Exception:
                # On any redis/firestore issue, fallback to original logic below
                pass
            current_user_profile = None
            # Corrected logic to get the profile and its following lists
            following_user_ids = []
            following_org_ids = []
            
            student_ct = ContentType.objects.get(model='student')
            org_ct = ContentType.objects.get(model='organization')

            if hasattr(current_user, 'student'):
                current_user_profile = current_user.student
                follows = Follow.objects.filter(
                    follower_content_type=student_ct,
                    follower_object_id=current_user_profile.id
                )
                following_student_ids = set(
                    str(x) for x in follows.filter(followee_content_type=student_ct)
                    .values_list('followee_object_id', flat=True)
                )
                following_org_ids = set(
                    str(x) for x in follows.filter(followee_content_type=org_ct)
                    .values_list('followee_object_id', flat=True)
                )
                following_user_ids = [str(uid) for uid in Student.objects.filter(id__in=following_student_ids).values_list('user_id', flat=True)]
                following_org_ids = [str(uid) for uid in Organization.objects.filter(id__in=following_org_ids).values_list('user_id', flat=True)]
            elif hasattr(current_user, 'organization'):
                current_user_profile = current_user.organization
                follows = Follow.objects.filter(
                    follower_content_type=org_ct,
                    follower_object_id=current_user_profile.id
                )
                following_student_ids = set(
                    str(x) for x in follows.filter(followee_content_type=student_ct)
                    .values_list('followee_object_id', flat=True)
                )
                following_org_ids = set(
                    str(x) for x in follows.filter(followee_content_type=org_ct)
                    .values_list('followee_object_id', flat=True)
                )
                following_user_ids = [str(uid) for uid in Student.objects.filter(id__in=following_student_ids).values_list('user_id', flat=True)]
                following_org_ids = [str(uid) for uid in Organization.objects.filter(id__in=following_org_ids).values_list('user_id', flat=True)]
            
            # print(f"Following user IDs: {following_user_ids}")
            # print(f"Following org IDs: {following_org_ids}")
            # print(f"Current user profile: {current_user_profile}")

            # Get the correct ratios based on user type
            ratios = self.get_feed_ratios(current_user_profile)
            CANDIDATE_POOL_SIZE = 75 
            
            # --- Fetch a Large Pool of Candidate Posts for Randomization ---
            followed_posts_candidates = []
            for chunk in chunk_list(following_user_ids):
                followed_posts_query = db.collection('posts').where('author_id', 'in', chunk).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(CANDIDATE_POOL_SIZE)
                for doc in followed_posts_query.stream():
                    post_data = doc.to_dict()
                    post_data['id'] = doc.id
                    followed_posts_candidates.append(post_data)
            
            # print(f"Followed posts candidates count: {len(followed_posts_candidates)}")

            not_followed_relations_candidates = []
            shared_relations_users_ids = []
            if isinstance(current_user_profile, Student):
                # exclude_ids = following_user_ids | {current_user.id}
                shared_relations_users_ids = list(
                    Student.objects.filter(
                        Q(faculty=current_user_profile.faculty) | 
                        Q(department=current_user_profile.department) |
                        Q(religion=current_user_profile.religion)
                    ).exclude(user__id__in=[int(uid) for uid in following_user_ids]).exclude(user=current_user).values_list('user_id', flat=True)
                )
                # print(f"Shared relations user IDs before limit: {shared_relations_users_ids}")
                for chunk in chunk_list([str(uid) for uid in shared_relations_users_ids]):
                    relations_posts_query = db.collection('posts').where('author_id', 'in', chunk).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(CANDIDATE_POOL_SIZE)
                    for doc in relations_posts_query.stream():
                        post_data = doc.to_dict()
                        post_data['id'] = doc.id
                        not_followed_relations_candidates.append(post_data)
            
            # print(f"Not followed relations candidates count: {len(not_followed_relations_candidates)}")

            all_other_user_ids = list(
                Student.objects.exclude(user__id__in=[int(uid) for uid in following_user_ids]).exclude(user__id__in=shared_relations_users_ids).exclude(user=current_user)
                .values_list('user_id', flat=True)
            )[:CANDIDATE_POOL_SIZE]

            # Build a set of author IDs from not_followed_relations_candidates for filtering
            not_followed_rel_author_ids = set(post.get('author_id') for post in not_followed_relations_candidates)

            not_followed_no_relations_candidates = []
            for chunk in chunk_list([str(uid) for uid in all_other_user_ids]):
                other_posts_query = db.collection('posts').where('author_id', 'in', chunk).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(CANDIDATE_POOL_SIZE)
                for doc in other_posts_query.stream():
                    post_data = doc.to_dict()
                    post_data['id'] = doc.id
                    author_id = post_data.get('author_id')
                    if author_id not in not_followed_rel_author_ids and author_id not in [str(uid) for uid in following_user_ids]:
                        not_followed_no_relations_candidates.append(post_data)

            org_followed_candidates = []
            for chunk in chunk_list(following_org_ids):
                org_followed_query = db.collection('posts').where('author_id', 'in', chunk).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(CANDIDATE_POOL_SIZE)
                for doc in org_followed_query.stream():
                    post_data = doc.to_dict()
                    post_data['id'] = doc.id
                    org_followed_candidates.append(post_data)
            
            # print(f"Org followed candidates count: {len(org_followed_candidates)}")
            # print(f"not_followed_no_relations_candidates count: {len(not_followed_no_relations_candidates)}")

            non_exclusive_org_ids = list(Organization.objects.filter(exclusive=False).exclude(user__id__in=[int(uid) for uid in following_org_ids]).values_list('user_id', flat=True))
            org_not_exclusive_candidates = []
            for chunk in chunk_list([str(uid) for uid in non_exclusive_org_ids]):
                org_not_exclusive_query = db.collection('posts').where('author_id', 'in', chunk).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(CANDIDATE_POOL_SIZE)
                for doc in org_not_exclusive_query.stream():
                    post_data = doc.to_dict()
                    post_data['id'] = doc.id
                    org_not_exclusive_candidates.append(post_data)
            
            # print(f"Shared relations user IDs: {shared_relations_users_ids}")
            # print(f"All other user IDs: {all_other_user_ids}")

            
            logger.info(f"Followed posts: {len(followed_posts_candidates)}")
            logger.info(f"Not followed (relations): {len(not_followed_relations_candidates)}")
            logger.info(f"Not followed (no relations): {len(not_followed_no_relations_candidates)}")
            logger.info(f"Org followed: {len(org_followed_candidates)}")
            logger.info(f"Org not exclusive: {len(org_not_exclusive_candidates)}")

            # --- 2. Build the Final Randomized, Un-Paginated Feed using dynamic ratios ---
            full_feed_list = []

            full_feed_list.extend(rng.sample(followed_posts_candidates, min(ratios['followed'], len(followed_posts_candidates))))
            full_feed_list.extend(rng.sample(not_followed_no_relations_candidates, min(ratios['not_followed_no_rel'], len(not_followed_no_relations_candidates))))
            full_feed_list.extend(rng.sample(not_followed_relations_candidates, min(ratios['not_followed_rel'], len(not_followed_relations_candidates))))
            full_feed_list.extend(rng.sample(org_not_exclusive_candidates, min(ratios['org_not_exclusive'], len(org_not_exclusive_candidates))))
            full_feed_list.extend(rng.sample(org_followed_candidates, min(ratios['org_followed'], len(org_followed_candidates))))

            # print(f"Full feed list count before shuffle: {len(full_feed_list)}")
            if len(full_feed_list) < page_size:
                logger.info("Falling back to a hybrid general feed. ")

                # Fetches a pool of recent posts
                recent_posts_query = db.collection('posts').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(int(CANDIDATE_POOL_SIZE // 2))
                recent_posts = []
                for doc in recent_posts_query.stream():
                    post_data = doc.to_dict()
                    post_data['id'] = doc.id
                    recent_posts.append(post_data)

                # Fetches a pool of popular posts (e.g., by view count)
                viewed_posts_query = db.collection('posts').order_by('view_count', direction=firestore.Query.DESCENDING).limit(int(CANDIDATE_POOL_SIZE // 2))
                viewed_posts = []
                for doc in viewed_posts_query.stream():
                    post_data = doc.to_dict()
                    post_data['id'] = doc.id
                    viewed_posts.append(post_data)

                # Combine the pools and remove duplicates
                combined_posts = recent_posts + viewed_posts
                seen_ids = set()
                hybrid_feed_candidates = []
                for post in combined_posts:
                    if post.get('id') not in seen_ids:
                        hybrid_feed_candidates.append(post)
                        seen_ids.add(post.get('id'))
                
                full_feed_list = hybrid_feed_candidates

            # Deterministic, session-scored ordering with recency and engagement bias
            session_sort_posts(full_feed_list, session_id, recency_weight=0.7, engagement_weight=0.15)

            # print(f"Full feed list count after shuffle: {len(full_feed_list)}")



            # --- 3. Paginate the Final List ---
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            paginated_posts = full_feed_list[start_index:end_index]

            # print(f"Paginated posts count before deduplication: {len(paginated_posts)}")
            
            unique_paginated_posts = []
            seen_post_ids = set()
            for post in paginated_posts:
                if post.get('id') not in seen_post_ids:
                    unique_paginated_posts.append(post)
                    seen_post_ids.add(post.get('id'))
            
            # print(f"Paginated posts count after deduplication: {len(unique_paginated_posts)}")

            final_posts_for_response = []

            # Collect all post IDs for batch checks
            final_post_ids = [post['id'] for post in unique_paginated_posts if 'id' in post]

            # NEW REWARD LOGIC
            rewarded_post_ids_set = set()
            if current_user.is_authenticated:
                rewarded_post_ids_qs = RewardPointTransaction.objects.filter(
                    giver=current_user,
                    firestore_post_id__in=final_post_ids).values_list('firestore_post_id', flat=True)
                rewarded_post_ids_set = set(rewarded_post_ids_qs)
                # Also compute total reward points per post for the final page
                try:
                    reward_totals_qs = RewardPointTransaction.objects.filter(
                        firestore_post_id__in=final_post_ids
                    ).values('firestore_post_id').annotate(total=Sum('points'))
                    reward_map = {r['firestore_post_id']: r['total'] for r in reward_totals_qs}
                except Exception:
                    reward_map = {}
            

            # Batch check which posts the current user has liked (use Redis cached sets)
            liked_set = set()
            if request.user.is_authenticated and final_post_ids:
                try:
                    liked_set = batch_has_liked(str(current_user.id), final_post_ids)
                except Exception:
                    liked_set = set()

            for post_data in unique_paginated_posts:
                post_id = post_data.get('id')
                if not post_id:
                    continue
                post_data['id'] = post_id
                post_doc = db.collection('posts').document(post_id).get()
                post_data['view_count'] = post_doc.to_dict().get('view_count', 0) if post_doc.exists else 0
                post_data['like_count'] = post_doc.to_dict().get('like_count', 0) if post_doc.exists else 0
                post_data['has_liked'] = str(post_id) in liked_set
                post_data['has_rewarded'] = post_id in rewarded_post_ids_set
                post_data['reward_point_count'] = reward_map.get(post_id, 0)
                final_posts_for_response.append(post_data)

            # print(f"Final posts for response count: {len(final_posts_for_response)}")

            # --- 4. Hydrate Author Data and Serialize ---
            author_ids = set(str(post['author_id']) for post in final_posts_for_response if 'author_id' in post)
            authors_map = {}
            authors_from_postgres = User.objects.filter(id__in=author_ids)
            for author in authors_from_postgres:
                author_name = display_name_slug = None
                exclusive = False
                author_faculty = None
                author_department = None

                if hasattr(author, 'student'):
                    author_name = author.student.name
                    display_name_slug = getattr(author.student, 'display_name_slug', None)
                    author_faculty = getattr(author.student, 'faculty', None)
                    author_department = getattr(author.student, 'department', None)
                elif hasattr(author, 'organization'):
                    author_name = author.organization.organization_name
                    display_name_slug = getattr(author.organization, 'display_name_slug', None)
                    exclusive = getattr(author.organization, 'exclusive', False)

                authors_map[str(author.id)] = {
                    "id": author.id,
                    "email": author.email,
                    "profile_pic_url": author.profile_pic_url,
                    "name": author_name,
                    "display_name_slug": display_name_slug,
                    "is_verified": author.is_verified,
                    "exclusive": exclusive,
                    "faculty": author_faculty,
                    "department": author_department,
                }
            serializer = FirestorePostOutputSerializer(final_posts_for_response, many=True, context={'authors_map': authors_map})
            has_next_page = end_index < len(full_feed_list)
            
            return Response({
                "results": serializer.data,
                "session_id": session_id,
                "page": page,
                "page_size": page_size,
                "has_next": has_next_page,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching feed posts: {str(e)}")
            return Response({"error": f"Failed to retrieve feed posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Custom Permission Example (simplified)
class IsFirestoreDocOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj_data):
        # For read permissions, they are often granted (IsAuthenticatedOrReadOnly)
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to the owner of the doc.
        # obj_data is the dictionary from Firestore
        return obj_data.get('author_id') == str(request.user.id)


##
## Post Views (Firestore)
##
class QuestionPostView(APIView):
    """ List recent posts that has the tag 'question' in a order of new to old, paginated.
    Uses a session ID for consistent pagination.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self,request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            session_id = request.query_params.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
            # For per-session deterministic ordering we use a local RNG only when needed
            rng = get_session_rng(session_id)

            # Fetch posts with 'question' tag
            question_posts_query = db.collection('posts').where('tags', '==', 'question').order_by('timestamp', direction=firestore.Query.DESCENDING)

            # Pagination
            start_index = (page - 1) * page_size
            end_index = start_index + page_size

            docs = question_posts_query.offset(start_index).limit(page_size).stream()

            posts_list = []
            author_ids = set()
            last_doc_id = None

            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['view_count'] = post_data.get('view_count', 0)
                post_data['like_count'] = post_data.get('like_count', 0)

                post_data['has_liked'] = False
                post_data['has_rewarded'] = False

                posts_list.append(post_data)
                last_doc_id = doc.id  # Will end up being the last doc in the loop

                if 'author_id' in post_data:
                    author_ids.add(str(post_data['author_id']))

            # Hydrate authors (similar to FeedView)
            authors_map = {}
            if author_ids:
                authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
                for author in authors_from_postgres:
                    author_name = None
                    display_name_slug = None
                    if hasattr(author, 'student'):
                        author_name = author.student.name
                        display_name_slug = getattr(author.student, 'display_name_slug', None)
                        author_faculty = getattr(author.student, 'faculty', None)
                        author_department = getattr(author.student, 'department', None)
                    elif hasattr(author, 'organization'):
                        author_name = author.organization.organization_name
                        display_name_slug = getattr(author.organization, 'display_name_slug', None)
                        exclusive = getattr(author.organization, 'exclusive', False)

                    authors_map[str(author.id)] = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": author_name,
                        "display_name_slug": display_name_slug,
                        "is_verified": author.is_verified,
                        "exclusive": exclusive if hasattr(author, 'organization') else False,
                        "faculty": author_faculty if hasattr(author, 'student') else None,
                        "department": author_department if hasattr(author, 'student') else None,
                    }
            # Has liked logic (batched via Redis)
            if request.user.is_authenticated and posts_list:
                user_id = str(request.user.id)
                post_ids_batch = [post['id'] for post in posts_list if 'id' in post]
                liked_set = batch_has_liked(user_id, post_ids_batch)
                for post in posts_list:
                    pid = post.get('id')
                    post['has_liked'] = str(pid) in liked_set if pid else False
                # Reward point totals for this page
                firestore_post_ids = [p['id'] for p in posts_list if 'id' in p]
                try:
                    reward_totals_qs = RewardPointTransaction.objects.filter(
                        firestore_post_id__in=firestore_post_ids
                    ).values('firestore_post_id').annotate(total=Sum('points'))
                    reward_map = {r['firestore_post_id']: r['total'] for r in reward_totals_qs}
                except Exception:
                    reward_map = {}

                # Batched rewarded presence for this user
                try:
                    rewarded_ids = RewardPointTransaction.objects.filter(
                        giver=request.user,
                        firestore_post_id__in=firestore_post_ids
                    ).values_list('firestore_post_id', flat=True)
                    rewarded_set = {str(r) for r in rewarded_ids}
                except Exception:
                    rewarded_set = set()

                for post in posts_list:
                    pid = post.get('id')
                    post['reward_point_count'] = reward_map.get(pid, 0)
                    post['has_rewarded'] = str(pid) in rewarded_set if pid else False
            serializer = FirestorePostOutputSerializer(posts_list, many=True, context={'authors_map': authors_map})
            has_next_page = end_index < len(question_posts_query.get())
            return Response({
                "results": serializer.data,
                "session_id": session_id,
                "page": page,
                "page_size": page_size,
                "has_next": has_next_page,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching question posts: {str(e)}")
            return Response({"error": f"Failed to retrieve question posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RelatablePostView(APIView):
    """
    List recent posts that has the tag 'relatable' in a order of new to old, paginated.
    Uses a session ID for consistent pagination.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self,request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            session_id = request.query_params.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
            rng = get_session_rng(session_id)

            # Fetch posts with 'question' tag
            question_posts_query = db.collection('posts').where('tags', '==', 'relatable').order_by('timestamp', direction=firestore.Query.DESCENDING)

            # Pagination
            start_index = (page - 1) * page_size
            end_index = start_index + page_size

            docs = question_posts_query.offset(start_index).limit(page_size).stream()

            posts_list = []
            author_ids = set()
            last_doc_id = None

            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['view_count'] = post_data.get('view_count', 0)
                post_data['like_count'] = post_data.get('like_count', 0)

                post_data['has_liked'] = False
                post_data['has_rewarded'] = False

                posts_list.append(post_data)
                last_doc_id = doc.id  # Will end up being the last doc in the loop

                if 'author_id' in post_data:
                    author_ids.add(str(post_data['author_id']))

            # Hydrate authors (similar to FeedView)
            authors_map = {}
            if author_ids:
                authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
                for author in authors_from_postgres:
                    author_name = None
                    display_name_slug = None
                    if hasattr(author, 'student'):
                        author_name = author.student.name
                        display_name_slug = getattr(author.student, 'display_name_slug', None)
                        author_faculty = getattr(author.student, 'faculty', None)
                        author_department = getattr(author.student, 'department', None)
                    elif hasattr(author, 'organization'):
                        author_name = author.organization.organization_name
                        display_name_slug = getattr(author.organization, 'display_name_slug', None)
                        exclusive = getattr(author.organization, 'exclusive', False)

                    authors_map[str(author.id)] = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": author_name,
                        "display_name_slug": display_name_slug,
                        "is_verified": author.is_verified,
                        "exclusive": exclusive if hasattr(author, 'organization') else False,
                        "faculty": author_faculty if hasattr(author, 'student') else None,
                        "department": author_department if hasattr(author, 'student') else None,
                    }
            # Has liked logic (batched via Redis) and reward totals
            if request.user.is_authenticated and posts_list:
                user_id = str(request.user.id)
                post_ids_batch = [post['id'] for post in posts_list if 'id' in post]
                liked_set = batch_has_liked(user_id, post_ids_batch)

                # Batched rewarded presence (did this user reward these posts?)
                rewarded_post_ids = RewardPointTransaction.objects.filter(
                    giver=request.user,
                    firestore_post_id__in=post_ids_batch
                ).values_list('firestore_post_id', flat=True)
                rewarded_set = set(rewarded_post_ids)

                # Reward point totals (sum per post)
                try:
                    reward_totals_qs = RewardPointTransaction.objects.filter(
                        firestore_post_id__in=post_ids_batch
                    ).values('firestore_post_id').annotate(total=Sum('points'))
                    reward_map = {r['firestore_post_id']: r['total'] for r in reward_totals_qs}
                except Exception:
                    reward_map = {}

                for post in posts_list:
                    pid = post.get('id')
                    post['has_liked'] = str(pid) in liked_set if pid else False
                    post['has_rewarded'] = str(pid) in rewarded_set if pid else False
                    post['reward_point_count'] = reward_map.get(pid, 0)
            serializer = FirestorePostOutputSerializer(posts_list, many=True, context={'authors_map': authors_map})
            has_next_page = end_index < len(question_posts_query.get())
            return Response({
                "results": serializer.data,
                "session_id": session_id,
                "page": page,
                "page_size": page_size,
                "has_next": has_next_page,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching relatable posts: {str(e)}")
            return Response({"error": f"Failed to retrieve relatable posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdatesPostView(APIView):
    """
    List recent posts that has the tag 'update' in a order of new to old, paginated.
    Uses a session ID for consistent pagination.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self,request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            session_id = request.query_params.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
            rng = get_session_rng(session_id)

            # Fetch posts with 'question' tag
            question_posts_query = db.collection('posts').where('tags', '==', 'update').order_by('timestamp', direction=firestore.Query.DESCENDING)

            # Pagination
            start_index = (page - 1) * page_size
            end_index = start_index + page_size

            docs = question_posts_query.offset(start_index).limit(page_size).stream()

            posts_list = []
            author_ids = set()
            last_doc_id = None

            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['view_count'] = post_data.get('view_count', 0)
                post_data['like_count'] = post_data.get('like_count', 0)

                post_data['has_liked'] = False
                post_data['has_rewarded'] = False

                posts_list.append(post_data)
                last_doc_id = doc.id  # Will end up being the last doc in the loop

                if 'author_id' in post_data:
                    author_ids.add(str(post_data['author_id']))

            # Hydrate authors (similar to FeedView)
            authors_map = {}
            if author_ids:
                authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
                for author in authors_from_postgres:
                    author_name = None
                    display_name_slug = None
                    if hasattr(author, 'student'):
                        author_name = author.student.name
                        display_name_slug = getattr(author.student, 'display_name_slug', None)
                        author_faculty = getattr(author.student, 'faculty', None)
                        author_department = getattr(author.student, 'department', None)
                    elif hasattr(author, 'organization'):
                        author_name = author.organization.organization_name
                        display_name_slug = getattr(author.organization, 'display_name_slug', None)
                        exclusive = getattr(author.organization, 'exclusive', False)

                    authors_map[str(author.id)] = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": author_name,
                        "display_name_slug": display_name_slug,
                        "is_verified": author.is_verified,
                        "exclusive": exclusive if hasattr(author, 'organization') else False,
                        "faculty": author_faculty if hasattr(author, 'student') else None,
                        "department": author_department if hasattr(author, 'student') else None,
                    }
            # Batch has_liked and has_rewarded
            if request.user.is_authenticated and posts_list:
                user_id = str(request.user.id)
                post_ids = [p['id'] for p in posts_list]
                try:
                    liked = batch_has_liked(user_id, post_ids)
                except Exception:
                    liked = set()
                try:
                    rewarded_ids = RewardPointTransaction.objects.filter(
                        giver=request.user,
                        firestore_post_id__in=post_ids
                    ).values_list('firestore_post_id', flat=True)
                    rewarded = {str(r) for r in rewarded_ids}
                except Exception:
                    rewarded = set()
                # Reward point totals for this page
                try:
                    reward_totals_qs = RewardPointTransaction.objects.filter(
                        firestore_post_id__in=post_ids
                    ).values('firestore_post_id').annotate(total=Sum('points'))
                    reward_map = {r['firestore_post_id']: r['total'] for r in reward_totals_qs}
                except Exception:
                    reward_map = {}
                for post in posts_list:
                    pid = str(post.get('id'))
                    post['has_liked'] = pid in liked
                    post['has_rewarded'] = pid in rewarded
                    post['reward_point_count'] = reward_map.get(post.get('id'), 0)
            serializer = FirestorePostOutputSerializer(posts_list, many=True, context={'authors_map': authors_map})
            has_next_page = end_index < len(question_posts_query.get())
            return Response({
                "results": serializer.data,
                "session_id": session_id,
                "page": page,
                "page_size": page_size,
                "has_next": has_next_page,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching update posts: {str(e)}")
            return Response({"error": f"Failed to retrieve update posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MilestonePostView(APIView):
    """
    List recent posts that has the tag 'milestone' in a order of new to old, paginated.
    Uses a session ID for consistent pagination.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self,request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            session_id = request.query_params.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
            rng = get_session_rng(session_id)

            # Fetch posts with 'question' tag
            question_posts_query = db.collection('posts').where('tags', '==', 'milestone').order_by('timestamp', direction=firestore.Query.DESCENDING)

            # Pagination
            start_index = (page - 1) * page_size
            end_index = start_index + page_size

            docs = question_posts_query.offset(start_index).limit(page_size).stream()

            posts_list = []
            author_ids = set()
            last_doc_id = None

            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['view_count'] = post_data.get('view_count', 0)
                post_data['like_count'] = post_data.get('like_count', 0)

                post_data['has_liked'] = False
                post_data['has_rewarded'] = False

                posts_list.append(post_data)
                last_doc_id = doc.id  # Will end up being the last doc in the loop

                if 'author_id' in post_data:
                    author_ids.add(str(post_data['author_id']))

            # Hydrate authors (similar to FeedView)
            authors_map = {}
            if author_ids:
                authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
                for author in authors_from_postgres:
                    author_name = None
                    display_name_slug = None
                    if hasattr(author, 'student'):
                        author_name = author.student.name
                        display_name_slug = getattr(author.student, 'display_name_slug', None)
                        author_faculty = getattr(author.student, 'faculty', None)
                        author_department = getattr(author.student, 'department', None)
                    elif hasattr(author, 'organization'):
                        author_name = author.organization.organization_name
                        display_name_slug = getattr(author.organization, 'display_name_slug', None)
                        exclusive = getattr(author.organization, 'exclusive', False)

                    authors_map[str(author.id)] = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": author_name,
                        "display_name_slug": display_name_slug,
                        "is_verified": author.is_verified,
                        "exclusive": exclusive if hasattr(author, 'organization') else False,
                        "faculty": author_faculty if hasattr(author, 'student') else None,
                        "department": author_department if hasattr(author, 'student') else None,
                    }
            # Batch has_liked and has_rewarded
            if request.user.is_authenticated and posts_list:
                user_id = str(request.user.id)
                post_ids = [p['id'] for p in posts_list]
                try:
                    liked = batch_has_liked(user_id, post_ids)
                except Exception:
                    liked = set()
                try:
                    rewarded_ids = RewardPointTransaction.objects.filter(
                        giver=request.user,
                        firestore_post_id__in=post_ids
                    ).values_list('firestore_post_id', flat=True)
                    rewarded = {str(r) for r in rewarded_ids}
                except Exception:
                    rewarded = set()
                # Reward point totals for this page
                try:
                    reward_totals_qs = RewardPointTransaction.objects.filter(
                        firestore_post_id__in=post_ids
                    ).values('firestore_post_id').annotate(total=Sum('points'))
                    reward_map = {r['firestore_post_id']: r['total'] for r in reward_totals_qs}
                except Exception:
                    reward_map = {}
                for post in posts_list:
                    pid = str(post.get('id'))
                    post['has_liked'] = pid in liked
                    post['has_rewarded'] = pid in rewarded
                    post['reward_point_count'] = reward_map.get(post.get('id'), 0)
            serializer = FirestorePostOutputSerializer(posts_list, many=True, context={'authors_map': authors_map})
            has_next_page = end_index < len(question_posts_query.get())
            return Response({
                "results": serializer.data,
                "session_id": session_id,
                "page": page,
                "page_size": page_size,
                "has_next": has_next_page,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching Milestone posts: {str(e)}")
            return Response({"error": f"Failed to retrieve Milestone posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BatchPostViewIncrementAPIView(APIView):
    """
    Increments the view count for multiple posts, but only once per user per post.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        post_ids = request.data.get('post_ids', [])
        user_id = str(request.user.id)
        if not isinstance(post_ids, list) or not post_ids:
            return Response({"error": "A list of post_ids is required."}, status=status.HTTP_400_BAD_REQUEST)

        batch = db.batch()
        incremented = 0
        for post_id in set(post_ids):
            post_ref = db.collection('posts').document(post_id)
            view_ref = post_ref.collection('views').document(user_id)
            if not view_ref.get().exists:
                batch.set(view_ref, {'viewed_at': firestore.SERVER_TIMESTAMP})
                batch.update(post_ref, {'view_count': firestore.Increment(1)})
                incremented += 1
        batch.commit()
        return Response({"message": f"{incremented} post view counts incremented (unique per user)."}, status=status.HTTP_200_OK)
    

class PostListCreateFirestoreView(APIView):
    """
    Create a new post or list all posts from Firestore.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            # --- Pagination setup ---
            page_size = int(request.query_params.get("page_size", 10))
            start_after_id = request.query_params.get("start_after", None)

            posts_ref = db.collection('posts').order_by('timestamp', direction=firestore.Query.DESCENDING)

            if start_after_id:
                start_doc = db.collection('posts').document(start_after_id).get()
                if start_doc.exists:
                    posts_ref = posts_ref.start_after(start_doc)
                else:
                    return Response({"error": "Invalid start_after ID"}, status=status.HTTP_400_BAD_REQUEST)

            docs = posts_ref.limit(page_size).stream()
            
            posts_list = []
            author_ids = set()
            firestore_post_ids = []
            last_doc_id = None

            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['view_count'] = post_data.get('view_count', 0)
                post_data['like_count'] = post_data.get('like_count', 0)

                post_data['has_liked'] = False
                post_data['has_rewarded'] = False


                posts_list.append(post_data)
                last_doc_id = doc.id  # Will end up being the last doc in the loop

                firestore_post_ids.append(doc.id)
                if 'author_id' in post_data:
                    author_ids.add(str(post_data['author_id']))

            # --- Hydrate authors ---
            authors_map = {}
            if author_ids:
                authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
                for author in authors_from_postgres:
                    author_name = None
                    display_name_slug = None
                    if hasattr(author, 'student'):
                        author_name = author.student.name
                        display_name_slug = getattr(author.student, 'display_name_slug', None)
                        author_faculty = getattr(author.student, 'faculty', None)
                        author_department = getattr(author.student, 'department', None)
                    elif hasattr(author, 'organization'):
                        author_name = author.organization.organization_name
                        display_name_slug = getattr(author.organization, 'display_name_slug', None)
                        exclusive = getattr(author.organization, 'exclusive', False)

                    authors_map[str(author.id)] = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": author_name,
                        "display_name_slug": display_name_slug,
                        "is_verified": author.is_verified,
                        "exclusive": exclusive if hasattr(author, 'organization') else False,
                        "faculty": author_faculty if hasattr(author, 'student') else None,
                        "department": author_department if hasattr(author, 'student') else None,
                    }

            # --- Has liked logic (batched via Redis) ---
            if request.user.is_authenticated and posts_list:
                user_id = str(request.user.id)
                post_ids_batch = [post['id'] for post in posts_list if 'id' in post]
                liked_set = batch_has_liked(user_id, post_ids_batch)
                for post in posts_list:
                    pid = post.get('id')
                    post['has_liked'] = str(pid) in liked_set if pid else False

                rewarded_post_ids = RewardPointTransaction.objects.filter(
                    giver=request.user,
                    firestore_post_id__in=firestore_post_ids
                ).values_list('firestore_post_id', flat=True)

                rewarded_set = set(rewarded_post_ids)

                for post in posts_list:
                    post['has_rewarded'] = post['id'] in rewarded_set
                # --- Reward point totals (sum of points per post) ---
                try:
                    reward_totals_qs = RewardPointTransaction.objects.filter(
                        firestore_post_id__in=firestore_post_ids
                    ).values('firestore_post_id').annotate(total=Sum('points'))
                    reward_map = {r['firestore_post_id']: r['total'] for r in reward_totals_qs}
                except Exception:
                    reward_map = {}

                for post in posts_list:
                    post['reward_point_count'] = reward_map.get(post.get('id'), 0)

            serializer = FirestorePostOutputSerializer(posts_list, many=True, context={'authors_map': authors_map})
            return Response({
                "results": serializer.data,
                "next_cursor": last_doc_id if len(posts_list) == page_size else None
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Failed to retrieve posts: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        # if not getattr(request.user, 'is_verified', False):
        #     return Response({"error": "You must be a verified user to create posts."}, status=status.HTTP_403_FORBIDDEN)

        serializer = FirestorePostCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                author_name = ""
                author_profile_pic_url = request.user.profile_pic_url

                if hasattr(request.user, 'student'):
                    author_name = request.user.student.name
                elif hasattr(request.user, 'organization'):
                    author_name = request.user.organization.organization_name
                else:
                    author_name = request.user.email

                post_payload = {
                    'author_id': str(request.user.id), # Link to Django User ID
                    # 'author_email': request.user.email, # Denormalize for convenience
                    'content': data['content'],
                    'slug': data.get('slug', ''), # Handle slug generation if needed
                    'tags': data.get('tags'),
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'like_count': 0,
                    'comment_count': 0,
                    'share_count': 0,
                    'media_urls': data.get('media_urls', []), # Handle media URLs if provided
                    'view_count': 0,
                    # Add other fields like media_urls, visibility, etc.
                }
                # Add a new document with an auto-generated ID
                update_time, doc_ref = db.collection('posts').add(post_payload)
                
                created_post = doc_ref.get().to_dict()
                created_post['id'] = doc_ref.id

                # --- Offload notification to Celery ---
                notify_all_users_new_post.delay(
                    author_id=request.user.id,
                    author_name=author_name,
                    post_content=data['content'],
                    post_id=created_post['id'],
                    author_profile_pic_url=author_profile_pic_url,
                )

                # --- Push-on-write: schedule fan-out to followers via Celery ---
                try:
                    from .tasks import fanout_post_to_followers
                    fanout_post_to_followers.delay(request.user.id, created_post['id'])
                except Exception:
                    logger.exception("Failed to enqueue fanout_post_to_followers task")

                return Response(created_post, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PostDetailFirestoreView(APIView):
    """
    Retrieve, update, or delete a single post from Firestore using document ID.
    If using slugs, you'd query: db.collection('posts').where('slug', '==', slug_value).limit(1).stream()
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsFirestoreDocOwner]
    authentication_classes = [JWTAuthentication]

    def get_post_doc_and_data(self, post_id_or_slug, is_slug=False):
        try:
            if is_slug:
                docs = db.collection('posts').where('slug', '==', post_id_or_slug).limit(1).stream()
                doc = next(docs, None) # Get the first document if it exists
                if doc:
                    return doc.reference, doc.to_dict()
                return None, None
            else: # Assume it's a document ID
                doc_ref = db.collection('posts').document(post_id_or_slug)
                doc = doc_ref.get()
                if doc.exists:
                    return doc_ref, doc.to_dict()
                return None, None
        except Exception: # Broad exception for brevity
            return None, None

    def get(self, request, post_id): # post_identifier can be ID or slug
        # Determine if post_identifier is a slug or ID based on your URL pattern
        # For this example, let's assume it's post_id. If using slug, pass is_slug=True
        doc_ref, post_data = self.get_post_doc_and_data(post_id) #, is_slug=True if your URL uses slug)

        if post_data:
            post_data['id'] = doc_ref.id
            post_data['view_count'] = doc_ref.get().to_dict().get('view_count', 0)
            post_data['like_count'] = doc_ref.get().to_dict().get('like_count', 0)

            

            # Hydrate author info
            author_id = str(post_data.get('author_id'))
            author_info = None
            if author_id:
                try:
                    author = User.objects.only('id', 'email', 'profile_pic_url', 'is_verified').get(id=author_id)
                    author_name = None
                    if hasattr(author, 'student') and author.student.name:
                        author_name = author.student.name
                        display_name_slug = getattr(author.student, 'display_name_slug', None)
                        author_faculty = author.student.faculty
                        author_department = author.student.department
                    elif hasattr(author, 'organization') and author.organization.organization_name:
                        author_name = author.organization.organization_name
                        exclusive = author.organization.exclusive
                        display_name_slug = getattr(author.organization, 'display_name_slug', None)

                    author_info = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": author_name,
                        "is_verified": author.is_verified if hasattr(author, 'is_verified') else False,
                        "display_name_slug": display_name_slug,
                        "exclusive": exclusive if hasattr(author, 'organization') else False,
                        "faculty": author_faculty if hasattr(author, 'student') else None,
                        "department": author_department if hasattr(author, 'student') else None,
                    }
                except User.DoesNotExist:
                    author_info = {
                        "id": author_id,
                        "email": None,
                        "profile_pic_url": None,
                        "name": None,
                        "is_verified": None
                    }
            else:
                author_info = None
            post_data['author_name'] = author_info['name'] if author_info else None
            post_data['author_profile_pic_url'] = author_info['profile_pic_url'] if author_info else None
            post_data['is_verified'] = author_info['is_verified'] if author_info else None
            post_data['author_id'] = author_info['id'] if author_info else None
            post_data['author_email'] = author_info['email'] if author_info else None
            post_data['author_exclusive'] = author_info['exclusive'] if author_info else False
            post_data['author_faculty'] = author_info['faculty'] if author_info else None
            post_data['author_department'] = author_info['department'] if author_info else None
            post_data['author_display_name_slug'] = display_name_slug

            # Add has_liked
            post_data['has_liked'] = False
            if request.user.is_authenticated:
                user_id = str(request.user.id)
                like_doc_ref = db.collection('posts').document(post_data['id']).collection('likes').document(user_id)
                post_data['has_liked'] = like_doc_ref.get().exists
            
            post_data['has_rewarded'] = False
            if request.user.is_authenticated:
                rewarded = RewardPointTransaction.objects.filter(
                    giver=request.user,
                    firestore_post_id=post_data['id']
                ).exists()
                post_data['has_rewarded'] = rewarded

            # Total reward points for the post
            try:
                total_points = RewardPointTransaction.objects.filter(
                    firestore_post_id=post_data['id']
                ).aggregate(total=Sum('points'))['total'] or 0
            except Exception:
                total_points = 0
            post_data['reward_point_count'] = total_points

            return Response(post_data, status=status.HTTP_200_OK)
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, post_id):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        doc_ref, post_data = self.get_post_doc_and_data(post_id)
        if not post_data:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        # Ownership check
        if post_data.get('author_id') != str(request.user.id):
            return Response({"error": "You do not have permission to edit this post."}, status=status.HTTP_403_FORBIDDEN)

        serializer = FirestorePostUpdateSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            update_payload = serializer.validated_data
            if not update_payload:
                return Response({"error": "No data provided for update."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                doc_ref.update(update_payload)
                updated_post_data = doc_ref.get().to_dict()
                updated_post_data['id'] = doc_ref.id
                return Response(updated_post_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, post_id):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        doc_ref, post_data = self.get_post_doc_and_data(post_id)
        if not post_data:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        # Ownership check
        if post_data.get('author_id') != str(request.user.id):
            return Response({"error": "You do not have permission to delete this post."}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Important: Also delete associated comments, likes, shares (e.g., using a Cloud Function or batch writes)
            doc_ref.delete()
            # Example: Batch delete for subcollection (do this carefully)
            # comments_ref = doc_ref.collection('comments')
            # for comment_doc in comments_ref.stream():
            #     comment_doc.reference.delete() # This can be slow for many comments, use batch/Cloud Function

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

##
## Comment Views (Firestore)
## Assuming comments are a subcollection under posts: `posts/{post_id}/comments/{comment_id}`
##
class CommentCreateFirestoreView(APIView):
    """
    Create a new comment for a post in Firestore using a transactional decorator.
    URL: /api/posts/{post_id}/comments/
    """
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    authentication_classes = [JWTAuthentication]

    def post(self, request, post_id): # Get post_id from URL
        user_id = str(request.user.id) # Ensure user ID is a string for Firestore

        # 1. Initial Post Existence Check (outside transaction for quick feedback)
        post_ref = db.collection('posts').document(post_id)
        post_doc_snapshot = post_ref.get() # Get a snapshot for initial check
        if not post_doc_snapshot.exists:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = FirestoreCommentSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            parent_comment_id = data.get('parent_comment_id')

            if parent_comment_id:
                # Verify parent comment exists
                parent_comment_ref = post_ref.collection('comments').document(parent_comment_id)
                if not parent_comment_ref.get().exists:
                    return Response({"error": "Parent comment not found"}, status=status.HTTP_400_BAD_REQUEST)
            
            current_user = request.user
            if hasattr(current_user, 'student'):
                author_name = current_user.student.name
            elif hasattr(current_user, 'organization'):
                author_name = current_user.organization.organization_name
            
            comment_payload = {
                'post_id': post_id, # Redundant if in subcollection, but useful for queries
                'author_id': user_id,
                'author_name': author_name, 
                'text': data['text'],
                'timestamp': firestore.SERVER_TIMESTAMP,
                # Add other fields like parent_comment_id for replies, etc.
                'parent_comment_id': parent_comment_id if parent_comment_id else None,
                'reply_count': 0 if not parent_comment_id else None, # Only top-level comments track reply_count
            }

            try:
                user_name = ""
                user_profile_pic_url = request.user.profile_pic_url
                if hasattr(request.user, 'student'):
                    user_name = request.user.student.name
                elif hasattr(request.user, 'organization'):
                    user_name = request.user.organization.organization_name
                else:
                    user_name = request.user.email

                # Define the transactional function
                # It takes the transaction object and any other arguments it needs
                @firestore.transactional
                def create_comment_and_increment_count(transaction, current_post_ref, payload):
                    # Re-read post document within the transaction to ensure latest state
                    # This read helps Firestore detect conflicts and retry the transaction if needed.
                    current_post_doc_in_tx = current_post_ref.get(transaction=transaction)
                    if not current_post_doc_in_tx.exists:
                        # If the post was deleted concurrently, this transaction will fail.
                        raise ValueError("Post not found during transaction.")

                    # Add the new comment document to the subcollection
                    # Get a new auto-ID document reference for the comment
                    new_comment_ref = current_post_ref.collection('comments').document()
                    transaction.set(new_comment_ref, payload)

                    # Increment the comment_count on the parent Post document
                    transaction.update(current_post_ref, {
                        'comment_count': firestore.Increment(1)
                    })

                    if 'parent_comment_id' in payload and payload['parent_comment_id']:
                        parent_comment_ref = current_post_ref.collection('comments').document(payload['parent_comment_id'])
                        transaction.update(parent_comment_ref, {
                            'reply_count': firestore.Increment(1)
                        })
                    
                    return new_comment_ref.id # Return the ID of the newly created comment

                # Run the transactional function.
                # It's called like a regular function, and db.transaction() is implicitly passed.
                # db.transaction() will retry the function automatically on contention.
                new_comment_id = create_comment_and_increment_count(db.transaction(), post_ref, comment_payload)



                # Fetch the parent's author for notification if it's a reply
                target_user = None
                notification_title = ""
                
                if parent_comment_id:
                    # Case 1: Reply to a comment
                    parent_comment_doc = post_ref.collection('comments').document(parent_comment_id).get()
                    if parent_comment_doc.exists:
                        parent_author_id = parent_comment_doc.to_dict().get('author_id')
                        if parent_author_id and parent_author_id != str(request.user.id):
                            target_user = User.objects.get(id=parent_author_id)
                            notification_title = "New Reply"
                    
                else:
                    # Case 2: New comment on a post
                    post_author_id = post_doc_snapshot.to_dict().get('author_id')
                    if post_author_id and post_author_id != str(request.user.id):
                        target_user = User.objects.get(id=post_author_id)
                        notification_title = "New Comment on Your Post"
                
                # Send the push notification if a target user was found
                if target_user:
                    send_push_notification(
                        user=target_user,
                        title=notification_title,
                        body=f"{user_name} commented: {comment_payload['text'][:50]}...",
                        data={
                            "type": "comment" if not parent_comment_id else "reply",
                            "post_id": post_id,
                            "comment_id": new_comment_id,
                            "commenter_id": user_id,
                            "commenter_profile_pic_url": user_profile_pic_url,
                        }
                    )
                
                created_comment_doc = post_ref.collection('comments').document(new_comment_id).get()
                created_comment_data = created_comment_doc.to_dict()
                created_comment_data['id'] = new_comment_id
                
                return Response(created_comment_data, status=status.HTTP_201_CREATED)

            except User.DoesNotExist:
                logger.warning("Notification target user not found.")
                # We can continue since the comment was still created successfully
                return Response(created_comment_data, status=status.HTTP_201_CREATED)
            except ValueError as ve:
                logger.error(f"Transaction failed: {str(ve)}")
                return Response({"error": f"Transaction failed: {str(ve)}"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error creating comment: {e}", exc_info=True)
                return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailFirestoreView(APIView):
    """
    Retrieve, update, or delete a comment for a specific post.
    URL: /api/posts/{post_id}/comments/{comment_id}/
    """
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    authentication_classes = [JWTAuthentication]

    def get_comment_ref(self, post_id, comment_id):
        return db.collection('posts').document(post_id).collection('comments').document(comment_id)

    def put(self, request, post_id, comment_id):
        comment_ref = self.get_comment_ref(post_id, comment_id)
        comment_doc = comment_ref.get()
        if not comment_doc.exists:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        comment_data = comment_doc.to_dict()
        if comment_data.get('author_id') != str(request.user.id):
            return Response({"error": "You do not have permission to edit this comment."}, status=status.HTTP_403_FORBIDDEN)

        serializer = FirestoreCommentSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            update_payload = serializer.validated_data
            if not update_payload:
                return Response({"error": "No data provided for update."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                comment_ref.update(update_payload)
                updated_comment = comment_ref.get().to_dict()
                updated_comment['id'] = comment_id
                return Response(updated_comment, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, post_id, comment_id):
        # Use a transaction to ensure atomic updates
        @firestore.transactional
        def delete_comment_and_decrement_counts(transaction, post_ref, comment_ref):
            comment_doc = comment_ref.get(transaction=transaction)
            if not comment_doc.exists:
                raise ValueError("Comment not found during transaction.")

            comment_data = comment_doc.to_dict()
            if comment_data.get('author_id') != str(request.user.id):
                # The transaction will be rolled back and an exception raised
                raise PermissionError("You do not have permission to delete this comment.")
            
            # Delete the comment
            transaction.delete(comment_ref)

            # Decrement comment_count on the post
            transaction.update(post_ref, {
                'comment_count': firestore.Increment(-1)
            })

            # Check if it was a reply and decrement the parent's reply_count
            parent_comment_id = comment_data.get('parent_comment_id')
            if parent_comment_id:
                parent_comment_ref = post_ref.collection('comments').document(parent_comment_id)
                transaction.update(parent_comment_ref, {
                    'reply_count': firestore.Increment(-1)
                })
            
            # If the deleted comment was a top-level comment, also find and delete its replies
            # This is critical for data integrity!
            if not parent_comment_id:
                replies_query = post_ref.collection('comments').where('parent_comment_id', '==', comment_id).stream()
                for reply_doc in replies_query:
                    transaction.delete(reply_doc.reference)
                    # We don't need to decrement post's count for these since they are
                    # already covered by the top-level comment's count.

        try:
            post_ref = db.collection('posts').document(post_id)
            comment_ref = self.get_comment_ref(post_id, comment_id)
            
            delete_comment_and_decrement_counts(db.transaction(), post_ref, comment_ref)
            
            return Response(status=status.HTTP_204_NO_CONTENT)

        except PermissionError as pe:
            return Response({"error": str(pe)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommentListFirestoreView(APIView):
    """
    List comments for a specific post.
    URL: /api/posts/{post_id}/comments/
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self, request, post_id):
        post_ref = db.collection('posts').document(post_id)
        if not post_ref.get().exists:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Step 1: Fetch ALL comments for the post.
            comments_ref = post_ref.collection('comments').order_by('timestamp', direction=firestore.Query.DESCENDING)
            docs = comments_ref.stream()

            comments_by_id = {}
            author_ids = set()

            # Step 2: Organize comments into a dictionary and gather author IDs.
            for doc in docs:
                comment_data = doc.to_dict()
                comment_data['id'] = doc.id
                comment_data['replies'] = []  # Initialize a list for replies
                comments_by_id[doc.id] = comment_data

                if 'author_id' in comment_data:
                    author_ids.add(str(comment_data['author_id']))

            # Step 3: Hydrate authors from Postgres in a single query.
            authors_map = {}
            if author_ids:
                authors_from_postgres = User.objects.filter(id__in=author_ids).only(
                    'id', 'email', 'profile_pic_url', 'is_verified'
                )
                for author in authors_from_postgres:
                    author_name = None
                    display_name_slug = None
                    exclusive = False
                    faculty = None
                    department = None

                    if hasattr(author, 'student'):
                        author_name = author.student.name
                        display_name_slug = getattr(author.student, 'display_name_slug', None)
                        faculty = getattr(author.student, 'faculty', None)
                        department = getattr(author.student, 'department', None)
                    elif hasattr(author, 'organization'):
                        author_name = author.organization.organization_name
                        display_name_slug = getattr(author.organization, 'display_name_slug', None)
                        exclusive = getattr(author.organization, 'exclusive', False)

                    authors_map[str(author.id)] = {
                        "id": str(author.id),
                        "name": author_name,
                        "display_name_slug": display_name_slug,
                        "profile_pic_url": author.profile_pic_url,
                        "is_verified": author.is_verified,
                        "exclusive": exclusive,
                        "faculty": faculty,
                        "department": department,
                    }

            # Step 4: Build the nested comment/reply structure and apply author info.
            top_level_comments = []
            for comment_id, comment_data in comments_by_id.items():
                author_id = str(comment_data.get('author_id'))
                author_info = authors_map.get(author_id, {})

                # Add all author-related keys to the comment data, regardless of it being a reply or top-level.
                # This ensures consistent data structure for all comments.
                comment_data['author_name'] = author_info.get('name')
                comment_data['author_display_name_slug'] = author_info.get('display_name_slug')
                comment_data['author_profile_pic_url'] = author_info.get('profile_pic_url')
                comment_data['author_faculty'] = author_info.get('faculty')
                comment_data['author_department'] = author_info.get('department')
                comment_data['author_exclusive'] = author_info.get('exclusive')

                parent_id = comment_data.get('parent_comment_id')
                if parent_id and parent_id in comments_by_id:
                    # This is a reply, so add it to its parent's replies list.
                    comments_by_id[parent_id]['replies'].append(comment_data)
                else:
                    # This is a top-level comment.
                    top_level_comments.append(comment_data)

            # Step 5: Sort replies by timestamp for correct ordering
            # Sort in ascending order (oldest to newest) for a conversational thread.
            for comment in comments_by_id.values():
                comment['replies'].sort(key=lambda x: x.get('timestamp'), reverse=False)

            # Step 6: Paginate the top-level comments in memory.
            page_size = int(request.query_params.get("page_size", 10))
            page_number = int(request.query_params.get("page", 1))
            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            paginated_comments = top_level_comments[start_index:end_index]

            # Step 7: Return the structured data.
            # The data is already formatted, so we can return it directly.
            return Response({
                "results": paginated_comments,
                "next_page": page_number + 1 if end_index < len(top_level_comments) else None,
                "total_comments": len(top_level_comments),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Failed to retrieve comments: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




##
## Like Views (Firestore)
##
# class LikeToggleFirestoreView(APIView):
#     """
#     Like or unlike a post. A single endpoint to toggle the like status.
#     URL: /api/posts/{post_id}/like/
#     """
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, post_id): # post_id from URL
#         user_id = str(request.user.id)
#         post_ref = db.collection('posts').document(post_id)
#         like_ref = post_ref.collection('likes').document(user_id) # Document ID is the user's ID

#         try:
#             post_doc = post_ref.get()
#             if not post_doc.exists:
#                 return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

#             like_doc = like_ref.get()
            
#             # Use a Firestore transaction to ensure atomic like/unlike and count update
#             @firestore.transactional
#             def toggle_like_transaction(transaction, current_post_ref, current_like_ref, current_like_exists):
#                 if current_like_exists:
#                     transaction.delete(current_like_ref)
#                     transaction.update(current_post_ref, {'like_count': firestore.Increment(-1)})
#                     return False # Unliked
#                 else:
#                     transaction.set(current_like_ref, {'liked_at': firestore.SERVER_TIMESTAMP})
#                     transaction.update(current_post_ref, {'like_count': firestore.Increment(1)})
#                     return True # Liked

#             transaction = db.transaction()
#             liked_now = toggle_like_transaction(transaction, post_ref, like_ref, like_doc.exists)

#             if liked_now:
#                 return Response({"message": "Post liked successfully."}, status=status.HTTP_201_CREATED)
#             else:
#                 return Response({"message": "Post unliked successfully."}, status=status.HTTP_200_OK) # Or 204 if you prefer

#         except Exception as e:
#             return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class LikeToggleFirestoreView(APIView):
    """
    Like or unlike a post. A single endpoint to toggle the like status.
    URL: /api/posts/{post_id}/like/
    """
    permission_classes = [permissions.IsAuthenticated, IsVerified] # Ensure user is authenticated and verified
    authentication_classes = [JWTAuthentication]

    def post(self, request, post_id): # post_id from URL
        user_id = str(request.user.id)
        post_ref = db.collection('posts').document(post_id)
        like_ref = post_ref.collection('likes').document(user_id) # Document ID is the user's ID

        try:
            user_name = ""
            if hasattr(request.user, 'student'):
                user_name = request.user.student.name
            elif hasattr(request.user, 'organization'):
                user_name = request.user.organization.organization_name
            else:
                user_name = request.user.email
            
            post_doc = post_ref.get()
            if not post_doc.exists:
                return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

            like_doc = like_ref.get()
            
            # Use a Firestore transaction to ensure atomic like/unlike and count update
            @firestore.transactional
            def toggle_like_transaction(transaction, current_post_ref, current_like_ref, current_like_exists):
                # Define the weight for a like in the trending score
                LIKE_TREND_WEIGHT = 1 

                if current_like_exists:
                    transaction.delete(current_like_ref)
                    transaction.update(current_post_ref, {
                        'like_count': firestore.Increment(-1),
                        'trending_score': firestore.Increment(-LIKE_TREND_WEIGHT), # Decrement trending score
                        'last_engagement_at': firestore.SERVER_TIMESTAMP # Update last engagement time
                    })
                    return False # Unliked
                else:
                    transaction.set(current_like_ref, {'liked_at': firestore.SERVER_TIMESTAMP})
                    transaction.update(current_post_ref, {
                        'like_count': firestore.Increment(1),
                        'trending_score': firestore.Increment(LIKE_TREND_WEIGHT), # Increment trending score
                        'last_engagement_at': firestore.SERVER_TIMESTAMP # Update last engagement time
                    })
                    return True # Liked

            transaction = db.transaction()
            liked_now = toggle_like_transaction(transaction, post_ref, like_ref, like_doc.exists)

            # --- Send notification to post author if liked ---
            if liked_now:
                post_data = post_doc.to_dict()
                post_author_id = post_data.get('author_id')
                if post_author_id and post_author_id != user_id:
                    try:
                        post_author = User.objects.get(id=post_author_id)
                        send_push_notification(
                            user=post_author,
                            title="Your post was liked!",
                            body=f"{user_name} liked your post.",
                            data={"type": "like", "post_id": post_id}
                        )
                    except User.DoesNotExist:
                        pass

            # --- Update Redis user likes cache asynchronously (best-effort) ---
            try:
                r = get_redis_client()
                likes_key = f"user:likes:{user_id}"
                if liked_now:
                    r.sadd(likes_key, post_id)
                    r.expire(likes_key, REDIS_LIKES_TTL)
                else:
                    r.srem(likes_key, post_id)
            except Exception:
                logger.exception("Failed to update redis user likes cache")

            if liked_now:
                return Response({"message": "Post liked successfully."}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message": "Post unliked successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            # It's good practice to log the full exception here for debugging
            logging.error(f"Error toggling like for post {post_id}: {e}")
            return Response({"error": f"Firestore error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LikeListFirestoreView(APIView):
    """
    List all likes for a specific post from Firestore.
    This view returns basic like information directly from Firestore,
    without hydrating user details from PostgreSQL.
    URL: /api/posts/{post_id}/likes/
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self, request, post_id):
        post_ref = db.collection('posts').document(post_id)
        # Check if the post itself exists
        if not post_ref.get().exists:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Reference to the 'likes' subcollection of the specific post
            likes_ref = post_ref.collection('likes').order_by('liked_at', direction=firestore.Query.ASCENDING)
            docs = likes_ref.stream() # Get all like documents

            raw_likes_list = []
            for doc in docs:
                like_data = doc.to_dict()
                
                # Add the Firestore document ID to the dictionary.
                # Since you're likely using the user_id as the document ID for a like,
                # 'id' will be the user_id. We also explicitly set 'user_id' in the dict
                # to match the serializer's expectation clearly.
                like_data['id'] = doc.id
                like_data['user_id'] = doc.id # The user_id is the document ID of the like

                # Add the post_id from the URL context, as it's not stored in the 'like' document itself
                # if the 'likes' are just a subcollection with user_id and liked_at.
                like_data['post_id'] = post_id 
                
                raw_likes_list.append(like_data)

            # Serialize the data. 'many=True' because we are serializing a list.
            serializer = FirestoreLikeOutputSerializer(raw_likes_list, many=True)
            
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            # Catch any other potential errors during Firestore interaction
            return Response({"error": f"Failed to retrieve likes: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RewardPointSubmitView(generics.GenericAPIView, CreateModelMixin): # Rename and use GenericAPIView + Mixin

    serializer_class = RewardPointSerializer
    permission_classes = [permissions.IsAuthenticated]

    # The POST method is handled by the CreateModelMixin, 
    # and the Serializer's create method handles the UPSERT logic via IntegrityError.
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class UserPointsDetailView(generics.RetrieveAPIView):
    """
    Endpoint to retrieve the total points received by ANY user, 
    identified by their primary key (pk) in the URL.
    """
    serializer_class = PrivatePointsProfileSerializer
    
    # Authentication is still required to access the API (if you want to prevent
    # unauthenticated crawling), but we remove the strict privacy enforcement 
    # of the previous version.
    permission_classes = [permissions.IsAuthenticated] 
    
    # Specify the queryset so DRF knows where to look for the object
    queryset = User.objects.all() 
    

# class TrendingPostsFirestoreView(generics.ListAPIView):
#     """
#     Retrieve a list of trending posts from Firestore.
#     Trending is based on a 'trending_score' field and filtered by recent engagement.
#     """
#     permission_classes = [permissions.AllowAny] 
#     serializer_class = FirestorePostOutputSerializer # Use the serializer for output formatting

#     def get_queryset(self):
#         posts_ref = db.collection('posts')

#         # --- Define the time window for "recent" engagement ---
#         # Get posts with engagement in the last 7 days.
#         # This value can be made configurable (e.g., via query parameters in a more complex API)
#         RECENT_ENGAGEMENT_DAYS = 7 
        
#         # Calculate the cutoff datetime. Always use UTC for consistency with Firestore timestamps.
#         now_utc = datetime.now(timezone.utc)
#         from_datetime_utc = now_utc - timedelta(days=RECENT_ENGAGEMENT_DAYS)

#         logging.info(f"Fetching trending posts engaged since: {from_datetime_utc.isoformat()}")

#         # ----------------------------------------------------------------------
#         # Firestore Query Construction:
#         # 1. Filter by recent engagement: `where('last_engagement_at', '>=', from_datetime_utc)`
#         # 2. Order by recency: `order_by('last_engagement_at', direction=firestore.Query.DESCENDING)`
#         # 3. Order by trending score (secondary sort): `order_by('trending_score', direction=firestore.Query.DESCENDING)`
#         #
#         # IMPORTANT: For this combined query, you MUST create a composite index in Firestore.
#         # The required index will be on (last_engagement_at ASC, trending_score DESC).
#         # If you get a Firestore error about a "missing index", follow the URL provided
#         # in the error message to create it in the Firebase console.
#         # ----------------------------------------------------------------------
        
#         query = posts_ref.where('last_engagement_at', '>=', from_datetime_utc) \
#                          .order_by('last_engagement_at', direction=firestore.Query.DESCENDING) \
#                          .order_by('trending_score', direction=firestore.Query.DESCENDING) \
#                          .limit(20) # Limit the number of trending posts returned (e.g., top 20)

#         try:
#             docs = query.stream()
#             # Convert Firestore documents to a list of dictionaries for the serializer
#             posts_list = []
#             for doc in docs:
#                 post_data = doc.to_dict()
#                 post_data['id'] = doc.id # Add the document ID to the dictionary
#                 posts_list.append(post_data)
#             return posts_list # Return a list of dicts
#         except Exception as e:
#             logging.error(f"Failed to fetch trending posts from Firestore: {e}", exc_info=True)
#             # Depending on your error handling, you might return an empty list or raise an APIException
#             return [] 

#     def list(self, request, *args, **kwargs):
#         posts_data = self.get_queryset()

#         # Add has_liked status (already in your code)
#         for post in posts_data:
#             post_id = post.get('id')
#             if request.user.is_authenticated:
#                 user_id = str(request.user.id)
#                 try:
#                     like_doc = db.collection('posts').document(post_id).collection('likes').document(user_id).get()
#                     post['has_liked'] = like_doc.exists
#                 except Exception as e:
#                     logging.warning(f"Error checking like status for post {post_id}: {e}")
#                     post['has_liked'] = False
#             else:
#                 post['has_liked'] = False

#         # --- Hydrate author info ---
#         author_ids = list(set(str(post['author_id']) for post in posts_data if 'author_id' in post))
#         authors_from_postgres = User.objects.filter(id__in=author_ids).only('id', 'email', 'profile_pic_url', 'is_verified')
#         authors_map = {}
#         for author in authors_from_postgres:
#             author_name = None
#             display_name_slug = None
#             if hasattr(author, 'student'):
#                 author_name = author.student.name
#                 display_name_slug = getattr(author.student, 'display_name_slug', None)
#             elif hasattr(author, 'organization'):
#                 author_name = author.organization.organization_name
#                 display_name_slug = getattr(author.organization, 'display_name_slug', None)

#             authors_map[str(author.id)] = {
#                 "id": author.id,
#                 "email": author.email,
#                 "profile_pic_url": author.profile_pic_url,
#                 "name": author_name,
#                 "display_name_slug": display_name_slug,
#                 "is_verified": author.is_verified if hasattr(author, 'is_verified') else False,
#             }

#         # --- Serialize with authors_map ---
#         serializer = self.get_serializer(posts_data, many=True, context={'authors_map': authors_map})
#         return Response(serializer.data, status=status.HTTP_200_OK)

class ExclusiveOrgsRecentPostsView(APIView):
    """
    List recent posts from exclusive organizations in a randomized, paginated order.
    Uses a session ID for consistent pagination.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            # --- Pagination and Session parameters ---
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
            session_id = request.query_params.get("session_id")

            # Generate a new session ID if none is provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Use a local RNG for deterministic session behavior
            rng = get_session_rng(session_id)

            # 1. Get all exclusive org user IDs
            exclusive_orgs = Organization.objects.filter(exclusive=True)
            exclusive_org_user_ids_str = [str(org.user_id) for org in exclusive_orgs]
            
            if not exclusive_org_user_ids_str:
                return Response({"results": [], "session_id": session_id, "has_next": False}, status=200)

            current_user_id = str(request.user.id) if request.user.is_authenticated else None
            
            # 2. Fetch ALL posts from exclusive orgs and prepare for shuffling
            all_posts = []
            
            # Since Firestore has a limit of 10 for 'in' queries, we must chunk the list
            def chunk(lst, size):
                for i in range(0, len(lst), size):
                    yield lst[i:i + size]
            
            # Firestore requires the 'in' list to be non-empty
            if exclusive_org_user_ids_str:
                for user_id_chunk in chunk(exclusive_org_user_ids_str, 10):
                    posts_query = db.collection("posts").where("author_id", "in", user_id_chunk)
                    for doc in posts_query.stream():
                        post_data = doc.to_dict()
                        post_data['id'] = doc.id
                        post_data['has_liked'] = False
                        post_data['has_rewarded'] = False
                        all_posts.append(post_data)

            # 3. Shuffle the ENTIRE list of posts
            # Deterministic session ordering for exclusive org posts
            session_sort_posts(all_posts, session_id, recency_weight=0.08)
            
            # --- Pagination ---
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            paginated_posts = all_posts[start_index:end_index]
            has_next = end_index < len(all_posts)

            # 4. Hydrate authors map (This part remains largely the same)
            authors_map = {}
            author_ids = [post['author_id'] for post in paginated_posts]
            for author in User.objects.filter(id__in=author_ids):
                try:
                    org = author.organization
                    authors_map[str(author.id)] = {
                        "id": author.id,
                        "email": author.email,
                        "profile_pic_url": author.profile_pic_url,
                        "name": org.organization_name,
                        "is_verified": author.is_verified,
                        "exclusive": org.exclusive,
                        "display_name_slug": getattr(org, 'display_name_slug', None),
                    }
                except Organization.DoesNotExist:
                    continue

            serializer = FirestorePostOutputSerializer(paginated_posts, many=True, context={'authors_map': authors_map})

            # Batch has_liked for current user
            if current_user_id and paginated_posts:
                try:
                    post_ids = [p['id'] for p in paginated_posts if 'id' in p]
                    liked_set = batch_has_liked(current_user_id, post_ids)
                    # Batched rewarded presence for this user
                    try:
                        rewarded_ids = RewardPointTransaction.objects.filter(
                            giver=request.user,
                            firestore_post_id__in=post_ids
                        ).values_list('firestore_post_id', flat=True)
                        rewarded_set = {str(r) for r in rewarded_ids}
                    except Exception:
                        rewarded_set = set()
                    # Reward totals per post
                    try:
                        reward_totals_qs = RewardPointTransaction.objects.filter(
                            firestore_post_id__in=post_ids
                        ).values('firestore_post_id').annotate(total=Sum('points'))
                        reward_map = {r['firestore_post_id']: r['total'] for r in reward_totals_qs}
                    except Exception:
                        reward_map = {}

                    for p in paginated_posts:
                        pid = str(p.get('id'))
                        p['has_liked'] = pid in liked_set
                        p['has_rewarded'] = pid in rewarded_set
                        p['reward_point_count'] = reward_map.get(p.get('id'), 0)
                except Exception:
                    pass

            return Response({
                "results": serializer.data,
                "session_id": session_id,
                "page": page,
                "page_size": page_size,
                "has_next": has_next
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching exclusive org posts: {e}", exc_info=True)
            return Response({"detail": "Error fetching posts."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class UserPostsFirestoreView(APIView):
    """
    List all posts by a specific user identified by their user_id, including shares.
    URL: /api/users/{user_id}/posts/
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsVerified]
    authentication_classes = [JWTAuthentication]

    def get(self, request, user_id):
        try:
            page_size = int(request.query_params.get("page_size", 20))
            start_after = request.query_params.get("start_after")  # Expecting a Firestore post ID

            posts_list = []
            shares_map = {}
            current_user_id = str(request.user.id) if request.user.is_authenticated else None

            # --- Authored Posts ---
            posts_query = db.collection('posts') \
                .where('author_id', '==', user_id) \
                .order_by('timestamp', direction=firestore.Query.DESCENDING)

            if start_after:
                try:
                    start_doc = db.collection('posts').document(start_after).get()
                    if start_doc.exists:
                        posts_query = posts_query.start_after(start_doc)
                except:
                    pass

            # Collect authored posts (no per-post reads for likes yet)
            authored_posts = []
            authored_post_ids = []
            for doc in posts_query.limit(50).stream():
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                post_data['has_liked'] = False
                post_data['is_shared'] = False
                post_data['has_rewarded'] = False
                authored_posts.append(post_data)
                authored_post_ids.append(doc.id)

            # --- Shared Posts ---
            shares_query = db.collection('shares') \
                .where('shared_by_id', '==', user_id) \
                .order_by('shared_at', direction=firestore.Query.DESCENDING)

            shared_posts = []
            original_post_ids = []
            for share_doc in shares_query.limit(50).stream():
                share_data = share_doc.to_dict()
                original_post_id = share_data.get('original_post_id')
                if not original_post_id:
                    continue

                # Add share metadata to shares_map
                share_data['id'] = share_doc.id
                if original_post_id not in shares_map:
                    shares_map[original_post_id] = []
                shares_map[original_post_id].append(share_data)

                # Collect original post ids for batch fetch
                original_post_ids.append(original_post_id)

            # Batch fetch original posts for shared posts
            if original_post_ids:
                # dedupe while preserving order
                seen = set()
                deduped_ids = []
                for pid in original_post_ids:
                    if pid not in seen:
                        seen.add(pid)
                        deduped_ids.append(pid)

                doc_refs = [db.collection('posts').document(pid) for pid in deduped_ids]
                try:
                    docs = list(db.get_all(doc_refs))
                except Exception:
                    docs = []

                for doc in docs:
                    if not doc.exists:
                        continue
                    post_data = doc.to_dict()
                    post_data['id'] = doc.id
                    post_data['is_shared'] = True
                    # attach the most recent share metadata for this post (if any)
                    shares_for_post = shares_map.get(doc.id, [])
                    if shares_for_post:
                        # shares were collected in descending shared_at order by the query
                        latest_share = shares_for_post[0]
                        post_data['shared_by_id'] = latest_share.get('shared_by_id')
                        post_data['shared_at'] = latest_share.get('shared_at')
                    post_data['has_liked'] = False
                    shared_posts.append(post_data)

            # --- Combine, sort, and paginate ---
            combined_posts = authored_posts + shared_posts
            combined_posts.sort(key=lambda x: x.get('shared_at') or x.get('timestamp'), reverse=True)

            paginated_posts = combined_posts[:page_size]
            next_cursor = paginated_posts[-1]['id'] if len(paginated_posts) == page_size else None

            # --- Batch hydrate has_liked, has_rewarded, and authors_map ---
            paginated_post_ids = [p['id'] for p in paginated_posts]

            # Batch has_liked via Redis-backed set
            liked_set = set()
            if current_user_id and paginated_post_ids:
                try:
                    liked_set = batch_has_liked(current_user_id, paginated_post_ids)
                except Exception:
                    liked_set = set()

            # Batch rewarded flags from Django model
            rewarded_set = set()
            if request.user.is_authenticated and paginated_post_ids:
                try:
                    rewarded_ids = RewardPointTransaction.objects.filter(
                        giver=request.user,
                        firestore_post_id__in=paginated_post_ids
                    ).values_list('firestore_post_id', flat=True)
                    rewarded_set = {str(rid) for rid in rewarded_ids}
                except Exception:
                    rewarded_set = set()

                # Reward totals per post for this page
                try:
                    reward_totals_qs = RewardPointTransaction.objects.filter(
                        firestore_post_id__in=paginated_post_ids
                    ).values('firestore_post_id').annotate(total=Sum('points'))
                    reward_map = {r['firestore_post_id']: r['total'] for r in reward_totals_qs}
                except Exception:
                    reward_map = {}

            # Apply flags
            for post in paginated_posts:
                pid = str(post.get('id'))
                post['has_liked'] = pid in liked_set
                post['has_rewarded'] = pid in rewarded_set
                post['reward_point_count'] = reward_map.get(post.get('id'), 0)

            # Hydrate authors via Redis cache + DB fallback
            author_ids = list({str(p.get('author_id')) for p in paginated_posts if p.get('author_id')})
            authors_map = {}
            if author_ids:
                try:
                    authors_map = hydrate_authors_map(author_ids)
                except Exception:
                    authors_map = {}

            serializer = FirestorePostOutputSerializer(
                paginated_posts, many=True,
                context={'authors_map': authors_map, 'shares_map': shares_map}
            )

            return Response({
                "results": serializer.data,
                "next_cursor": next_cursor
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Failed to retrieve posts for user: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FollowDepartmentView(APIView):
    """Endpoint for a student to suggest students to follow in their department.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        user = request.user

        try:
            current_student = Student.objects.select_related('user').get(user=user)
        except Student.DoesNotExist:
            return Response({"error": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        department = current_student.department
        if not department:
            return Response({"results": []}, status=status.HTTP_200_OK)

        # Fetch students in the same department, excluding already followed and self
        student_ct = ContentType.objects.get(model='student')
        follows_qs = Follow.objects.filter(
            follower_content_type=student_ct,
            follower_object_id=current_student.id
        )
        followed_student_ids = set(follows_qs.filter(
            followee_content_type=student_ct
        ).values_list('followee_object_id', flat=True))

        recommended_students = Student.objects.select_related('user').filter(
            department__iexact=department
        ).exclude(
            id__in=followed_student_ids
        ).exclude(
            user=user
        ).order_by('?')[:20]  # Limit to 20 suggestions

        users_data = []
        for student in recommended_students:
            user_obj = getattr(student, 'user', None)
            users_data.append({
                "type": "student",
                "id": student.id,
                "user_id": user_obj.id if user_obj else None,
                "name": student.name,
                "faculty": student.faculty,
                "department": student.department,
                "display_name_slug": getattr(student, "display_name_slug", None),
                "profile_pic_url": getattr(user_obj, "profile_pic_url", None),
                "bio": getattr(user_obj, "bio", None),
                "is_following": False,
                "is_verified": getattr(user_obj, "is_verified", False),
            })

        return Response({"results": users_data}, status=status.HTTP_200_OK)
        

class WhoToFollowView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [JWTAuthentication] # Keep this as per your setup

    def get(self, request, *args, **kwargs):
        user = request.user
        LIMIT = 20 # Define the limit once

        try:
            # 1. Fetch current student and related data efficiently
            current_student = Student.objects.select_related('user').get(user=user)
        except Student.DoesNotExist:
            return Response({"error": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Pre-fetch ContentTypes once
        try:
            student_ct = ContentType.objects.get(model='student')
            org_ct = ContentType.objects.get(model='organization')
        except ContentType.DoesNotExist:
            # Handle case where ContentTypes aren't found, though rare
            return Response({"error": "Content type configuration error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Get followed IDs in two efficient queries
        follows_qs = Follow.objects.filter(
            follower_content_type=student_ct,
            follower_object_id=current_student.id
        )
        
        # Use a list comprehension with .distinct() for better SQL optimization
        followed_student_ids = set(follows_qs.filter(
            followee_content_type=student_ct
        ).values_list('followee_object_id', flat=True))
        
        followed_org_ids = set(follows_qs.filter(
            followee_content_type=org_ct
        ).values_list('followee_object_id', flat=True))

        # 4. Build keyword-based recommendation query
        keywords = []
        # Use a consistent list of profile attributes for recommendation
        for attr in ['department', 'faculty', 'religion']:
            value = getattr(current_student, attr, None)
            if value:
                # Add value to keywords, ensuring it's treated as a single search term if needed
                keywords.append(value) 

        # 5. Get recommended Students (optimizing with select_related)
        student_query = Q()
        for kw in set(keywords): # Use set to avoid redundant keywords
            # Combining the lookups with OR logic
            student_query |= (
                Q(department__icontains=kw) | 
                Q(faculty__icontains=kw) | 
                Q(religion__icontains=kw)
            )
        
        recommended_students = Student.objects.select_related('user').filter(
            student_query
        ).exclude(
            id__in=followed_student_ids
        ).exclude(
            user=user # Exclude self
        ).order_by('?')[:LIMIT] # Use '?' for random or consider a popularity/activity score

        # 6. Get recommended Organizations (optimizing with select_related)
        org_query = Q()
        for kw in set(keywords):
            # Organization fields to match on
            org_query |= (
                Q(organization_name__icontains=kw) | 
                Q(user__bio__icontains=kw)
            )

        # Separate filter for exclusive organizations for clarity
        exclusive_orgs_qs = Organization.objects.select_related('user').filter(
            exclusive=True
        ).exclude(
            id__in=followed_org_ids
        )

        recommended_orgs_qs = Organization.objects.select_related('user').filter(
            org_query
        ).exclude(
            id__in=followed_org_ids
        )
        
        # Combine, ensure uniqueness, and take the top N (ordering might matter here)
        all_recommended_orgs = (exclusive_orgs_qs | recommended_orgs_qs).distinct().order_by('?')[:LIMIT]


        # 7. Serialize Data (can be refactored into a Serializer)
        users_data = []

        # Students
        users_data.extend(
            self._serialize_student(s, followed_student_ids) 
            for s in recommended_students
        )
        
        # Organizations
        users_data.extend(
            self._serialize_organization(org, followed_org_ids) 
            for org in all_recommended_orgs
        )

        # 8. Truncate (if necessary, though limits were applied) and return
        return Response(users_data[:LIMIT], status=status.HTTP_200_OK)

    # Helper methods for cleaner serialization (optional but recommended)
    def _serialize_student(self, student, followed_ids):
        """Helper to serialize a Student instance."""
        user = getattr(student, 'user', None)
        return {
            "type": "student",
            "id": student.id,
            "user_id": user.id if user else None,
            "name": student.name,
            "faculty": student.faculty,
            "department": student.department,
            "display_name_slug": getattr(student, "display_name_slug", None),
            "profile_pic_url": getattr(user, "profile_pic_url", None),
            "bio": getattr(user, "bio", None),
            "is_following": student.id in followed_ids,
            "is_verified": getattr(user, "is_verified", False),
        }

    def _serialize_organization(self, org, followed_ids):
        """Helper to serialize an Organization instance."""
        user = getattr(org, 'user', None)
        return {
            "type": "organization",
            "id": org.id,
            "user_id": user.id if user else None,
            "name": org.organization_name,
            "display_name_slug": org.display_name_slug,
            "profile_pic_url": getattr(user, "profile_pic_url", None),
            "bio": getattr(user, "bio", None),
            "exclusive": org.exclusive,
            "is_following": org.id in followed_ids,
            "is_verified": getattr(user, "is_verified", False),
        }

class VerifiedOrgBadge(APIView):
    """Checks if the Organization is Exclusive and Verified"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user
        try:
            org = Organization.objects.get(user=user)
            if org.exclusive and org.user.is_verified:
                return Response({"is_verified": True}, status=status.HTTP_200_OK)
            else:
                return Response({"is_verified": False}, status=status.HTTP_200_OK)
        except Organization.DoesNotExist:
            return Response({"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)

REDIS_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')

class RewardWeeklyLeaderboardView(APIView):
    """
    View to retrieve the weekly leaderboard for rewards.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        limit = int(request.query_params.get('limit', 100))
        # default Redis url fallback if not in settings
        r = redis.Redis.from_url(REDIS_URL)
        # Optional: accept `week_start` query param to look up a specific ISO week.
        # Accept formats: YYYY-MM-DD (any date in the week) or YYYY-Www (e.g. 2025-W46)
        week_param = request.query_params.get('week_start')
        dt = None
        if week_param:
            try:
                # Try parsing as ISO date first
                dt = datetime.fromisoformat(week_param).date()
            except Exception:
                try:
                    # Try ISO week representation like '2025-W46'
                    if '-W' in week_param:
                        parts = week_param.split('-W')
                        y = int(parts[0])
                        w = int(parts[1])
                        dt = datetime.fromisocalendar(y, w, 1).date()
                except Exception:
                    return Response({'error': 'Invalid week_start format. Use YYYY-MM-DD or YYYY-Www'}, status=status.HTTP_400_BAD_REQUEST)

        key = key_weekly('points', dt)
        members = r.zrevrange(key, 0, limit - 1, withscores=True)
        user_ids = [int(m.decode() if isinstance(m, bytes) else m) for m, _ in members]
        users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}
        results = []
        for member, score in members:
            uid = member.decode() if isinstance(member, bytes) else member
            u = users_map.get(int(uid))
            results.append({
                'user_id': uid,
                'score': score,
                'name': (getattr(u, 'student', None) and u.student.name) or (getattr(u, 'organization', None) and u.organization.organization_name) or (u.email if u else None),
                'profile_pic_url': getattr(u, 'profile_pic_url', None) if u else None,
            })
        return Response({'results': results}, status=status.HTTP_200_OK)


class RewardMonthlyLeaderboardView(APIView):
    """
    View to retrieve the monthly leaderboard for rewards.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        limit = int(request.query_params.get('limit', 100))
        r = redis.Redis.from_url(REDIS_URL)
        key = key_monthly('points')
        members = r.zrevrange(key, 0, limit - 1, withscores=True)
        user_ids = [int(m.decode() if isinstance(m, bytes) else m) for m, _ in members]
        users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}
        results = []
        for member, score in members:
            uid = member.decode() if isinstance(member, bytes) else member
            u = users_map.get(int(uid))
            results.append({
                'user_id': uid,
                'score': score,
                'name': (getattr(u, 'student', None) and u.student.name) or (getattr(u, 'organization', None) and u.organization.organization_name) or (u.email if u else None),
                'profile_pic_url': getattr(u, 'profile_pic_url', None) if u else None,
            })
        return Response({'results': results}, status=status.HTTP_200_OK)

class RewardAlltimeLeaderboardView(APIView):
    """
    View to retrieve the alltime leaderboard for rewards.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        limit = int(request.query_params.get('limit', 100))
        r = redis.Redis.from_url(REDIS_URL)
        # For now we use the alltime key for yearly; you can add explicit yearly keys if desired
        key = key_alltime('points')
        members = r.zrevrange(key, 0, limit - 1, withscores=True)
        user_ids = [int(m.decode() if isinstance(m, bytes) else m) for m, _ in members]
        users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}
        results = []
        for member, score in members:
            uid = member.decode() if isinstance(member, bytes) else member
            u = users_map.get(int(uid))
            results.append({
                'user_id': uid,
                'score': score,
                'name': (getattr(u, 'student', None) and u.student.name) or (getattr(u, 'organization', None) and u.organization.organization_name) or (u.email if u else None),
                'profile_pic_url': getattr(u, 'profile_pic_url', None) if u else None,
            })
        return Response({'results': results}, status=status.HTTP_200_OK)


class TopPostersView(APIView):
    """
    Return users ranked by total number of posts (all-time).

    Behavior:
    - If Redis key `leaderboard:posts:alltime` exists and has members, return top-N from Redis.
    - Otherwise, if query param `compute=true` is provided, scan Firestore posts collection,
      compute counts per `author_id`, optionally populate Redis, and return top-N.
    - If neither condition is met, return 404 with instructions to run backfill or use compute=true.

    Query params:
    - `limit` (int, default 100)
    - `compute` (bool, optional) — when true, compute counts from Firestore synchronously.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        limit = int(request.query_params.get('limit', 100))
        compute = request.query_params.get('compute', 'false').lower() in ('1', 'true', 'yes')

        # Try Redis first
        try:
            r = get_redis_client()
            key = 'leaderboard:posts:alltime'
            members = r.zrevrange(key, 0, limit - 1, withscores=True)
            if members:
                user_ids = [int(m.decode() if isinstance(m, bytes) else m) for m, _ in members]
                users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}
                results = []
                for member, score in members:
                    uid = member.decode() if isinstance(member, bytes) else member
                    u = users_map.get(int(uid))
                    results.append({
                        'user_id': uid,
                        'score': int(score),
                        'name': (getattr(u, 'student', None) and u.student.name) or (getattr(u, 'organization', None) and u.organization.organization_name) or (u.email if u else None),
                        'profile_pic_url': getattr(u, 'profile_pic_url', None) if u else None,
                    })
                return Response({'results': results}, status=status.HTTP_200_OK)
        except Exception:
            # Redis may be unavailable; fall through to compute option
            logging.exception('Redis unavailable when fetching top posters')

        if not compute:
            # Enqueue background backfill task and return 202 Accepted
            try:
                recompute_posts_alltime.delay()
                return Response({'status': 'accepted', 'message': 'Background backfill started. Please retry after a short while.'}, status=status.HTTP_202_ACCEPTED)
            except Exception:
                logging.exception('Failed to enqueue posts backfill task')
                return Response({'error': 'No cached data and failed to start backfill. Try ?compute=true or run the backfill management command.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Compute counts from Firestore (synchronous; may be slow)
        counts = {}
        try:
            posts_ref = db.collection('posts')
            for doc in posts_ref.stream():
                data = doc.to_dict()
                author_id = data.get('author_id')
                if not author_id:
                    continue
                counts[author_id] = counts.get(author_id, 0) + 1

            # Convert to sorted list
            sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]

            # Optionally populate Redis for future requests
            try:
                r = get_redis_client()
                pipe = r.pipeline()
                key = 'leaderboard:posts:alltime'
                # Replace the sorted set
                pipe.delete(key)
                for uid, cnt in sorted_items:
                    pipe.zadd(key, {str(uid): int(cnt)})
                # Set no expiry for alltime
                pipe.execute()
            except Exception:
                logging.exception('Failed to populate Redis with top posters')

            # Hydrate user info from Postgres
            user_ids = [int(uid) for uid, _ in sorted_items if str(uid).isdigit()]
            users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}
            results = []
            for uid, cnt in sorted_items:
                u = users_map.get(int(uid)) if str(uid).isdigit() else None
                results.append({
                    'user_id': uid,
                    'score': int(cnt),
                    'name': (getattr(u, 'student', None) and u.student.name) or (getattr(u, 'organization', None) and u.organization.organization_name) or (u.email if u else None),
                    'profile_pic_url': getattr(u, 'profile_pic_url', None) if u else None,
                })
            return Response({'results': results}, status=status.HTTP_200_OK)
        except Exception:
            logging.exception('Failed to compute top posters from Firestore')
            return Response({'error': 'Failed to compute top posters'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
