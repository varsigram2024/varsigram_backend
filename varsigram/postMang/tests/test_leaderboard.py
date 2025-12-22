from django.test import TestCase
from django.contrib.auth import get_user_model
from postMang.models import RewardPointTransaction
from postMang import tasks
from postMang.leaderboard_utils import key_weekly
from datetime import datetime, date
from unittest.mock import MagicMock, patch


User = get_user_model()


class LeaderboardTasksTest(TestCase):
    def setUp(self):
        # Create two users: author and giver
        self.author = User.objects.create_user(email='author@example.com', password='pass')
        self.giver1 = User.objects.create_user(email='giver1@example.com', password='pass')
        self.giver2 = User.objects.create_user(email='giver2@example.com', password='pass')

    @patch('postMang.tasks._get_redis')
    def test_recompute_points_weekly_creates_redis_mapping(self, mock_get_redis):
        # Prepare fake redis pipeline
        fake_pipe = MagicMock()
        fake_redis = MagicMock()
        fake_redis.pipeline.return_value = fake_pipe
        mock_get_redis.return_value = fake_redis

        # Create transactions within the ISO week of 2025-11-11 (week starting Monday 2025-11-10)
        week_date = datetime.fromisoformat('2025-11-11').date()
        monday = datetime.fromisocalendar(week_date.isocalendar()[0], week_date.isocalendar()[1], 1).date()

        t1 = RewardPointTransaction.objects.create(
            giver=self.giver1,
            firestore_post_id='p1',
            post_author=self.author,
            points=3,
        )
        t1.created_at = datetime(2025, 11, 11)
        t1.save(update_fields=['created_at'])

        t2 = RewardPointTransaction.objects.create(
            giver=self.giver2,
            firestore_post_id='p2',
            post_author=self.author,
            points=2,
        )
        t2.created_at = datetime(2025, 11, 12)
        t2.save(update_fields=['created_at'])

        # Run the weekly recompute synchronously by calling the wrapped function
        # (the shared_task decorator wraps the original function)
        tasks.recompute_points_weekly.__wrapped__(tasks.recompute_points_weekly, '2025-11-11')

        # Ensure pipeline.delete was called for the weekly key
        expected_key = key_weekly('points', monday)
        fake_pipe.delete.assert_any_call(expected_key)

        # Ensure zadd was called with mapping that sums points for the author
        # mapping is passed as a dict to zadd
        # We expect the pipeline.zadd to be called with the mapping containing the author's id
        called = False
        for call in fake_pipe.zadd.call_args_list:
            args, kwargs = call
            if args:
                mapping = args[0]
                # mapping keys are strings of post_author id
                if str(self.author.id) in mapping:
                    self.assertEqual(mapping[str(self.author.id)], float(5.0))
                    called = True
        self.assertTrue(called, 'zadd was not called with expected mapping for author')
