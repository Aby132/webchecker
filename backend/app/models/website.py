"""Pydantic models for websites."""

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


INTERVAL_PRESETS = [10, 15, 30, 45, 60, 90, 120]
MIN_INTERVAL = 10
MAX_INTERVAL = 120
MIN_TIMEOUT = 1
MAX_TIMEOUT = 60


def sanitize_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Name cannot be empty")
    if len(cleaned) > 200:
        raise ValueError("Name must be 200 characters or fewer")
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    return cleaned


def validate_url(url: str) -> str:
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("URL must include a valid host")
    if len(cleaned) > 2048:
        raise ValueError("URL is too long")
    return cleaned


class WebsiteBase(BaseModel):
    project_id: str
    name: str
    url: str
    enabled: bool = True
    check_interval: int = Field(default=60, ge=MIN_INTERVAL, le=MAX_INTERVAL)
    timeout: int = Field(default=10, ge=MIN_TIMEOUT, le=MAX_TIMEOUT)
    expected_status_code: int = Field(default=200, ge=100, le=599)
    alert_enabled: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return sanitize_name(v)

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("check_interval")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < MIN_INTERVAL or v > MAX_INTERVAL:
            raise ValueError(
                f"check_interval must be between {MIN_INTERVAL} and {MAX_INTERVAL} seconds"
            )
        return v


class WebsiteCreate(WebsiteBase):
    pass


class WebsiteUpdate(BaseModel):
    project_id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None
    check_interval: Optional[int] = Field(default=None, ge=MIN_INTERVAL, le=MAX_INTERVAL)
    timeout: Optional[int] = Field(default=None, ge=MIN_TIMEOUT, le=MAX_TIMEOUT)
    expected_status_code: Optional[int] = Field(default=None, ge=100, le=599)
    alert_enabled: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_name(v)

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_url(v)

    @field_validator("check_interval")
    @classmethod
    def validate_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < MIN_INTERVAL or v > MAX_INTERVAL:
            raise ValueError(
                f"check_interval must be between {MIN_INTERVAL} and {MAX_INTERVAL} seconds"
            )
        return v


class Website(WebsiteBase):
    id: str
    monitor_type: str = "WEBSITE"
    status: str = "UNKNOWN"  # UP, DOWN, DEGRADED, DISABLED, UNKNOWN
    last_status_code: Optional[int] = None
    last_response_time: Optional[float] = None
    last_checked: Optional[str] = None
    last_error: Optional[str] = None
    last_success_at: Optional[str] = None
    incident_started_at: Optional[str] = None
    next_check_at: Optional[str] = None
    created_at: str
    updated_at: str
