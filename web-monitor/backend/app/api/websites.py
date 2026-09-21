"""Websites API."""

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
from app.models.website import Website, WebsiteCreate, WebsiteUpdate
from app.monitoring.checker import validate_url_ssrf
from app.services import get_services

router = APIRouter(prefix="/api/websites", tags=["websites"])


@router.get("", response_model=list[Website])
def list_websites(project_id: str | None = None):
    return get_services().websites.list_all(project_id=project_id)


@router.get("/{website_id}", response_model=Website)
def get_website(website_id: str):
    website = get_services().websites.get(website_id)
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


@router.post("", response_model=Website, status_code=201)
def create_website(payload: WebsiteCreate):
    svc = get_services()
    project = svc.projects.get(payload.project_id)
    if not project:
        raise HTTPException(status_code=400, detail="Project not found")

    ok, reason = validate_url_ssrf(payload.url, allow_private=svc.worker.allow_private_urls)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    return svc.websites.create(payload)


@router.put("/{website_id}", response_model=Website)
def update_website(website_id: str, payload: WebsiteUpdate):
    svc = get_services()
    existing = svc.websites.get(website_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Website not found")

    if payload.project_id is not None:
        project = svc.projects.get(payload.project_id)
        if not project:
            raise HTTPException(status_code=400, detail="Project not found")

    if payload.url is not None:
        ok, reason = validate_url_ssrf(payload.url, allow_private=svc.worker.allow_private_urls)
        if not ok:
            raise HTTPException(status_code=400, detail=reason)

    website = svc.websites.update(website_id, payload)
    return website


@router.delete("/{website_id}")
def delete_website(website_id: str):
    svc = get_services()
    existing = svc.websites.get(website_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Website not found")
    svc.websites.delete(website_id)
    svc.logs.delete_by_website(website_id)
    svc.state.remove_site(website_id)
    return {"ok": True}


@router.get("/{website_id}/details")
def website_details(
    website_id: str,
    range: str = Query(default="24h", pattern="^(1h|6h|24h|7d|30d)$"),
):
    svc = get_services()
    website = svc.websites.get(website_id)
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    project = svc.projects.get(website.project_id)
    now = datetime.now(timezone.utc)
    range_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    since = now - range_map[range]
    logs = svc.logs.get_website_logs(website_id, since=since, until=now)
    all_logs = svc.logs.get_website_logs(website_id)

    incident_duration = None
    if website.status == "DOWN" and website.incident_started_at:
        incident_duration = incident_duration_label(website.incident_started_at)

    windows = uptime_windows(all_logs)
    range_uptime = calc_uptime(logs)

    return {
        "website": website,
        "project": project,
        "uptime": range_uptime,
        "uptime_windows": windows,
        "avg_response_time": avg_response_time(logs),
        "incident_duration": incident_duration,
        "response_time_series": response_time_series(logs),
        "status_timeline": status_timeline(logs),
        "status_codes": status_code_distribution(logs),
        "incidents": svc.state.get_incidents(website_id),
        "range": range,
        "log_count": len(logs),
    }
