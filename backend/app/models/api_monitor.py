"""Pydantic models for API monitors."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.website import MAX_INTERVAL, MAX_TIMEOUT, MIN_INTERVAL, MIN_TIMEOUT, sanitize_name, validate_url
from app.secrets_mask import mask_headers

HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
AUTH_TYPES = ("none", "bearer", "basic", "api_key", "custom_headers")
VALIDATION_OPERATORS = ("equals", "not_equals", "contains", "not_contains", "exists", "not_exists")
API_KEY_LOCATIONS = ("header", "query")
BODY_METHODS = {"POST", "PUT", "PATCH"}


class ValidationRule(BaseModel):
    field: str
    operator: Literal[
        "equals",
        "not_equals",
        "contains",
        "not_contains",
        "exists",
        "not_exists",
    ]
    value: Optional[str] = None

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("Validation field cannot be empty")
        if len(cleaned) > 300:
            raise ValueError("Validation field is too long")
        return cleaned

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        text = str(v)
        if len(text) > 2000:
            raise ValueError("Validation value is too long")
        return text

    @model_validator(mode="after")
    def require_value(self) -> "ValidationRule":
        if self.operator not in ("exists", "not_exists") and self.value is None:
            raise ValueError(f"value is required for operator {self.operator}")
        return self


def _normalize_headers(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    if isinstance(headers, list):
        result: dict[str, str] = {}
        for item in headers:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "").strip()
            if not key:
                continue
            result[key] = "" if item.get("value") is None else str(item.get("value"))
        return result
    if not isinstance(headers, dict):
        raise ValueError("headers must be an object of key/value pairs")
    cleaned: dict[str, str] = {}
    for key, value in headers.items():
        name = str(key).strip()
        if not name:
            continue
        if len(name) > 200:
            raise ValueError("Header name is too long")
        text = "" if value is None else str(value)
        if len(text) > 8000:
            raise ValueError("Header value is too long")
        cleaned[name] = text
    if len(cleaned) > 40:
        raise ValueError("A maximum of 40 headers is allowed")
    return cleaned


def _validate_json_body(body: Optional[str], headers: dict[str, str], method: str) -> Optional[str]:
    if body is None:
        return None
    text = body.strip()
    if not text:
        return ""
    if len(text) > 20000:
        raise ValueError("Request body is too large")
    content_type = ""
    for key, value in headers.items():
        if key.lower() == "content-type":
            content_type = value.lower()
            break
    json_like = "application/json" in content_type or text[:1] in "{["
    if json_like:
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON") from exc
    return text


class ApiMonitorBase(BaseModel):
    project_id: str
    name: str
    url: str
    method: str = "GET"
    enabled: bool = True
    check_interval: int = Field(default=60, ge=MIN_INTERVAL, le=MAX_INTERVAL)
    timeout: int = Field(default=10, ge=MIN_TIMEOUT, le=MAX_TIMEOUT)
    expected_status_code: int = Field(default=200, ge=100, le=599)
    alert_enabled: bool = True
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = ""
    auth_type: str = "none"
    bearer_token: str = ""
    auth_username: str = ""
    auth_password: str = ""
    api_key_name: str = ""
    api_key_value: str = ""
    api_key_in: str = "header"
    validation_enabled: bool = False
    validation_rules: list[ValidationRule] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return sanitize_name(v)

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        method = (v or "GET").strip().upper()
        if method not in HTTP_METHODS:
            raise ValueError(f"method must be one of: {', '.join(HTTP_METHODS)}")
        return method

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        auth = (v or "none").strip().lower()
        if auth not in AUTH_TYPES:
            raise ValueError(f"auth_type must be one of: {', '.join(AUTH_TYPES)}")
        return auth

    @field_validator("api_key_in")
    @classmethod
    def validate_api_key_in(cls, v: str) -> str:
        location = (v or "header").strip().lower()
        if location not in API_KEY_LOCATIONS:
            raise ValueError("api_key_in must be header or query")
        return location

    @field_validator("headers", mode="before")
    @classmethod
    def validate_headers(cls, v: Any) -> dict[str, str]:
        return _normalize_headers(v)

    @field_validator("check_interval")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < MIN_INTERVAL or v > MAX_INTERVAL:
            raise ValueError(
                f"check_interval must be between {MIN_INTERVAL} and {MAX_INTERVAL} seconds"
            )
        return v

    @field_validator("validation_rules")
    @classmethod
    def validate_rules(cls, v: list[ValidationRule]) -> list[ValidationRule]:
        if len(v) > 30:
            raise ValueError("A maximum of 30 validation rules is allowed")
        return v

    @model_validator(mode="after")
    def validate_body_and_auth(self) -> "ApiMonitorBase":
        self.body = _validate_json_body(self.body, self.headers, self.method)
        if self.method not in BODY_METHODS and self.body:
            # Allowed but unused for GET/HEAD/OPTIONS/DELETE unless explicitly sent.
            pass
        if self.auth_type == "api_key" and not (self.api_key_name or "").strip():
            raise ValueError("api_key_name is required for API key authentication")
        if self.auth_type == "basic" and not (self.auth_username or "").strip():
            raise ValueError("auth_username is required for basic authentication")
        return self


class ApiMonitorCreate(ApiMonitorBase):
    pass


class ApiMonitorUpdate(BaseModel):
    project_id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    enabled: Optional[bool] = None
    check_interval: Optional[int] = Field(default=None, ge=MIN_INTERVAL, le=MAX_INTERVAL)
    timeout: Optional[int] = Field(default=None, ge=MIN_TIMEOUT, le=MAX_TIMEOUT)
    expected_status_code: Optional[int] = Field(default=None, ge=100, le=599)
    alert_enabled: Optional[bool] = None
    headers: Optional[dict[str, str]] = None
    body: Optional[str] = None
    auth_type: Optional[str] = None
    bearer_token: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    api_key_name: Optional[str] = None
    api_key_value: Optional[str] = None
    api_key_in: Optional[str] = None
    validation_enabled: Optional[bool] = None
    validation_rules: Optional[list[ValidationRule]] = None

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

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        method = v.strip().upper()
        if method not in HTTP_METHODS:
            raise ValueError(f"method must be one of: {', '.join(HTTP_METHODS)}")
        return method

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        auth = v.strip().lower()
        if auth not in AUTH_TYPES:
            raise ValueError(f"auth_type must be one of: {', '.join(AUTH_TYPES)}")
        return auth

    @field_validator("api_key_in")
    @classmethod
    def validate_api_key_in(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        location = v.strip().lower()
        if location not in API_KEY_LOCATIONS:
            raise ValueError("api_key_in must be header or query")
        return location

    @field_validator("headers", mode="before")
    @classmethod
    def validate_headers(cls, v: Any) -> Any:
        if v is None:
            return v
        return _normalize_headers(v)

    @field_validator("validation_rules")
    @classmethod
    def validate_rules(cls, v: Optional[list[ValidationRule]]) -> Optional[list[ValidationRule]]:
        if v is None:
            return v
        if len(v) > 30:
            raise ValueError("A maximum of 30 validation rules is allowed")
        return v

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        text = v.strip()
        if not text:
            return ""
        if len(text) > 20000:
            raise ValueError("Request body is too large")
        if text[:1] in "{[":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError("Request body must be valid JSON") from exc
        return text


class ApiMonitor(ApiMonitorBase):
    id: str
    monitor_type: str = "API"
    status: str = "UNKNOWN"
    last_status_code: Optional[int] = None
    last_response_time: Optional[float] = None
    last_checked: Optional[str] = None
    last_error: Optional[str] = None
    last_success_at: Optional[str] = None
    incident_started_at: Optional[str] = None
    next_check_at: Optional[str] = None
    created_at: str
    updated_at: str


class ApiMonitorPublic(BaseModel):
    """API monitor as returned to the frontend — secrets are masked or omitted."""

    id: str
    project_id: str
    name: str
    url: str
    method: str
    enabled: bool
    check_interval: int
    timeout: int
    expected_status_code: int
    alert_enabled: bool
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = ""
    auth_type: str = "none"
    auth_username: str = ""
    api_key_name: str = ""
    api_key_in: str = "header"
    bearer_configured: bool = False
    password_configured: bool = False
    api_key_configured: bool = False
    validation_enabled: bool = False
    validation_rules: list[ValidationRule] = Field(default_factory=list)
    monitor_type: str = "API"
    status: str = "UNKNOWN"
    last_status_code: Optional[int] = None
    last_response_time: Optional[float] = None
    last_checked: Optional[str] = None
    last_error: Optional[str] = None
    last_success_at: Optional[str] = None
    incident_started_at: Optional[str] = None
    next_check_at: Optional[str] = None
    created_at: str
    updated_at: str


def to_public(monitor: ApiMonitor) -> ApiMonitorPublic:
    return ApiMonitorPublic(
        id=monitor.id,
        project_id=monitor.project_id,
        name=monitor.name,
        url=monitor.url,
        method=monitor.method,
        enabled=monitor.enabled,
        check_interval=monitor.check_interval,
        timeout=monitor.timeout,
        expected_status_code=monitor.expected_status_code,
        alert_enabled=monitor.alert_enabled,
        headers=mask_headers(monitor.headers),
        body=monitor.body or "",
        auth_type=monitor.auth_type,
        auth_username=monitor.auth_username,
        api_key_name=monitor.api_key_name,
        api_key_in=monitor.api_key_in,
        bearer_configured=bool(monitor.bearer_token),
        password_configured=bool(monitor.auth_password),
        api_key_configured=bool(monitor.api_key_value),
        validation_enabled=monitor.validation_enabled,
        validation_rules=monitor.validation_rules,
        monitor_type="API",
        status=monitor.status,
        last_status_code=monitor.last_status_code,
        last_response_time=monitor.last_response_time,
        last_checked=monitor.last_checked,
        last_error=monitor.last_error,
        last_success_at=monitor.last_success_at,
        incident_started_at=monitor.incident_started_at,
        next_check_at=monitor.next_check_at,
        created_at=monitor.created_at,
        updated_at=monitor.updated_at,
    )
