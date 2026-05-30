from __future__ import annotations

import sys
from pathlib import Path


def ensure_import_path() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def storage_from_pin(pin: str | None, *, unlock_minutes: int = 480) -> dict[str, object]:
    ensure_import_path()
    from elward_wcc import security  # noqa: WPS433
    from elward_wcc.db import init_db  # noqa: WPS433

    init_db()
    storage: dict[str, object] = {}
    if pin:
        if not security.verify_pin(pin):
            raise SystemExit("Invalid PIN.")
        security.register_unlock(storage, minutes=unlock_minutes)
    return storage
