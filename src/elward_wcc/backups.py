from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .config import BACKUP_DIR, DB_PATH
from .db import get_setting
from .db import record_backup


def backup_database() -> Path:
    backup_root = Path(get_setting("backup_dir", str(BACKUP_DIR)) or str(BACKUP_DIR))
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_root / f"elward_wcc-{stamp}.sqlite3"
    source = sqlite3.connect(DB_PATH)
    try:
        target = sqlite3.connect(backup_path)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    size_bytes = backup_path.stat().st_size
    record_backup(str(backup_path), size_bytes=size_bytes, status="ok", message="Database backup created.")
    return backup_path
