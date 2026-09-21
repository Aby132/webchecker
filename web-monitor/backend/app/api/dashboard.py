"""Dashboard and project detail APIs."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.analytics import avg_response_time, calc_uptime, incident_duration_label
from app.services import get_services

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/health")
def health():
    svc = get_services()
    state = svc.state.read()
    return {
        "status": "ok",
        "engine_running": bool(state.get("engine_running")),
        "started_at": state.get("started_at"),
        "last_tick_at": state.get("last_tick_at"),
        "checks_total": state.get("checks_total", 0),
    }


@router.get("/dashboard")
def dashboard():
    svc = get_services()
    projects = svc.projects.list_all()
    websites = svc.websites.list_all()

    up = sum(1 for w in websites if w.enabled and w.status == "UP")
    down = sum(1 for w in websites if w.enabled and w.status == "DOWN")
    disabled = sum(1 for w in websites if not w.enabled or w.status == "DISABLED")
    unknown = sum(1 for w in websites if w.enabled and w.status in ("UNKNOWN", None))

    # Overall uptime from last 24h of logs across all sites
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    all_recent = []
    for w in websites:
        all_recent.extend(svc.logs.get_website_logs(w.id, since=since, until=now))
    overall_uptime = calc_uptime(all_recent)

    active_incidents = svc.state.get_active_incident_count()
    # Also count currently DOWN websites as incidents if state is missing
    if active_incidents == 0:
        active_incidents = down

    project_sections = []
    for project in projects:
        sites = [w for w in websites if w.project_id == project.id]
        enabled_sites = [w for w in sites if w.enabled]
        up_count = sum(1 for w in enabled_sites if w.status == "UP")
        site_rows = []
        for w in sites:
            site_logs = svc.logs.get_website_logs(w.id, since=since, until=now)
            site_rows.append(
                {
                    **w.model_dump(),
                    "uptime": calc_uptime(site_logs),
                    "project_name": project.name,
                }
            )
        project_sections.append(
            {
                "project": project,
                "total": len(sites),
                "operational": up_count,
                "websites": site_rows,
            }
        )

    state = svc.state.read()

    return {
        "summary": {
            "total_projects": len(projects),
            "total_websites": len(websites),
            "up": up,
            "down": down,
            "disabled": disabled,
            "unknown": unknown,
            "overall_uptime": overall_uptime,
            "active_incidents": active_incidents,
        },
        "projects": project_sections,
        "engine": {
            "running": bool(state.get("engine_running")),
            "started_at": state.get("started_at"),
            "last_tick_at": state.get("last_tick_at"),
        },
    }


@router.get("/projects/{project_id}/details")
def project_details(project_id: str):
    svc = get_services()
    project = svc.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    websites = svc.websites.list_all(project_id=project_id)
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    all_logs = []
    rows = []
    for w in websites:
        logs = svc.logs.get_website_logs(w.id, since=since, until=now)
        all_logs.extend(logs)
        rows.append(
            {
                **w.model_dump(),
                "uptime": calc_uptime(logs),
                "incident_duration": (
                    incident_duration_label(w.incident_started_at)
                    if w.status == "DOWN"
                    else None
                ),
            }
        )

    enabled = [w for w in websites if w.enabled]
    return {
        "project": project,
        "total_websites": len(websites),
        "up": sum(1 for w in enabled if w.status == "UP"),
        "down": sum(1 for w in enabled if w.status == "DOWN"),
        "average_response_time": avg_response_time(all_logs),
        "uptime": calc_uptime(all_logs),
        "websites": rows,
    }
