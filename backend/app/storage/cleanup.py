"""Log retention cleanup."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_old_logs(logs_dir: Path, retention_days: int = 31) -> int:
    """Delete log files older than retention_days. Returns count deleted."""
    if not logs_dir.exists():
        return 0

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=retention_days)
    deleted = 0

    for path in logs_dir.glob("*.json"):
        try:
            day = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            logger.warning("Skipping unrecognized log file: %s", path.name)
            continue

        if day < cutoff:
            try:
                path.unlink()
                deleted += 1
                logger.info("Deleted expired log file: %s", path.name)
            except OSError as exc:
                logger.error("Failed to delete %s: %s", path.name, exc)

    return deleted
