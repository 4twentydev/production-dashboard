from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from elward_wcc import actions, db


def seed_database() -> None:
    db.init_db()
    actions.ensure_registry()


if __name__ == "__main__":
    seed_database()
