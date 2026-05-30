from __future__ import annotations

from _bootstrap import ensure_import_path

ensure_import_path()

from elward_wcc.actions import execute_action  # noqa: E402
from elward_wcc.db import init_db  # noqa: E402


def main() -> None:
    init_db()
    result = execute_action("open_browser_tabs", storage={})
    print(result.message)


if __name__ == "__main__":
    main()
