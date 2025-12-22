from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from postMang.tasks import recompute_points_daily, recompute_points_weekly, recompute_points_alltime

class Command(BaseCommand):
    help = 'Backfill leaderboard snapshots (daily/weekly/alltime) from RewardPointTransaction records.'

    def add_arguments(self, parser):
        parser.add_argument('--from-date', type=str, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--to-date', type=str, help='End date (YYYY-MM-DD)')
        parser.add_argument('--weekly', action='store_true', help='Backfill weekly snapshots')
        parser.add_argument('--daily', action='store_true', help='Backfill daily snapshots')
        parser.add_argument('--alltime', action='store_true', help='Recompute all-time snapshot')
        parser.add_argument('--run-sync', action='store_true', help='Run tasks synchronously (no Celery)')

    def handle(self, *args, **options):
        run_sync = options['run_sync']

        # Default to daily if neither daily nor weekly nor alltime specified
        if not (options['daily'] or options['weekly'] or options['alltime']):
            options['daily'] = True

        from_date = None
        to_date = None
        if options['from_date']:
            try:
                from_date = datetime.fromisoformat(options['from_date']).date()
            except Exception:
                raise CommandError('Invalid --from-date format. Use YYYY-MM-DD')
        if options['to_date']:
            try:
                to_date = datetime.fromisoformat(options['to_date']).date()
            except Exception:
                raise CommandError('Invalid --to-date format. Use YYYY-MM-DD')

        if options['daily']:
            if not from_date or not to_date:
                raise CommandError('For daily backfill please provide --from-date and --to-date')
            day = from_date
            while day <= to_date:
                date_iso = day.isoformat()
                self.stdout.write(f'Backfilling daily leaderboard for {date_iso}...')
                if run_sync:
                    recompute_points_daily(None, date_iso)
                else:
                    recompute_points_daily.delay(date_iso)
                day = day + timedelta(days=1)

        if options['weekly']:
            if not from_date or not to_date:
                raise CommandError('For weekly backfill please provide --from-date and --to-date')
            # Iterate weeks by stepping 7 days from the monday of from_date
            # Normalize start to Monday
            start = from_date - timedelta(days=from_date.weekday())
            end = to_date - timedelta(days=to_date.weekday())
            week_start = start
            while week_start <= end:
                date_iso = week_start.isoformat()
                self.stdout.write(f'Backfilling weekly leaderboard for week starting {date_iso}...')
                if run_sync:
                    recompute_points_weekly(None, date_iso)
                else:
                    recompute_points_weekly.delay(date_iso)
                week_start = week_start + timedelta(days=7)

        if options['alltime']:
            self.stdout.write('Recomputing all-time leaderboard...')
            if run_sync:
                recompute_points_alltime()
            else:
                recompute_points_alltime.delay()

        self.stdout.write(self.style.SUCCESS('Backfill scheduled.'))
