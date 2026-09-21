"""Pydantic models for application settings."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailSettings(BaseModel):
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""
    recipients: list[str] = Field(default_factory=list)
    use_tls: bool = True

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: list[str]) -> list[str]:
        cleaned = []
        for item in v:
            email = item.strip()
            if email and email not in cleaned:
                cleaned.append(email)
        return cleaned


class EmailSettingsUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = Field(default=None, ge=1, le=65535)
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    recipients: Optional[list[str]] = None
    use_tls: Optional[bool] = None

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        cleaned = []
        for item in v:
            email = item.strip()
            if email and email not in cleaned:
                cleaned.append(email)
        return cleaned


class EmailSettingsPublic(BaseModel):
    """Public email settings — password never exposed."""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    password_configured: bool = False
    from_email: str = ""
    recipients: list[str] = Field(default_factory=list)
    use_tls: bool = True


class AppSettings(BaseModel):
    email: EmailSettings = Field(default_factory=EmailSettings)
    allow_private_urls: bool = False
    max_concurrent_checks: int = 20
    log_retention_days: int = 31
    timezone: str = "Asia/Kolkata"


class TestEmailRequest(BaseModel):
    recipient: Optional[str] = None
