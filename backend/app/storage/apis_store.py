"""API monitor persistence on the filesystem."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from app.models.api_monitor import ApiMonitor, ApiMonitorCreate, ApiMonitorUpdate
from app.secrets_mask import merge_headers, merge_secret
from app.storage.json_store import JsonStore, backup_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApisStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store = JsonStore(data_dir / "apis.json", default=[])
        self.backup_dir = data_dir / "backups"

    def list_all(self, project_id: Optional[str] = None) -> list[ApiMonitor]:
        items = self.store.read()
        if project_id:
            items = [a for a in items if a.get("project_id") == project_id]
        return [ApiMonitor(**a) for a in items]

    def get(self, api_id: str) -> Optional[ApiMonitor]:
        for item in self.store.read():
            if item.get("id") == api_id:
                return ApiMonitor(**item)
        return None

    def create(self, payload: ApiMonitorCreate) -> ApiMonitor:
        now = _now()
        monitor = ApiMonitor(
            id=f"api-{uuid4().hex[:8]}",
            project_id=payload.project_id,
            name=payload.name,
            url=payload.url,
            method=payload.method,
            enabled=payload.enabled,
            check_interval=payload.check_interval,
            timeout=payload.timeout,
            expected_status_code=payload.expected_status_code,
            alert_enabled=payload.alert_enabled,
            headers=payload.headers,
            body=payload.body or "",
            auth_type=payload.auth_type,
            bearer_token=payload.bearer_token or "",
            auth_username=payload.auth_username or "",
            auth_password=payload.auth_password or "",
            api_key_name=payload.api_key_name or "",
            api_key_value=payload.api_key_value or "",
            api_key_in=payload.api_key_in,
            validation_enabled=payload.validation_enabled,
            validation_rules=payload.validation_rules,
            monitor_type="API",
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
        data.append(monitor.model_dump())
        self.store.write(data)
        return monitor

    def update(self, api_id: str, payload: ApiMonitorUpdate) -> Optional[ApiMonitor]:
        data = self.store.read()
        for i, item in enumerate(data):
            if item.get("id") != api_id:
                continue
            updates = payload.model_dump(exclude_unset=True)
            if "headers" in updates:
                updates["headers"] = merge_headers(item.get("headers") or {}, updates.get("headers"))
            if "bearer_token" in updates:
                updates["bearer_token"] = merge_secret(item.get("bearer_token"), updates.get("bearer_token"))
            if "auth_password" in updates:
                updates["auth_password"] = merge_secret(item.get("auth_password"), updates.get("auth_password"))
            if "api_key_value" in updates:
                updates["api_key_value"] = merge_secret(item.get("api_key_value"), updates.get("api_key_value"))

            item.update(updates)
            if item.get("auth_type") == "none":
                item["bearer_token"] = ""
                item["auth_password"] = ""
                item["api_key_value"] = ""
            item["updated_at"] = _now()
            if not item.get("enabled"):
                item["status"] = "DISABLED"
            data[i] = item
            self.store.write(data)
            return ApiMonitor(**item)
        return None

    def delete(self, api_id: str) -> bool:
        backup_file(self.store.path, self.backup_dir)
        data = self.store.read()
        new_data = [item for item in data if item.get("id") != api_id]
        if len(new_data) == len(data):
            return False
        self.store.write(new_data)
        return True

    def delete_by_project(self, project_id: str) -> int:
        backup_file(self.store.path, self.backup_dir)
        data = self.store.read()
        new_data = [item for item in data if item.get("project_id") != project_id]
        removed = len(data) - len(new_data)
        if removed:
            self.store.write(new_data)
        return removed

    def update_check_result(self, api_id: str, fields: dict[str, Any]) -> Optional[ApiMonitor]:
        data = self.store.read()
        for i, item in enumerate(data):
            if item.get("id") == api_id:
                item.update(fields)
                item["updated_at"] = _now()
                data[i] = item
                self.store.write(data)
                return ApiMonitor(**item)
        return None

    def get_due_apis(self, now_iso: str) -> list[ApiMonitor]:
        due: list[ApiMonitor] = []
        for item in self.store.read():
            if not item.get("enabled"):
                continue
            next_check = item.get("next_check_at")
            if next_check is None or next_check <= now_iso:
                due.append(ApiMonitor(**item))
        return due
