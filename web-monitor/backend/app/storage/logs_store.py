"""Daily log file storage and querying."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.storage.json_store import atomic_write_json, ensure_dir, read_json


class LogsStore:
    def __init__(self, data_dir: Path, retention_days: int = 31):
        self.logs_dir = data_dir / "logs"
        self.retention_days = retention_days
        ensure_dir(self.logs_dir)

    def _day_path(self, day: date) -> Path:
        return self.logs_dir / f"{day.isoformat()}.json"

    def append(self, record: dict[str, Any]) -> None:
        ts = record.get("timestamp")
        if ts:
            day = datetime.fromisoformat(ts).date()
        else:
            day = datetime.now(timezone.utc).date()
            record["timestamp"] = datetime.now(timezone.utc).isoformat()

        path = self._day_path(day)
        entries = read_json(path, default=[])
        if not isinstance(entries, list):
            entries = []
        entries.append(record)
        atomic_write_json(path, entries)

    def list_days(self) -> list[date]:
        days = []
        for path in sorted(self.logs_dir.glob("*.json")):
            try:
                days.append(date.fromisoformat(path.stem))
            except ValueError:
                continue
        return days

    def get_logs(
        self,
        project_id: Optional[str] = None,
        website_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 5000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if date_to is None:
            date_to = datetime.now(timezone.utc).date()
        if date_from is None:
            date_from = date_to - timedelta(days=self.retention_days - 1)

        # Clamp to retention window
        earliest = datetime.now(timezone.utc).date() - timedelta(days=self.retention_days - 1)
        if date_from < earliest:
            date_from = earliest
        if date_to < date_from:
            return []

        results: list[dict[str, Any]] = []
        current = date_from
        while current <= date_to:
            path = self._day_path(current)
            entries = read_json(path, default=[])
            if isinstance(entries, list):
                for entry in entries:
                    if project_id and entry.get("project_id") != project_id:
                        continue
                    if website_id and entry.get("website_id") != website_id:
                        continue
                    if status and entry.get("status") != status.upper():
                        continue
                    results.append(entry)
            current += timedelta(days=1)

        results.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return results[offset : offset + limit]

    def get_website_logs(
        self,
        website_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        if until is None:
            until = datetime.now(timezone.utc)
        if since is None:
            since = until - timedelta(days=self.retention_days)

        date_from = since.date()
        date_to = until.date()
        logs = self.get_logs(
            website_id=website_id,
            date_from=date_from,
            date_to=date_to,
            limit=100000,
        )
        filtered = []
        for entry in logs:
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if since <= ts <= until:
                    filtered.append(entry)
            except (KeyError, ValueError):
                continue
        # Chronological for charts
        filtered.sort(key=lambda e: e.get("timestamp", ""))
        return filtered

    def delete_by_website(self, website_id: str) -> int:
        removed = 0
        for path in self.logs_dir.glob("*.json"):
            entries = read_json(path, default=[])
            if not isinstance(entries, list):
                continue
            new_entries = [e for e in entries if e.get("website_id") != website_id]
            removed += len(entries) - len(new_entries)
            if len(new_entries) != len(entries):
                atomic_write_json(path, new_entries)
        return removed

    def delete_by_project(self, project_id: str) -> int:
        removed = 0
        for path in self.logs_dir.glob("*.json"):
            entries = read_json(path, default=[])
            if not isinstance(entries, list):
                continue
            new_entries = [e for e in entries if e.get("project_id") != project_id]
            removed += len(entries) - len(new_entries)
            if len(new_entries) != len(entries):
                atomic_write_json(path, new_entries)
        return removed

    def to_csv(self, logs: list[dict[str, Any]]) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "timestamp",
                "project",
                "website",
                "url",
                "status",
                "status_code",
                "response_time",
                "error",
            ]
        )
        for entry in logs:
            writer.writerow(
                [
                    entry.get("timestamp", ""),
                    entry.get("project_name", ""),
                    entry.get("website_name", ""),
                    entry.get("url", ""),
                    entry.get("status", ""),
                    entry.get("status_code", ""),
                    entry.get("response_time", ""),
                    entry.get("error", "") or "",
                ]
            )
        return buffer.getvalue()

    def to_json(self, logs: list[dict[str, Any]]) -> str:
        return json.dumps(logs, indent=2, ensure_ascii=False)
