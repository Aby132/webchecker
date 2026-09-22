"""Website persistence on the filesystem."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from app.models.website import Website, WebsiteCreate, WebsiteUpdate
from app.storage.json_store import JsonStore, backup_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WebsitesStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store = JsonStore(data_dir / "websites.json", default=[])
        self.backup_dir = data_dir / "backups"

    def list_all(self, project_id: Optional[str] = None) -> list[Website]:
        items = self.store.read()
        if project_id:
            items = [w for w in items if w.get("project_id") == project_id]
        return [Website(**w) for w in items]

    def get(self, website_id: str) -> Optional[Website]:
        for w in self.store.read():
            if w.get("id") == website_id:
                return Website(**w)
        return None

    def create(self, payload: WebsiteCreate) -> Website:
        now = _now()
        website = Website(
            id=f"site-{uuid4().hex[:8]}",
            project_id=payload.project_id,
            name=payload.name,
            url=payload.url,
            enabled=payload.enabled,
            check_interval=payload.check_interval,
            timeout=payload.timeout,
            expected_status_code=payload.expected_status_code,
            alert_enabled=payload.alert_enabled,
            status="UNKNOWN",
            last_status_code=None,
            last_response_time=None,
            last_checked=None,
            last_error=None,
            last_success_at=None,
            incident_started_at=None,
            next_check_at=now,
            created_at=now,
            updated_at=now,
        )
        data = self.store.read()
        data.append(website.model_dump())
        self.store.write(data)
        return website

    def update(self, website_id: str, payload: WebsiteUpdate) -> Optional[Website]:
        data = self.store.read()
        for i, item in enumerate(data):
            if item.get("id") == website_id:
                updates = payload.model_dump(exclude_unset=True)
                item.update(updates)
                item["updated_at"] = _now()
                if not item.get("enabled"):
                    item["status"] = "DISABLED"
                data[i] = item
                self.store.write(data)
                return Website(**item)
        return None

    def delete(self, website_id: str) -> bool:
        backup_file(self.store.path, self.backup_dir)
        data = self.store.read()
        new_data = [w for w in data if w.get("id") != website_id]
        if len(new_data) == len(data):
            return False
        self.store.write(new_data)
        return True

    def delete_by_project(self, project_id: str) -> int:
        backup_file(self.store.path, self.backup_dir)
        data = self.store.read()
        new_data = [w for w in data if w.get("project_id") != project_id]
        removed = len(data) - len(new_data)
        if removed:
            self.store.write(new_data)
        return removed

    def update_check_result(self, website_id: str, fields: dict[str, Any]) -> Optional[Website]:
        data = self.store.read()
        for i, item in enumerate(data):
            if item.get("id") == website_id:
                item.update(fields)
                item["updated_at"] = _now()
                data[i] = item
                self.store.write(data)
                return Website(**item)
        return None

    def get_due_websites(self, now_iso: str) -> list[Website]:
        due: list[Website] = []
        for w in self.store.read():
            if not w.get("enabled"):
                continue
            next_check = w.get("next_check_at")
            if next_check is None or next_check <= now_iso:
                due.append(Website(**w))
        return due
