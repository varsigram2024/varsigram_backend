import datetime
from typing import Optional


def key_alltime(metric: str) -> str:
    return f"leaderboard:{metric}:alltime"


def key_daily(metric: str, dt: Optional[datetime.date] = None) -> str:
    # Use timezone-aware UTC now to avoid naive datetime warnings
    dt = dt or datetime.datetime.now(datetime.timezone.utc).date()
    return f"leaderboard:{metric}:daily:{dt.isoformat()}"


def key_weekly(metric: str, dt: Optional[datetime.date] = None) -> str:
    # Use ISO week (year, week number)
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc).date()
    y, w, _ = dt.isocalendar()
    return f"leaderboard:{metric}:weekly:{y}-W{w:02d}"


def key_monthly(metric: str, dt: Optional[datetime.date] = None) -> str:
    dt = dt or datetime.datetime.now(datetime.timezone.utc).date()
    return f"leaderboard:{metric}:monthly:{dt.year}-{dt.month:02d}"


def period_keys(metric: str, dt: Optional[datetime.date] = None) -> list:
    # Accept either a date or None. Use UTC now by default.
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc).date()
    return [
        key_alltime(metric),
        key_daily(metric, dt),
        key_weekly(metric, dt),
        key_monthly(metric, dt),
    ]
