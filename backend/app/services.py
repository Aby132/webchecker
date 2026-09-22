"""Shared application services / dependency container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import Settings, get_settings
from app.monitoring.scheduler import MonitorScheduler
from app.monitoring.state import StateStore
from app.monitoring.worker import MonitoringWorker
from app.storage.json_store import ensure_dir
from app.storage.logs_store import LogsStore
from app.storage.projects_store import ProjectsStore
from app.storage.settings_store import SettingsStore
from app.storage.apis_store import ApisStore
from app.storage.websites_store import WebsitesStore


@dataclass
class AppServices:
    settings: Settings
    data_dir: Path
    projects: ProjectsStore
    websites: WebsitesStore
    apis: ApisStore
    logs: LogsStore
    app_settings: SettingsStore
    state: StateStore
    worker: MonitoringWorker
    scheduler: MonitorScheduler


_services: Optional[AppServices] = None


def init_demo_data(projects: ProjectsStore, websites: WebsitesStore, data_dir: Path) -> None:
    """Create sample data only when stores are empty on first startup."""
    marker = data_dir / ".initialized"
    if marker.exists():
        return

    existing_projects = projects.list_all()
    existing_websites = websites.list_all()
    if existing_projects or existing_websites:
        marker.write_text("initialized\n", encoding="utf-8")
        return

    from app.models.project import ProjectCreate
    from app.models.website import WebsiteCreate

    project = projects.create(
        ProjectCreate(
            name="Demo Production",
            description="Sample project - safe to delete",
            enabled=True,
        )
    )
    websites.create(
        WebsiteCreate(
            project_id=project.id,
            name="Demo Frontend",
            url="https://example.com",
            enabled=True,
            check_interval=60,
            timeout=10,
            expected_status_code=200,
            alert_enabled=False,
        )
    )
    websites.create(
        WebsiteCreate(
            project_id=project.id,
            name="Demo API",
            url="https://httpbin.org/status/200",
            enabled=True,
            check_interval=30,
            timeout=10,
            expected_status_code=200,
            alert_enabled=False,
        )
    )
    marker.write_text("initialized\n", encoding="utf-8")


def create_services() -> AppServices:
    global _services
    settings = get_settings()
    data_dir = settings.data_path
    ensure_dir(data_dir)
    ensure_dir(data_dir / "logs")
    ensure_dir(data_dir / "backups")

    projects = ProjectsStore(data_dir)
    websites = WebsitesStore(data_dir)
    apis = ApisStore(data_dir)
    logs = LogsStore(data_dir, retention_days=settings.log_retention_days)
    app_settings = SettingsStore(data_dir)
    state = StateStore(data_dir)

    init_demo_data(projects, websites, data_dir)

    # Merge env allow_private with settings file
    stored = app_settings.get()
    allow_private = settings.allow_private_urls or stored.allow_private_urls
    max_concurrent = settings.max_concurrent_checks or stored.max_concurrent_checks

    worker = MonitoringWorker(
        projects_store=projects,
        websites_store=websites,
        apis_store=apis,
        logs_store=logs,
        settings_store=app_settings,
        state_store=state,
        max_concurrent=max_concurrent,
        allow_private_urls=allow_private,
    )
    scheduler = MonitorScheduler(
        worker=worker,
        logs_dir=data_dir / "logs",
        retention_days=settings.log_retention_days,
    )

    _services = AppServices(
        settings=settings,
        data_dir=data_dir,
        projects=projects,
        websites=websites,
        apis=apis,
        logs=logs,
        app_settings=app_settings,
        state=state,
        worker=worker,
        scheduler=scheduler,
    )
    return _services


def get_services() -> AppServices:
    if _services is None:
        return create_services()
    return _services
