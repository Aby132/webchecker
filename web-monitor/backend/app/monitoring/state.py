"""Monitoring runtime state persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.storage.json_store import JsonStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateStore:
    """Persists monitoring engine status and per-site alert state."""

    def __init__(self, data_dir: Path):
        self.store = JsonStore(
            data_dir / "state.json",
            default={
                "engine_running": False,
                "started_at": None,
                "last_tick_at": None,
                "checks_total": 0,
                "incidents": {},
                "sites": {},
            },
        )

    def read(self) -> dict[str, Any]:
        data = self.store.read()
        if not isinstance(data, dict):
            return {
                "engine_running": False,
                "started_at": None,
                "last_tick_at": None,
                "checks_total": 0,
                "incidents": {},
                "sites": {},
            }
        return data

    def write(self, data: dict[str, Any]) -> None:
        self.store.write(data)

    def set_engine_running(self, running: bool) -> None:
        data = self.read()
        data["engine_running"] = running
        if running:
            data["started_at"] = _now()
        self.write(data)

    def touch_tick(self) -> None:
        data = self.read()
        data["last_tick_at"] = _now()
        data["checks_total"] = int(data.get("checks_total", 0)) + 1
        self.write(data)

    def get_site_state(self, website_id: str) -> dict[str, Any]:
        data = self.read()
        sites = data.get("sites") or {}
        return sites.get(
            website_id,
            {
                "status": "UNKNOWN",
                "incident_started_at": None,
                "last_alert_type": None,
            },
        )

    def set_site_state(self, website_id: str, fields: dict[str, Any]) -> None:
        data = self.read()
        sites = data.get("sites") or {}
        current = sites.get(website_id, {})
        current.update(fields)
        sites[website_id] = current
        data["sites"] = sites
        self.write(data)

    def remove_site(self, website_id: str) -> None:
        data = self.read()
        sites = data.get("sites") or {}
        if website_id in sites:
            del sites[website_id]
            data["sites"] = sites
            self.write(data)

    def remove_project_sites(self, website_ids: list[str]) -> None:
        data = self.read()
        sites = data.get("sites") or {}
        for wid in website_ids:
            sites.pop(wid, None)
        data["sites"] = sites
        self.write(data)

    def add_incident(self, website_id: str, incident: dict[str, Any]) -> None:
        data = self.read()
        incidents = data.get("incidents") or {}
        site_incidents = incidents.get(website_id, [])
        site_incidents.insert(0, incident)
        # Keep last 100 incidents per site
        incidents[website_id] = site_incidents[:100]
        data["incidents"] = incidents
        self.write(data)

    def close_incident(self, website_id: str, ended_at: str, duration_seconds: int) -> Optional[dict]:
        data = self.read()
        incidents = data.get("incidents") or {}
        site_incidents = incidents.get(website_id, [])
        for inc in site_incidents:
            if inc.get("ended_at") is None:
                inc["ended_at"] = ended_at
                inc["duration_seconds"] = duration_seconds
                inc["status"] = "RECOVERED"
                data["incidents"] = incidents
                self.write(data)
                return inc
        return None

    def get_incidents(self, website_id: str, limit: int = 50) -> list[dict[str, Any]]:
        data = self.read()
        incidents = data.get("incidents") or {}
        return (incidents.get(website_id) or [])[:limit]

    def get_active_incident_count(self) -> int:
        data = self.read()
        incidents = data.get("incidents") or {}
        count = 0
        for site_list in incidents.values():
            for inc in site_list:
                if inc.get("ended_at") is None:
                    count += 1
        return count
