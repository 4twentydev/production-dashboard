from __future__ import annotations

import argparse

from _bootstrap import ensure_import_path

ensure_import_path()

from elward_wcc.actions import execute_action  # noqa: E402
from elward_wcc.db import init_db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-ref", default="")
    parser.add_argument("--release-ref", default="")
    args = parser.parse_args()
    init_db()
    result = execute_action(
        "create_blank_release_checklist",
        storage={},
        payload={"job_ref": args.job_ref, "release_ref": args.release_ref},
    )
    print(result.message)


if __name__ == "__main__":
    main()
