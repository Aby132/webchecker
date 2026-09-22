"""HTML email notifications for DOWN and RECOVERY events."""

from __future__ import annotations

import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from zoneinfo import ZoneInfo

import aiosmtplib

from app.models.settings import EmailSettings

logger = logging.getLogger(__name__)


def _format_dt(iso_str: Optional[str], tz_name: str = "Asia/Kolkata") -> str:
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            from datetime import timezone

            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(ZoneInfo(tz_name))
        return local.strftime("%d %B %Y %H:%M:%S %Z")
    except Exception:
        return iso_str


def _format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "N/A"
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs or not parts:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    return " ".join(parts)


def _base_styles() -> str:
    return """
    body { font-family: 'Segoe UI', Arial, sans-serif; background:#0f1419; color:#e7ecf3; margin:0; padding:24px; }
    .card { max-width:640px; margin:0 auto; background:#1a2332; border:1px solid #2a3648; border-radius:12px; overflow:hidden; }
    .header { padding:20px 24px; border-bottom:1px solid #2a3648; }
    .header h1 { margin:0; font-size:18px; letter-spacing:0.02em; }
    .badge { display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700; margin-top:8px; }
    .badge-down { background:#3b1219; color:#ff6b7a; }
    .badge-up { background:#0f2e1f; color:#3dd68c; }
    .body { padding:24px; }
    .row { display:flex; justify-content:space-between; gap:16px; padding:10px 0; border-bottom:1px solid #243044; }
    .label { color:#8b9bb4; font-size:13px; min-width:140px; }
    .value { color:#e7ecf3; font-size:13px; text-align:right; word-break:break-all; }
    .footer { padding:16px 24px; color:#6b7c93; font-size:12px; border-top:1px solid #2a3648; }
    """


def _monitor_label(context: dict) -> str:
    kind = (context.get("monitor_kind") or "WEBSITE").upper()
    return "API" if kind == "API" else "Website"


def build_down_email(context: dict) -> tuple[str, str, str]:
    project = context.get("project_name", "")
    website = context.get("website_name", "")
    label = _monitor_label(context)
    subject = f"🚨 {label.upper()} DOWN | {project} | {website}"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_base_styles()}</style></head>
<body>
  <div class="card">
    <div class="header">
      <h1>Monitoring Alert</h1>
      <span class="badge badge-down">DOWN</span>
    </div>
    <div class="body">
      <div class="row"><span class="label">Status</span><span class="value">DOWN</span></div>
      <div class="row"><span class="label">Project</span><span class="value">{project}</span></div>
      <div class="row"><span class="label">{label}</span><span class="value">{website}</span></div>
      <div class="row"><span class="label">URL</span><span class="value">{context.get('url','')}</span></div>
      <div class="row"><span class="label">HTTP Status</span><span class="value">{context.get('http_status_label','N/A')}</span></div>
      <div class="row"><span class="label">Response Time</span><span class="value">{context.get('response_time_label','N/A')}</span></div>
      <div class="row"><span class="label">Detected At</span><span class="value">{context.get('detected_at','')}</span></div>
      <div class="row"><span class="label">Check Interval</span><span class="value">{context.get('check_interval')} seconds</span></div>
      <div class="row"><span class="label">Timeout</span><span class="value">{context.get('timeout')} seconds</span></div>
      <div class="row"><span class="label">Expected Status</span><span class="value">{context.get('expected_status')}</span></div>
      <div class="row"><span class="label">Actual Status</span><span class="value">{context.get('actual_status','N/A')}</span></div>
      <div class="row"><span class="label">Error</span><span class="value">{context.get('error','N/A')}</span></div>
      <div class="row"><span class="label">Last Successful Check</span><span class="value">{context.get('last_success','N/A')}</span></div>
    </div>
    <div class="footer">Web Monitor — self-hosted uptime monitoring</div>
  </div>
</body></html>"""

    text = (
        f"Monitoring Alert\nStatus: DOWN\nProject: {project}\n{label}: {website}\n"
        f"URL: {context.get('url')}\nError: {context.get('error')}\n"
        f"Detected At: {context.get('detected_at')}\n"
    )
    return subject, html, text


def build_recovery_email(context: dict) -> tuple[str, str, str]:
    project = context.get("project_name", "")
    website = context.get("website_name", "")
    label = _monitor_label(context)
    subject = f"✅ {label.upper()} RECOVERED | {project} | {website}"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_base_styles()}</style></head>
<body>
  <div class="card">
    <div class="header">
      <h1>Monitoring Recovery</h1>
      <span class="badge badge-up">RECOVERED</span>
    </div>
    <div class="body">
      <div class="row"><span class="label">Status</span><span class="value">RECOVERED</span></div>
      <div class="row"><span class="label">Project</span><span class="value">{project}</span></div>
      <div class="row"><span class="label">{label}</span><span class="value">{website}</span></div>
      <div class="row"><span class="label">URL</span><span class="value">{context.get('url','')}</span></div>
      <div class="row"><span class="label">Current HTTP Status</span><span class="value">{context.get('actual_status','')}</span></div>
      <div class="row"><span class="label">Response Time</span><span class="value">{context.get('response_time_label','N/A')}</span></div>
      <div class="row"><span class="label">Recovered At</span><span class="value">{context.get('recovered_at','')}</span></div>
      <div class="row"><span class="label">Downtime Duration</span><span class="value">{context.get('duration','')}</span></div>
      <div class="row"><span class="label">Last Failure</span><span class="value">{context.get('last_failure','N/A')}</span></div>
      <div class="row"><span class="label">Failure Started</span><span class="value">{context.get('failure_started','N/A')}</span></div>
    </div>
    <div class="footer">Web Monitor — self-hosted uptime monitoring</div>
  </div>
</body></html>"""

    text = (
        f"Monitoring Recovery\nStatus: RECOVERED\nProject: {project}\n{label}: {website}\n"
        f"URL: {context.get('url')}\nDuration: {context.get('duration')}\n"
        f"Recovered At: {context.get('recovered_at')}\n"
    )
    return subject, html, text


async def send_email(
    settings: EmailSettings,
    subject: str,
    html: str,
    text: str,
    recipients: Optional[list[str]] = None,
) -> tuple[bool, str]:
    to_list = recipients or settings.recipients
    if not to_list:
        return False, "No recipients configured"
    if not settings.smtp_host or not settings.from_email:
        return False, "SMTP host and from email are required"

    message = MIMEMultipart("alternative")
    message["From"] = settings.from_email
    message["To"] = ", ".join(to_list)
    message["Subject"] = subject
    message.attach(MIMEText(text, "plain", "utf-8"))
    message.attach(MIMEText(html, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.use_tls,
        )
        return True, "Email sent successfully"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send email")
        return False, str(exc)


async def send_down_alert(settings: EmailSettings, context: dict, tz_name: str = "Asia/Kolkata") -> tuple[bool, str]:
    context = {
        **context,
        "detected_at": _format_dt(context.get("detected_at"), tz_name),
        "last_success": _format_dt(context.get("last_success"), tz_name),
        "response_time_label": (
            f"{context['response_time']} ms"
            if context.get("response_time") is not None
            else "N/A"
        ),
        "http_status_label": (
            str(context.get("actual_status"))
            if context.get("actual_status") is not None
            else (context.get("error") or "N/A")
        ),
    }
    subject, html, text = build_down_email(context)
    return await send_email(settings, subject, html, text)


async def send_recovery_alert(
    settings: EmailSettings, context: dict, tz_name: str = "Asia/Kolkata"
) -> tuple[bool, str]:
    context = {
        **context,
        "recovered_at": _format_dt(context.get("recovered_at"), tz_name),
        "failure_started": _format_dt(context.get("failure_started"), tz_name),
        "duration": _format_duration(context.get("duration_seconds")),
        "response_time_label": (
            f"{context['response_time']} ms"
            if context.get("response_time") is not None
            else "N/A"
        ),
    }
    subject, html, text = build_recovery_email(context)
    return await send_email(settings, subject, html, text)


async def send_test_email(settings: EmailSettings, recipient: Optional[str] = None) -> tuple[bool, str]:
    recipients = [recipient] if recipient else None
    subject = "✅ Web Monitor — Test Email"
    html = f"""<!DOCTYPE html>
<html><head><style>{_base_styles()}</style></head>
<body>
  <div class="card">
    <div class="header"><h1>Test Email</h1><span class="badge badge-up">OK</span></div>
    <div class="body">
      <p>Your SMTP configuration is working correctly.</p>
      <p>Web Monitor can deliver downtime and recovery alerts.</p>
    </div>
    <div class="footer">Web Monitor</div>
  </div>
</body></html>"""
    text = "Your SMTP configuration is working correctly."
    return await send_email(settings, subject, html, text, recipients=recipients)


# Re-export helpers used by worker
format_duration = _format_duration
format_dt = _format_dt
