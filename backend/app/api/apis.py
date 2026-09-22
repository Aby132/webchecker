"""API monitors REST API. Secrets are never returned in responses."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from app.analytics import (
    avg_response_time,
    calc_uptime,
    incident_duration_label,
    response_time_series,
    status_code_distribution,
    status_timeline,
    uptime_windows,
)
from app.models.api_monitor import ApiMonitorCreate, ApiMonitorPublic, ApiMonitorUpdate, to_public
from app.monitoring.checker import validate_url_ssrf
from app.services import get_services

router = APIRouter(prefix="/api/apis", tags=["apis"])


@router.get("", response_model=list[ApiMonitorPublic])
def list_apis(project_id: str | None = None):
    return [to_public(item) for item in get_services().apis.list_all(project_id=project_id)]


@router.get("/{api_id}", response_model=ApiMonitorPublic)
def get_api(api_id: str):
    monitor = get_services().apis.get(api_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="API not found")
    return to_public(monitor)


@router.post("", response_model=ApiMonitorPublic, status_code=201)
def create_api(payload: ApiMonitorCreate):
    svc = get_services()
    project = svc.projects.get(payload.project_id)
    if not project:
        raise HTTPException(status_code=400, detail="Project not found")

    ok, reason = validate_url_ssrf(payload.url, allow_private=svc.worker.allow_private_urls)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    return to_public(svc.apis.create(payload))


@router.put("/{api_id}", response_model=ApiMonitorPublic)
def update_api(api_id: str, payload: ApiMonitorUpdate):
    svc = get_services()
    existing = svc.apis.get(api_id)
    if not existing:
        raise HTTPException(status_code=404, detail="API not found")

    if payload.project_id is not None:
        project = svc.projects.get(payload.project_id)
        if not project:
            raise HTTPException(status_code=400, detail="Project not found")

    if payload.url is not None:
        ok, reason = validate_url_ssrf(payload.url, allow_private=svc.worker.allow_private_urls)
        if not ok:
            raise HTTPException(status_code=400, detail=reason)

    monitor = svc.apis.update(api_id, payload)
    return to_public(monitor)


@router.delete("/{api_id}")
def delete_api(api_id: str):
    svc = get_services()
    existing = svc.apis.get(api_id)
    if not existing:
        raise HTTPException(status_code=404, detail="API not found")
    svc.apis.delete(api_id)
    svc.logs.delete_by_api(api_id)
    svc.state.remove_site(api_id)
    return {"ok": True}


@router.get("/{api_id}/details")
def api_details(
    api_id: str,
    range: str = Query(default="24h", pattern="^(1h|6h|24h|7d|30d)$"),
):
    svc = get_services()
    monitor = svc.apis.get(api_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="API not found")

    project = svc.projects.get(monitor.project_id)
    now = datetime.now(timezone.utc)
    range_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    since = now - range_map[range]
    logs = svc.logs.get_api_logs(api_id, since=since, until=now)
    all_logs = svc.logs.get_api_logs(api_id)

    incident_duration = None
    if monitor.status == "DOWN" and monitor.incident_started_at:
        incident_duration = incident_duration_label(monitor.incident_started_at)

    windows = uptime_windows(all_logs)
    range_uptime = calc_uptime(logs)

    return {
        "api": to_public(monitor),
        "project": project,
        "uptime": range_uptime,
        "uptime_windows": windows,
        "avg_response_time": avg_response_time(logs),
        "incident_duration": incident_duration,
        "response_time_series": response_time_series(logs),
        "status_timeline": status_timeline(logs),
        "status_codes": status_code_distribution(logs),
        "incidents": svc.state.get_incidents(api_id),
        "range": range,
        "log_count": len(logs),
    }
