"""Settings / email alerts API."""

from fastapi import APIRouter, HTTPException

from app.models.settings import EmailSettingsPublic, EmailSettingsUpdate, TestEmailRequest
from app.notifications.email import send_test_email
from app.services import get_services

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/email", response_model=EmailSettingsPublic)
def get_email_settings():
    return get_services().app_settings.get_email_public()


@router.put("/email", response_model=EmailSettingsPublic)
def update_email_settings(payload: EmailSettingsUpdate):
    return get_services().app_settings.update_email(payload)


@router.post("/email/test")
async def test_email(payload: TestEmailRequest | None = None):
    svc = get_services()
    email = svc.app_settings.get_email()
    recipient = payload.recipient if payload else None
    ok, message = await send_test_email(email, recipient=recipient)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}
