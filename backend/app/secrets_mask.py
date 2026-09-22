"""Mask and merge secrets so they are never exposed in APIs, logs, or errors."""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional

SENSITIVE_HEADER_MARKERS = (
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "token",
    "secret",
    "password",
    "passwd",
    "api-key",
    "apikey",
    "x-api-key",
    "access-key",
    "credential",
    "private-key",
)

_REDACT_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)(\S+)"),
    re.compile(r"(?i)(basic\s+)([A-Za-z0-9+/=]+)"),
    re.compile(r"(?i)((?:api[-_]?key|token|secret|password|authorization)\s*[:=]\s*)(\S+)"),
]


def is_sensitive_header(key: str) -> bool:
    lowered = (key or "").strip().lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in SENSITIVE_HEADER_MARKERS)


def is_masked_value(value: Optional[str]) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if text.lower().startswith("bearer "):
        text = text[7:].strip()
    if not text:
        return False
    return bool(re.fullmatch(r"\*+", text))


def mask_secret_value(value: Optional[str], header_name: str = "") -> str:
    if not value:
        return ""
    text = str(value)
    if header_name.lower() == "authorization" or text.lower().startswith("bearer "):
        if text.lower().startswith("bearer "):
            return "Bearer ************"
        return "************"
    return "************"


def mask_headers(headers: Optional[Mapping[str, Any]]) -> dict[str, str]:
    masked: dict[str, str] = {}
    for key, value in (headers or {}).items():
        text = "" if value is None else str(value)
        if is_sensitive_header(str(key)):
            masked[str(key)] = mask_secret_value(text, str(key))
        else:
            masked[str(key)] = text
    return masked


def merge_headers(existing: Optional[Mapping[str, Any]], incoming: Optional[Mapping[str, Any]]) -> dict[str, str]:
    current = {str(k): "" if v is None else str(v) for k, v in (existing or {}).items()}
    if incoming is None:
        return current
    merged: dict[str, str] = {}
    for key, value in incoming.items():
        name = str(key).strip()
        if not name:
            continue
        text = "" if value is None else str(value)
        if text == "" or is_masked_value(text):
            if name in current:
                merged[name] = current[name]
            continue
        merged[name] = text
    return merged


def merge_secret(existing: Optional[str], incoming: Optional[str]) -> str:
    if incoming is None or incoming == "" or is_masked_value(incoming):
        return existing or ""
    return incoming


def sanitize_error_text(message: Optional[str]) -> Optional[str]:
    if not message:
        return message
    text = str(message)
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}************", text)
    return text
