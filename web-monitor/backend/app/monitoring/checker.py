"""HTTP website checker with SSRF protections."""

from __future__ import annotations

import ipaddress
import logging
import socket
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx

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
            error=f"Unexpected error: {exc}",
            url=url,
        )
