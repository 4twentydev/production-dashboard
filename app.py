from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from nicegui import ui

load_dotenv()

storage_secret = os.getenv(
    "NICEGUI_STORAGE_SECRET",
    "ufahh47hfaw478hfa7chra7wlfbhwa48h7hca7w4h8caw3c489cbgaw4hae",
)

ui.run(
    host="0.0.0.0",
    port=8080,
    title="Elward Command Center",
    storage_secret=storage_secret,
)

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from elward_wcc.main import main

if __name__ == "__main__":
    main()
