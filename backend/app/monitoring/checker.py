"""HTTP website and API checker with SSRF protections."""

from __future__ import annotations

import ipaddress
import json
import logging
import socket
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

import httpx

from app.models.api_monitor import BODY_METHODS
from app.monitoring.validation import validate_response
from app.secrets_mask import sanitize_error_text

if TYPE_CHECKING:
    from app.models.api_monitor import ApiMonitor

logger = logging.getLogger(__name__)

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata",
}

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Cloud metadata
METADATA_IPS = {"169.254.169.254", "fd00:ec2::254"}


@dataclass
class CheckResult:
    status: str  # UP or DOWN
    status_code: Optional[int]
    response_time: Optional[float]
    error: Optional[str]
    method: str = "GET"
    url: str = ""


def is_private_or_blocked_host(hostname: str, allow_private: bool = False) -> tuple[bool, str]:
    """Return (blocked, reason)."""
    if not hostname:
        return True, "Empty hostname"

    host = hostname.lower().strip("[]")
    if host in BLOCKED_HOSTNAMES:
        return True, f"Blocked hostname: {host}"

    # Literal IP
    try:
        ip = ipaddress.ip_address(host)
        if str(ip) in METADATA_IPS:
            return True, "Blocked cloud metadata address"
        if not allow_private:
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    return True, f"Blocked private/internal address: {ip}"
        return False, ""
    except ValueError:
        pass

    # Resolve DNS and check resolved IPs
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Let the check fail later with DNS error — not an SSRF block
        return False, ""

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if str(ip) in METADATA_IPS:
            return True, "Blocked cloud metadata address"
        if not allow_private:
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    return True, f"Hostname resolves to blocked address: {ip}"

    return False, ""


def validate_url_ssrf(url: str, allow_private: bool = False) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL"

    if parsed.scheme not in ("http", "https"):
        return False, "Only http and https URLs are allowed"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL missing hostname"

    blocked, reason = is_private_or_blocked_host(hostname, allow_private=allow_private)
    if blocked:
        return False, reason

    return True, ""


async def check_website(
    client: httpx.AsyncClient,
    url: str,
    timeout: float,
    expected_status_code: int,
    allow_private: bool = False,
) -> CheckResult:
    """Perform a single HTTP check. Never raises."""
    ok, reason = validate_url_ssrf(url, allow_private=allow_private)
    if not ok:
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=None,
            error=f"URL blocked: {reason}",
            url=url,
        )

    started = time.perf_counter()
    try:
        response = await client.get(
            url,
            timeout=httpx.Timeout(timeout),
            follow_redirects=False,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        status_code = response.status_code
        if status_code == expected_status_code:
            return CheckResult(
                status="UP",
                status_code=status_code,
                response_time=round(elapsed_ms, 2),
                error=None,
                url=url,
            )
        return CheckResult(
            status="DOWN",
            status_code=status_code,
            response_time=round(elapsed_ms, 2),
            error=f"Expected {expected_status_code}, got {status_code}",
            url=url,
        )
    except httpx.TimeoutException:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=round(elapsed_ms, 2),
            error="Timeout",
            url=url,
        )
    except httpx.ConnectError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        msg = str(exc) or "Connection error"
        if "Name or service not known" in msg or "getaddrinfo failed" in msg or "nodename" in msg.lower():
            msg = "DNS failure"
        elif "Connection refused" in msg:
            msg = "Connection refused"
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=round(elapsed_ms, 2),
            error=msg,
            url=url,
        )
    except httpx.ConnectTimeout:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=round(elapsed_ms, 2),
            error="Connection timeout",
            url=url,
        )
    except httpx.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        error = str(exc) or "HTTP error"
        if "SSL" in error or "certificate" in error.lower():
            error = f"SSL error: {error}"
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=round(elapsed_ms, 2),
            error=error,
            url=url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected check error for %s", url)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=round(elapsed_ms, 2),
            error=sanitize_error_text(f"Unexpected error: {exc}"),
            url=url,
        )


def _build_api_request(monitor: "ApiMonitor") -> tuple[dict, Optional[tuple[str, str]]]:
    headers = {str(k): str(v) for k, v in (monitor.headers or {}).items() if str(k).strip()}
    params: dict[str, str] = {}
    auth = None

    if monitor.auth_type == "bearer" and monitor.bearer_token:
        headers.setdefault("Authorization", f"Bearer {monitor.bearer_token}")
    elif monitor.auth_type == "basic":
        auth = (monitor.auth_username or "", monitor.auth_password or "")
    elif monitor.auth_type == "api_key" and monitor.api_key_value:
        key_name = (monitor.api_key_name or "X-API-Key").strip()
        if monitor.api_key_in == "query":
            params[key_name] = monitor.api_key_value
        else:
            headers[key_name] = monitor.api_key_value

    kwargs: dict = {
        "method": monitor.method,
        "url": monitor.url,
        "headers": headers,
        "follow_redirects": False,
    }
    if params:
        kwargs["params"] = params

    if monitor.method in BODY_METHODS and (monitor.body or "").strip():
        content_type = ""
        for key, value in headers.items():
            if key.lower() == "content-type":
                content_type = value.lower()
                break
        body = monitor.body or ""
        if "application/json" in content_type or body.lstrip()[:1] in "{[":
            kwargs["json"] = json.loads(body)
        else:
            kwargs["content"] = body.encode("utf-8")

    return kwargs, auth


async def check_api(
    client: httpx.AsyncClient,
    monitor: "ApiMonitor",
    allow_private: bool = False,
) -> CheckResult:
    """Perform a single API check. Never raises. Never logs secrets."""
    url = monitor.url
    ok, reason = validate_url_ssrf(url, allow_private=allow_private)
    if not ok:
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=None,
            error=f"URL blocked: {reason}",
            method=monitor.method,
            url=url,
        )

    started = time.perf_counter()
    try:
        kwargs, auth = _build_api_request(monitor)
        kwargs["timeout"] = httpx.Timeout(float(monitor.timeout))
        response = await client.request(auth=auth, **kwargs)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        status_code = response.status_code

        if status_code != monitor.expected_status_code:
            return CheckResult(
                status="DOWN",
                status_code=status_code,
                response_time=elapsed_ms,
                error=f"Expected {monitor.expected_status_code}, got {status_code}",
                method=monitor.method,
                url=url,
            )

        if monitor.validation_enabled and monitor.validation_rules:
            valid, message = validate_response(response.text, monitor.validation_rules)
            if not valid:
                return CheckResult(
                    status="DOWN",
                    status_code=status_code,
                    response_time=elapsed_ms,
                    error=sanitize_error_text(message) or "Response validation failed",
                    method=monitor.method,
                    url=url,
                )

        return CheckResult(
            status="UP",
            status_code=status_code,
            response_time=elapsed_ms,
            error=None,
            method=monitor.method,
            url=url,
        )
    except json.JSONDecodeError:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=elapsed_ms,
            error="Request body is not valid JSON",
            method=monitor.method,
            url=url,
        )
    except httpx.TimeoutException:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=elapsed_ms,
            error="Timeout",
            method=monitor.method,
            url=url,
        )
    except httpx.ConnectError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        msg = sanitize_error_text(str(exc) or "Connection error") or "Connection error"
        if "Name or service not known" in msg or "getaddrinfo failed" in msg or "nodename" in msg.lower():
            msg = "DNS failure"
        elif "Connection refused" in msg:
            msg = "Connection refused"
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=elapsed_ms,
            error=msg,
            method=monitor.method,
            url=url,
        )
    except httpx.ConnectTimeout:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=elapsed_ms,
            error="Connection timeout",
            method=monitor.method,
            url=url,
        )
    except httpx.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        error = sanitize_error_text(str(exc) or "HTTP error") or "HTTP error"
        if "SSL" in error or "certificate" in error.lower():
            error = f"SSL error: {error}"
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=elapsed_ms,
            error=error,
            method=monitor.method,
            url=url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected API check error for %s", monitor.id)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return CheckResult(
            status="DOWN",
            status_code=None,
            response_time=elapsed_ms,
            error=sanitize_error_text(f"Unexpected error: {exc}"),
            method=monitor.method,
            url=url,
        )
