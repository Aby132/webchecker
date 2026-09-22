"""Dashboard and project detail APIs."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.analytics import avg_response_time, calc_uptime, incident_duration_label
from app.models.api_monitor import to_public
from app.services import get_services

router = APIRouter(prefix="/api", tags=["dashboard"])


def _counts(items):
    enabled = [item for item in items if item.enabled]
    return {
        "up": sum(1 for item in enabled if item.status == "UP"),
        "down": sum(1 for item in enabled if item.status == "DOWN"),
        "disabled": sum(1 for item in items if not item.enabled or item.status == "DISABLED"),
        "unknown": sum(1 for item in enabled if item.status in ("UNKNOWN", None)),
    }


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
    apis = svc.apis.list_all()
    site_counts = _counts(websites)
    api_counts = _counts(apis)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    all_recent = []
    for w in websites:
        all_recent.extend(svc.logs.get_website_logs(w.id, since=since, until=now))
    for api in apis:
        all_recent.extend(svc.logs.get_api_logs(api.id, since=since, until=now))
    overall_uptime = calc_uptime(all_recent)

    down = site_counts["down"] + api_counts["down"]
    active_incidents = svc.state.get_active_incident_count()
    if active_incidents == 0:
        active_incidents = down

    project_sections = []
    for project in projects:
        sites = [w for w in websites if w.project_id == project.id]
        api_items = [a for a in apis if a.project_id == project.id]
        enabled_sites = [w for w in sites if w.enabled]
        enabled_apis = [a for a in api_items if a.enabled]
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
        api_rows = []
        for api in api_items:
            api_logs = svc.logs.get_api_logs(api.id, since=since, until=now)
            row = to_public(api).model_dump()
            row["uptime"] = calc_uptime(api_logs)
            row["project_name"] = project.name
            api_rows.append(row)
        project_sections.append(
            {
                "project": project,
                "total": len(sites),
                "operational": sum(1 for w in enabled_sites if w.status == "UP"),
                "total_apis": len(api_items),
                "operational_apis": sum(1 for a in enabled_apis if a.status == "UP"),
                "websites": site_rows,
                "apis": api_rows,
            }
        )

    state = svc.state.read()

    return {
        "summary": {
            "total_projects": len(projects),
            "total_websites": len(websites),
            "total_apis": len(apis),
            "up": site_counts["up"] + api_counts["up"],
            "down": down,
            "disabled": site_counts["disabled"] + api_counts["disabled"],
            "unknown": site_counts["unknown"] + api_counts["unknown"],
            "websites_up": site_counts["up"],
            "websites_down": site_counts["down"],
            "apis_up": api_counts["up"],
            "apis_down": api_counts["down"],
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
    apis = svc.apis.list_all(project_id=project_id)
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

    api_rows = []
    for api in apis:
        logs = svc.logs.get_api_logs(api.id, since=since, until=now)
        all_logs.extend(logs)
        row = to_public(api).model_dump()
        row["uptime"] = calc_uptime(logs)
        row["incident_duration"] = (
            incident_duration_label(api.incident_started_at) if api.status == "DOWN" else None
        )
        api_rows.append(row)

    enabled = [w for w in websites if w.enabled]
    enabled_apis = [a for a in apis if a.enabled]
    return {
        "project": project,
        "total_websites": len(websites),
        "total_apis": len(apis),
        "up": sum(1 for w in enabled if w.status == "UP") + sum(1 for a in enabled_apis if a.status == "UP"),
        "down": sum(1 for w in enabled if w.status == "DOWN") + sum(1 for a in enabled_apis if a.status == "DOWN"),
        "websites_up": sum(1 for w in enabled if w.status == "UP"),
        "websites_down": sum(1 for w in enabled if w.status == "DOWN"),
        "apis_up": sum(1 for a in enabled_apis if a.status == "UP"),
        "apis_down": sum(1 for a in enabled_apis if a.status == "DOWN"),
        "average_response_time": avg_response_time(all_logs),
        "uptime": calc_uptime(all_logs),
        "websites": rows,
        "apis": api_rows,
    }
