from django.core.management.base import BaseCommand
from django.db.models import Sum
from postMang.models import RewardPointTransaction
from postMang.leaderboard_utils import key_alltime, key_daily, key_weekly, key_monthly
import redis
import os
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Initialize Redis leaderboards from existing PostgreSQL reward transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back for daily/weekly/monthly boards (default: 30)'
        )

    def handle(self, *args, **options):
        redis_url = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
        r = redis.Redis.from_url(redis_url)
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Initializing Leaderboards from PostgreSQL'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        # Check total transactions
        total_transactions = RewardPointTransaction.objects.count()
        self.stdout.write(f'\n Found {total_transactions} total reward transactions in PostgreSQL\n')
        
        # 1. ALL-TIME LEADERBOARD
        self.stdout.write(self.style.HTTP_INFO(' Computing all-time leaderboard...'))
        qs = RewardPointTransaction.objects.values('post_author').annotate(score=Sum('points'))
        key = key_alltime('points')
        pipe = r.pipeline()
        pipe.delete(key)
        if qs:
            mapping = {str(item['post_author']): float(item['score']) for item in qs}
            pipe.zadd(key, mapping)
        result = pipe.execute()
        self.stdout.write(self.style.SUCCESS(f'   ✓ All-time leaderboard: {len(qs)} users'))
        
        # Get top 3 for display
        top_3 = r.zrevrange(key, 0, 2, withscores=True)
        if top_3:
            self.stdout.write('   Top 3 users:')
            for i, (user_id, score) in enumerate(top_3, 1):
                user_id_str = user_id.decode() if isinstance(user_id, bytes) else user_id
                self.stdout.write(f'     {i}. User ID {user_id_str}: {int(score)} points')
        
        # 2. CURRENT WEEK LEADERBOARD
        self.stdout.write(f'\n{self.style.HTTP_INFO(" Computing current week leaderboard...")}')
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        qs_week = RewardPointTransaction.objects.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=week_end
        ).values('post_author').annotate(score=Sum('points'))
        
        key = key_weekly('points', week_start)
        pipe = r.pipeline()
        pipe.delete(key)
        if qs_week:
            mapping = {str(item['post_author']): float(item['score']) for item in qs_week}
            pipe.zadd(key, mapping)
        pipe.expire(key, 60 * 60 * 24 * 180)
        pipe.execute()
        
        iso_year, iso_week, _ = week_start.isocalendar()
        self.stdout.write(self.style.SUCCESS(f'    Weekly leaderboard (Week {iso_year}-W{iso_week:02d}): {len(qs_week)} users'))
        self.stdout.write(f'   Period: {week_start} to {week_end}')
        
        # 3. CURRENT MONTH LEADERBOARD
        self.stdout.write(f'\n{self.style.HTTP_INFO(" Computing current month leaderboard...")}')
        month_start = today.replace(day=1)
        
        qs_month = RewardPointTransaction.objects.filter(
            created_at__date__gte=month_start
        ).values('post_author').annotate(score=Sum('points'))
        
        key = key_monthly('points', today)
        pipe = r.pipeline()
        pipe.delete(key)
        if qs_month:
            mapping = {str(item['post_author']): float(item['score']) for item in qs_month}
            pipe.zadd(key, mapping)
        pipe.expire(key, 60 * 60 * 24 * 180)
        pipe.execute()
        self.stdout.write(self.style.SUCCESS(f'   Monthly leaderboard ({today.strftime("%B %Y")}): {len(qs_month)} users'))
        
        # 4. TODAY'S LEADERBOARD
        self.stdout.write(f"\n{self.style.HTTP_INFO('Computing today leaderboard...')}")
        qs_today = RewardPointTransaction.objects.filter(
            created_at__date=today
        ).values('post_author').annotate(score=Sum('points'))
        
        key = key_daily('points', today)
        pipe = r.pipeline()
        pipe.delete(key)
        if qs_today:
            mapping = {str(item['post_author']): float(item['score']) for item in qs_today}
            pipe.zadd(key, mapping)
        pipe.expire(key, 60 * 60 * 24 * 180)
        pipe.execute()
        self.stdout.write(self.style.SUCCESS(f'Daily leaderboard ({today}): {len(qs_today)} users'))
        
        # Summary
        self.stdout.write(f"\n{self.style.WARNING('=' * 70)}")
        self.stdout.write(self.style.SUCCESS('All leaderboards initialized successfully!'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write("\n Next steps:")
        self.stdout.write('1. Test leaderboard endpoints:')
        self.stdout.write('- GET /api/leaderboard/alltime/')
        self.stdout.write('- GET /api/leaderboard/weekly/')
        self.stdout.write('- GET /api/leaderboard/monthly/')
        self.stdout.write('2. Start Celery Beat for automatic weekly resets')
        self.stdout.write("3. New rewards will automatically update Redis\n")