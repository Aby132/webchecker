"""APScheduler-based monitoring and cleanup schedulers."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.storage.cleanup import cleanup_old_logs

if TYPE_CHECKING:
    from app.monitoring.worker import MonitoringWorker
    from pathlib import Path

logger = logging.getLogger(__name__)


class MonitorScheduler:
    def __init__(
        self,
        worker: "MonitoringWorker",
        logs_dir: "Path",
        retention_days: int = 31,
    ):
        self.worker = worker
        self.logs_dir = logs_dir
        self.retention_days = retention_days
        self.scheduler: Optional[AsyncIOScheduler] = None

    async def start(self) -> None:
        await self.worker.start()
        self.scheduler = AsyncIOScheduler()
        # Tick every second to honor per-site intervals accurately
        self.scheduler.add_job(
            self._safe_tick,
            "interval",
            seconds=1,
            id="monitor_tick",
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            self._safe_cleanup,
            "cron",
            hour=3,
            minute=15,
            id="log_cleanup",
            coalesce=True,
        )
        # Run cleanup once at startup
        self.scheduler.add_job(
            self._safe_cleanup,
            "date",
            id="log_cleanup_startup",
        )
        self.scheduler.start()
        logger.info("Scheduler started")

    async def stop(self) -> None:
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
        await self.worker.stop()
        logger.info("Scheduler stopped")

    async def _safe_tick(self) -> None:
        try:
            await self.worker.tick()
        except Exception:  # noqa: BLE001
            logger.exception("Monitor tick failed")

    async def _safe_cleanup(self) -> None:
        try:
            # Run blocking cleanup in thread
            deleted = await asyncio.to_thread(
                cleanup_old_logs, self.logs_dir, self.retention_days
            )
            if deleted:
                logger.info("Log cleanup removed %s file(s)", deleted)
        except Exception:  # noqa: BLE001
            logger.exception("Log cleanup failed")
