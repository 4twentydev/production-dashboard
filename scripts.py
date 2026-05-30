from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from elward_wcc.actions import ACTION_SPECS, ensure_registry, execute_action, list_actions, seeded_defaults  # noqa: F401

