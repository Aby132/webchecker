"""Project persistence on the filesystem."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.models.project import Project, ProjectCreate, ProjectUpdate
from app.storage.json_store import JsonStore, backup_file


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectsStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store = JsonStore(data_dir / "projects.json", default=[])
        self.backup_dir = data_dir / "backups"

    def list_all(self) -> list[Project]:
        return [Project(**p) for p in self.store.read()]

    def get(self, project_id: str) -> Optional[Project]:
        for p in self.store.read():
            if p.get("id") == project_id:
                return Project(**p)
        return None

    def create(self, payload: ProjectCreate) -> Project:
        now = _now()
        project = Project(
            id=f"project-{uuid4().hex[:8]}",
            name=payload.name,
            description=payload.description,
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        data = self.store.read()
        data.append(project.model_dump())
        self.store.write(data)
        return project

    def update(self, project_id: str, payload: ProjectUpdate) -> Optional[Project]:
        data = self.store.read()
        for i, item in enumerate(data):
            if item.get("id") == project_id:
                updates = payload.model_dump(exclude_unset=True)
                item.update(updates)
                item["updated_at"] = _now()
                data[i] = item
                self.store.write(data)
                return Project(**item)
        return None

    def delete(self, project_id: str) -> bool:
        backup_file(self.store.path, self.backup_dir)
        data = self.store.read()
        new_data = [p for p in data if p.get("id") != project_id]
        if len(new_data) == len(data):
            return False
        self.store.write(new_data)
        return True
