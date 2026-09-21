"""Application settings persistence."""

from __future__ import annotations

from pathlib import Path

from app.models.settings import AppSettings, EmailSettings, EmailSettingsPublic, EmailSettingsUpdate
from app.storage.json_store import JsonStore, backup_file


class SettingsStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store = JsonStore(
            data_dir / "settings.json",
            default=AppSettings().model_dump(),
        )
        self.backup_dir = data_dir / "backups"

    def get(self) -> AppSettings:
        data = self.store.read()
        if not isinstance(data, dict):
            data = AppSettings().model_dump()
        return AppSettings(**data)

    def get_email_public(self) -> EmailSettingsPublic:
        email = self.get().email
        return EmailSettingsPublic(
            smtp_host=email.smtp_host,
            smtp_port=email.smtp_port,
            smtp_username=email.smtp_username,
            password_configured=bool(email.smtp_password),
            from_email=email.from_email,
            recipients=email.recipients,
            use_tls=email.use_tls,
        )

    def update_email(self, payload: EmailSettingsUpdate) -> EmailSettingsPublic:
        backup_file(self.store.path, self.backup_dir)
        settings = self.get()
        current = settings.email.model_dump()
        updates = payload.model_dump(exclude_unset=True)

        # Do not clear password if empty string sent as "unchanged"
        if "smtp_password" in updates:
            if updates["smtp_password"] is None or updates["smtp_password"] == "":
                updates.pop("smtp_password")

        current.update(updates)
        settings.email = EmailSettings(**current)
        self.store.write(settings.model_dump())
        return self.get_email_public()

    def get_email(self) -> EmailSettings:
        return self.get().email
