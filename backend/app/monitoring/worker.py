"""Central monitoring worker — concurrent due checks with semaphore."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

import httpx

from app.monitoring.checker import CheckResult, check_api, check_website
from app.notifications import email as email_notify
from app.secrets_mask import sanitize_error_text

if TYPE_CHECKING:
    from app.storage.apis_store import ApisStore
    from app.storage.logs_store import LogsStore
    from app.storage.projects_store import ProjectsStore
    from app.storage.settings_store import SettingsStore
    from app.storage.websites_store import WebsitesStore
    from app.monitoring.state import StateStore

logger = logging.getLogger(__name__)


class MonitoringWorker:
    def __init__(
        self,
        projects_store: "ProjectsStore",
        websites_store: "WebsitesStore",
        apis_store: "ApisStore",
        logs_store: "LogsStore",
        settings_store: "SettingsStore",
        state_store: "StateStore",
        max_concurrent: int = 20,
        allow_private_urls: bool = False,
    ):
        self.projects_store = projects_store
        self.websites_store = websites_store
        self.apis_store = apis_store
        self.logs_store = logs_store
        self.settings_store = settings_store
        self.state_store = state_store
        self.max_concurrent = max_concurrent
        self.allow_private_urls = allow_private_urls
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._tick_lock = asyncio.Lock()
        self.running = False

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "WebMonitor/1.0 (+self-hosted)"},
            verify=True,
        )
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self.running = True
        self.state_store.set_engine_running(True)
        logger.info("Monitoring worker started (max concurrent=%s)", self.max_concurrent)

    async def stop(self) -> None:
        self.running = False
        self.state_store.set_engine_running(False)
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("Monitoring worker stopped")

    async def tick(self) -> None:
        if not self.running or not self._client or not self._semaphore:
            return

        async with self._tick_lock:
            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()

            projects = {p.id: p for p in self.projects_store.list_all()}
            due_sites = [
                w
                for w in self.websites_store.get_due_websites(now_iso)
                if w.project_id in projects and projects[w.project_id].enabled
            ]
            due_apis = [
                api
                for api in self.apis_store.get_due_apis(now_iso)
                if api.project_id in projects and projects[api.project_id].enabled
            ]

            if not due_sites and not due_apis:
                return

            tasks = [self._check_one(w, projects.get(w.project_id), now) for w in due_sites]
            tasks.extend(self._check_one_api(api, projects.get(api.project_id), now) for api in due_apis)
            await asyncio.gather(*tasks, return_exceptions=True)
            self.state_store.touch_tick()

    async def _check_one(self, website, project, now: datetime) -> None:
        assert self._client and self._semaphore
        async with self._semaphore:
            try:
                result = await check_website(
                    self._client,
                    url=website.url,
                    timeout=float(website.timeout),
                    expected_status_code=website.expected_status_code,
                    allow_private=self.allow_private_urls,
                )
                await self._process_result(website, project, result, now)
            except Exception:  # noqa: BLE001
                logger.exception("Worker error checking %s", website.id)

    async def _check_one_api(self, api, project, now: datetime) -> None:
        assert self._client and self._semaphore
        async with self._semaphore:
            try:
                result = await check_api(
                    self._client,
                    api,
                    allow_private=self.allow_private_urls,
                )
                await self._process_api_result(api, project, result, now)
            except Exception:  # noqa: BLE001
                logger.exception("Worker error checking API %s", api.id)

    async def _process_result(self, website, project, result: CheckResult, now: datetime) -> None:
        now_iso = now.isoformat()
        previous_status = website.status
        if previous_status in (None, "UNKNOWN", "DISABLED"):
            # Treat first real check without prior UP/DOWN carefully
            site_state = self.state_store.get_site_state(website.id)
            previous_status = site_state.get("status") or previous_status

        new_status = result.status
        next_check = (now + timedelta(seconds=website.check_interval)).isoformat()

        fields = {
            "status": new_status,
            "last_status_code": result.status_code,
            "last_response_time": result.response_time,
            "last_checked": now_iso,
            "last_error": sanitize_error_text(result.error),
            "next_check_at": next_check,
        }

        if new_status == "UP":
            fields["last_success_at"] = now_iso

        # Transition detection
        transition = None
        if previous_status == "UP" and new_status == "DOWN":
            transition = "DOWN"
            fields["incident_started_at"] = now_iso
        elif previous_status == "DOWN" and new_status == "UP":
            transition = "RECOVERY"
        elif previous_status in ("UNKNOWN", "DISABLED", None) and new_status == "DOWN":
            # First observed down — start incident, alert once
            transition = "DOWN"
            fields["incident_started_at"] = now_iso
        elif new_status == "UP" and previous_status != "DOWN":
            fields["incident_started_at"] = None

        if transition == "RECOVERY":
            fields["incident_started_at"] = None

        updated = self.websites_store.update_check_result(website.id, fields)

        # Persist monitoring state for restart safety
        self.state_store.set_site_state(
            website.id,
            {
                "status": new_status,
                "incident_started_at": fields.get(
                    "incident_started_at",
                    website.incident_started_at if transition != "RECOVERY" else None,
                ),
                "last_alert_type": transition,
                "last_checked": now_iso,
            },
        )

        # Append log
        project_name = project.name if project else "Unknown"
        self.logs_store.append(
            {
                "timestamp": now_iso,
                "project_id": website.project_id,
                "project_name": project_name,
                "monitor_type": "WEBSITE",
                "website_id": website.id,
                "website_name": website.name,
                "api_id": None,
                "api_name": None,
                "url": website.url,
                "status": new_status,
                "status_code": result.status_code,
                "response_time": result.response_time,
                "error": sanitize_error_text(result.error),
                "method": result.method,
            }
        )

        # Alerts only on transitions
        if transition and website.alert_enabled:
            await self._send_transition_alert(
                website=updated or website,
                project_name=project_name,
                result=result,
                transition=transition,
                now_iso=now_iso,
                previous_incident_start=website.incident_started_at,
            )

    async def _send_transition_alert(
        self,
        website,
        project_name: str,
        result: CheckResult,
        transition: str,
        now_iso: str,
        previous_incident_start: Optional[str],
        monitor_kind: str = "WEBSITE",
    ) -> None:
        settings = self.settings_store.get()
        email_cfg = settings.email
        tz_name = settings.timezone or "Asia/Kolkata"

        if transition == "DOWN":
            self.state_store.add_incident(
                website.id,
                {
                    "started_at": now_iso,
                    "ended_at": None,
                    "status": "DOWN",
                    "status_code": result.status_code,
                    "error": result.error,
                    "duration_seconds": None,
                },
            )
            ok, msg = await email_notify.send_down_alert(
                email_cfg,
                {
                    "project_name": project_name,
                    "website_name": website.name,
                    "url": website.url,
                    "expected_status": website.expected_status_code,
                    "actual_status": result.status_code,
                    "error": result.error,
                    "response_time": result.response_time,
                    "detected_at": now_iso,
                    "check_interval": website.check_interval,
                    "timeout": website.timeout,
                    "last_success": website.last_success_at,
                    "monitor_kind": monitor_kind,
                },
                tz_name=tz_name,
            )
            if not ok:
                logger.warning("DOWN alert not sent for %s: %s", website.id, msg)

        elif transition == "RECOVERY":
            started = previous_incident_start
            duration = None
            if started:
                try:
                    start_dt = datetime.fromisoformat(started)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    duration = (datetime.fromisoformat(now_iso) - start_dt).total_seconds()
                except Exception:
                    duration = None

            self.state_store.close_incident(
                website.id,
                ended_at=now_iso,
                duration_seconds=int(duration or 0),
            )

            ok, msg = await email_notify.send_recovery_alert(
                email_cfg,
                {
                    "project_name": project_name,
                    "website_name": website.name,
                    "url": website.url,
                    "actual_status": result.status_code,
                    "response_time": result.response_time,
                    "recovered_at": now_iso,
                    "duration_seconds": duration,
                    "last_failure": website.last_status_code or website.last_error,
                    "failure_started": started,
                    "monitor_kind": monitor_kind,
                },
                tz_name=tz_name,
            )
            if not ok:
                logger.warning("Recovery alert not sent for %s: %s", website.id, msg)

    async def _process_api_result(self, api, project, result: CheckResult, now: datetime) -> None:
        now_iso = now.isoformat()
        previous_status = api.status
        if previous_status in (None, "UNKNOWN", "DISABLED"):
            site_state = self.state_store.get_site_state(api.id)
            previous_status = site_state.get("status") or previous_status

        new_status = result.status
        next_check = (now + timedelta(seconds=api.check_interval)).isoformat()
        error = sanitize_error_text(result.error)

        fields = {
            "status": new_status,
            "last_status_code": result.status_code,
            "last_response_time": result.response_time,
            "last_checked": now_iso,
            "last_error": error,
            "next_check_at": next_check,
        }

        if new_status == "UP":
            fields["last_success_at"] = now_iso

        transition = None
        if previous_status == "UP" and new_status == "DOWN":
            transition = "DOWN"
            fields["incident_started_at"] = now_iso
        elif previous_status == "DOWN" and new_status == "UP":
            transition = "RECOVERY"
        elif previous_status in ("UNKNOWN", "DISABLED", None) and new_status == "DOWN":
            transition = "DOWN"
            fields["incident_started_at"] = now_iso
        elif new_status == "UP" and previous_status != "DOWN":
            fields["incident_started_at"] = None

        if transition == "RECOVERY":
            fields["incident_started_at"] = None

        updated = self.apis_store.update_check_result(api.id, fields)

        self.state_store.set_site_state(
            api.id,
            {
                "status": new_status,
                "incident_started_at": fields.get(
                    "incident_started_at",
                    api.incident_started_at if transition != "RECOVERY" else None,
                ),
                "last_alert_type": transition,
                "last_checked": now_iso,
            },
        )

        project_name = project.name if project else "Unknown"
        self.logs_store.append(
            {
                "timestamp": now_iso,
                "project_id": api.project_id,
                "project_name": project_name,
                "monitor_type": "API",
                "website_id": None,
                "website_name": None,
                "api_id": api.id,
                "api_name": api.name,
                "url": api.url,
                "status": new_status,
                "status_code": result.status_code,
                "response_time": result.response_time,
                "error": error,
                "method": result.method,
            }
        )

        if transition and api.alert_enabled:
            await self._send_transition_alert(
                website=updated or api,
                project_name=project_name,
                result=result,
                transition=transition,
                now_iso=now_iso,
                previous_incident_start=api.incident_started_at,
                monitor_kind="API",
            )
