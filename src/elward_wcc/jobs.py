from __future__ import annotations

from pathlib import Path

from . import db, filesystem
from .config import MOUNT_PATHS


def refresh_job_index() -> dict[str, int]:
    jobs_scanned = 0
    documents_scanned = 0
    for mount_key, mount_path in MOUNT_PATHS.items():
        status = filesystem.path_status(mount_path)
        db.set_mount_status(
            mount_key,
            str(mount_path),
            present=bool(status["present"]),
            is_mount=bool(status["is_mount"]),
            message=str(status["message"]),
        )
        if not mount_path.exists():
            continue
        documents = filesystem.scan_documents(mount_path, source_key=mount_key)
        documents_scanned += len(documents)
        for document in documents:
            search_bits = [
                str(document.get("job_number") or ""),
                str(document.get("release_code") or ""),
                str(document.get("pallet_code") or ""),
                str(document.get("mark_number") or ""),
                str(document.get("display_name") or ""),
                str(document.get("source_path") or ""),
            ]
            search_text = " ".join(bit for bit in search_bits if bit).lower()
            job_id = db.upsert_job(
                {
                    "job_number": document.get("job_number"),
                    "release_code": document.get("release_code"),
                    "pallet_code": document.get("pallet_code"),
                    "mark_number": document.get("mark_number"),
                    "display_name": str(document.get("display_name") or Path(str(document["source_path"])).name),
                    "search_text": search_text,
                    "source_type": str(document.get("doc_type") or "filesystem"),
                    "source_path": document.get("source_path"),
                    "source_url": None,
                }
            )
            db.upsert_job_document(
                {
                    "job_id": job_id,
                    "doc_type": str(document.get("doc_type") or "file"),
                    "label": str(document.get("display_name") or ""),
                    "path_or_url": str(document.get("source_path") or ""),
                    "source_path": str(document.get("source_path") or ""),
                    "search_text": search_text,
                    "sort_order": 0,
                }
            )
            jobs_scanned += 1
    return {"jobs_scanned": jobs_scanned, "documents_scanned": documents_scanned}


def search_jobs(query: str, *, limit: int = 25) -> list[dict[str, object]]:
    results = db.search_jobs(query, limit=limit)
    for row in results:
        row["documents"] = db.job_documents_for(int(row["id"]))
    if query.strip():
        db.log_search(query, len(results))
    return results


def recent_jobs(limit: int = 12) -> list[dict[str, object]]:
    results = db.recent_jobs(limit=limit)
    for row in results:
        row["documents"] = db.job_documents_for(int(row["id"]))
    return results
