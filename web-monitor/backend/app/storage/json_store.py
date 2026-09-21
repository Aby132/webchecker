"""Atomic JSON file storage helpers."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_lock = threading.RLock()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically via temp file + replace."""
    ensure_dir(path.parent)
    with _lock:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


def read_json(path: Path, default: Any = None) -> Any:
    with _lock:
        if not path.exists():
            return default if default is not None else {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            backup = path.with_suffix(path.suffix + ".bak")
            if backup.exists():
                with open(backup, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            return default if default is not None else {}


def backup_file(path: Path, backup_dir: Path) -> Path | None:
    if not path.exists():
        return None
    ensure_dir(backup_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"{path.stem}_{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    return dest


class JsonStore:
    """Thread-safe JSON document store for a single file."""

    def __init__(self, path: Path, default: Any = None):
        self.path = path
        self.default = default if default is not None else []
        ensure_dir(path.parent)
        if not path.exists():
            atomic_write_json(path, self.default)

    def read(self) -> Any:
        return read_json(self.path, default=self.default)

    def write(self, data: Any) -> None:
        atomic_write_json(self.path, data)

    def update(self, updater) -> Any:
        with _lock:
            data = self.read()
            result = updater(data)
            self.write(data if result is None else result)
            return self.read()
