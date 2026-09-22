"""Projects API."""

from fastapi import APIRouter, HTTPException

from app.models.project import Project, ProjectCreate, ProjectUpdate
from app.services import get_services

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[Project])
def list_projects():
    return get_services().projects.list_all()


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str):
    project = get_services().projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=Project, status_code=201)
def create_project(payload: ProjectCreate):
    return get_services().projects.create(payload)


@router.put("/{project_id}", response_model=Project)
def update_project(project_id: str, payload: ProjectUpdate):
    project = get_services().projects.update(project_id, payload)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str):
    svc = get_services()
    project = svc.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    websites = svc.websites.list_all(project_id=project_id)
    website_ids = [w.id for w in websites]
    apis = svc.apis.list_all(project_id=project_id)
    api_ids = [a.id for a in apis]

    svc.websites.delete_by_project(project_id)
    svc.apis.delete_by_project(project_id)
    svc.logs.delete_by_project(project_id)
    svc.state.remove_project_sites(website_ids + api_ids)
    svc.projects.delete(project_id)

    return {"ok": True, "deleted_websites": len(website_ids), "deleted_apis": len(api_ids)}
