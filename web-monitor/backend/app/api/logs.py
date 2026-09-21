"""Logs API with CSV/JSON export."""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services import get_services

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {value}") from exc


@router.get("")
def get_logs(
    project_id: Optional[str] = None,
    website_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=1000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
):
    svc = get_services()
    logs = svc.logs.get_logs(
        project_id=project_id,
        website_id=website_id,
        status=status,
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(logs),
        "offset": offset,
        "limit": limit,
        "logs": logs,
    }


@router.get("/export")
def export_logs(
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    project_id: Optional[str] = None,
    website_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    svc = get_services()
    logs = svc.logs.get_logs(
        project_id=project_id,
        website_id=website_id,
        status=status,
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        limit=100000,
        offset=0,
    )

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if format == "json":
        content = svc.logs.to_json(logs)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="web-monitor-logs-{stamp}.json"'
            },
        )

    content = svc.logs.to_csv(logs)
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="web-monitor-logs-{stamp}.csv"'
        },
    )
