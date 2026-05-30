from __future__ import annotations

import re
from pathlib import Path

JOB_PATTERN = re.compile(r"(?P<job>\d{5})")
RELEASE_PATTERN = re.compile(r"\b(?P<release>R\d+)\b", re.IGNORECASE)
PALLET_PATTERN = re.compile(r"\b(?P<pallet>P\d+)\b", re.IGNORECASE)
MARK_PATTERN = re.compile(r"\b(?P<mark>\d{4,6})\b")


def path_status(path: Path) -> dict[str, object]:
    exists = path.exists()
    return {
        "path": str(path),
        "present": exists,
        "is_mount": path.is_mount() if exists else False,
        "message": "Mounted and ready" if exists else "Missing mount",
    }


def _extract_metadata(blob: str) -> dict[str, str | None]:
    job = JOB_PATTERN.search(blob)
    release = RELEASE_PATTERN.search(blob)
    pallet = PALLET_PATTERN.search(blob)
    mark = MARK_PATTERN.search(blob)
    return {
        "job_number": job.group("job") if job else None,
        "release_code": release.group("release").upper() if release else None,
        "pallet_code": pallet.group("pallet").upper() if pallet else None,
        "mark_number": mark.group("mark") if mark else None,
    }


def scan_documents(root: Path, *, source_key: str) -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    if not root.exists():
        return documents
    for path in root.rglob("*"):
        if path.name.startswith("."):
            continue
        if not path.is_file() and not path.is_dir():
            continue
        blob = " ".join([path.name, *path.parts]).lower()
        meta = _extract_metadata(blob)
        display_name = path.name.replace("_", " ").replace("-", " ").strip() or path.name
        documents.append(
            {
                "source_key": source_key,
                "source_path": str(path),
                "doc_type": "folder" if path.is_dir() else (path.suffix.lower().lstrip(".") or "file"),
                "display_name": display_name,
                "search_text": blob,
                **meta,
            }
        )
    return documents
