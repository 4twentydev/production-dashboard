from __future__ import annotations

from getpass import getpass

from _bootstrap import ensure_import_path, storage_from_pin

ensure_import_path()

from elward_wcc.actions import execute_action  # noqa: E402


def main() -> None:
    pin = getpass("PIN (leave blank if not required): ").strip() or None
    storage = storage_from_pin(pin)
    result = execute_action("refresh_job_index", storage=storage)
    print(result.message)


if __name__ == "__main__":
    main()
