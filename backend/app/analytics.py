"""Uptime and analytics helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional


def parse_ts(value: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def calc_uptime(logs: list[dict[str, Any]]) -> Optional[float]:
    if not logs:
        return None
    total = len(logs)
    if total == 0:
        return None
    up = sum(1 for e in logs if e.get("status") == "UP")
    return round((up / total) * 100, 2)


def filter_since(logs: list[dict[str, Any]], hours: Optional[float] = None, days: Optional[float] = None) -> list[dict]:
    if hours is None and days is None:
        return logs
    now = datetime.now(timezone.utc)
    if days is not None:
        since = now - timedelta(days=days)
    else:
        since = now - timedelta(hours=hours or 0)
    out = []
    for e in logs:
        ts = parse_ts(e.get("timestamp", ""))
        if ts and ts >= since:
            out.append(e)
    return out


def uptime_windows(logs: list[dict[str, Any]]) -> dict[str, Optional[float]]:
    return {
        "1h": calc_uptime(filter_since(logs, hours=1)),
        "6h": calc_uptime(filter_since(logs, hours=6)),
        "24h": calc_uptime(filter_since(logs, hours=24)),
        "7d": calc_uptime(filter_since(logs, days=7)),
        "30d": calc_uptime(filter_since(logs, days=30)),
    }


def avg_response_time(logs: list[dict[str, Any]]) -> Optional[float]:
    times = [e["response_time"] for e in logs if e.get("response_time") is not None]
    if not times:
        return None
    return round(sum(times) / len(times), 2)


def status_code_distribution(logs: list[dict[str, Any]]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for e in logs:
        code = e.get("status_code")
        key = str(code) if code is not None else "error"
        dist[key] = dist.get(key, 0) + 1
    return dict(sorted(dist.items(), key=lambda x: (-x[1], x[0])))


def response_time_series(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    series = []
    for e in logs:
        if e.get("response_time") is None:
            continue
        series.append(
            {
                "timestamp": e.get("timestamp"),
                "response_time": e.get("response_time"),
                "status": e.get("status"),
            }
        )
    return series


def status_timeline(logs: list[dict[str, Any]], limit: int = 200) -> list[dict[str, Any]]:
    # Return chronological timeline points
    points = [
        {
            "timestamp": e.get("timestamp"),
            "status": e.get("status"),
            "status_code": e.get("status_code"),
        }
        for e in logs
    ]
    if len(points) > limit:
        # sample evenly
        step = len(points) / limit
        sampled = []
        i = 0.0
        while len(sampled) < limit and int(i) < len(points):
            sampled.append(points[int(i)])
            i += step
        return sampled
    return points


def incident_duration_label(started_at: Optional[str], ended_at: Optional[str] = None) -> Optional[str]:
    if not started_at:
        return None
    start = parse_ts(started_at)
    if not start:
        return None
    end = parse_ts(ended_at) if ended_at else datetime.now(timezone.utc)
    if not end:
        end = datetime.now(timezone.utc)
    seconds = int((end - start).total_seconds())
    hours, rem = divmod(max(seconds, 0), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
