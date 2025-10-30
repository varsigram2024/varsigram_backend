from datetime import datetime
from typing import Union, Optional

def key_alltime(metric: str) -> str:
    return f"leaderboard:{metric}:alltime"

def key_daily(metric: str, dt: Optional[datetime.date] = None) -> str:
    dt = dt or datetime.utcnow().date()
    return f"leaderboard:{metric}:daily:{dt.isoformat()}"

def key_weekly(metric: str, dt: Optional[datetime.date] = None) -> str:
    dt = dt or datetime.utcnow().date()
    y, w, _ = dt.isocalendar()
    return f"leaderboard:{metric}:weekly:{y}-W{w:02d}"

def key_monthly(metric: str, dt: Optional[datetime.date] = None) -> str:
    dt = dt or datetime.utcnow().date()
    return f"leaderboard:{metric}:monthly:{dt.year}-{dt.month:02d}"

def period_keys(metric: str, dt: Optional[datetime.date] = None) -> list:
    dt = dt or datetime.now(datetime.timezone.utc)
    return [
        key_alltime(metric),
        key_daily(metric, dt),
        key_weekly(metric, dt),
        key_monthly(metric, dt),
    ]
