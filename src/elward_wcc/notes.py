from __future__ import annotations

from datetime import date

from .db import create_note


def blank_release_checklist(job_ref: str = "", release_ref: str = "") -> tuple[str, str]:
    title = f"Release Checklist {job_ref or release_ref}".strip()
    body = "\n".join(
        [
            "# Release Checklist",
            "",
            f"- Job: {job_ref or 'TBD'}",
            f"- Release: {release_ref or 'TBD'}",
            "",
            "- [ ] Drawings verified",
            "- [ ] Release docs reviewed",
            "- [ ] CNC package confirmed",
            "- [ ] Pallet tracker updated",
            "- [ ] Material availability checked",
            "- [ ] Ready for production handoff",
        ]
    )
    create_note(note_type="release_checklist", title=title, body=body, job_ref=job_ref or None)
    return title, body


def material_shortage_note(
    *,
    job_ref: str = "",
    release_ref: str = "",
    material: str = "",
    quantity_needed: str = "",
    shortage: str = "",
    needed_by_date: str = "",
    notes_text: str = "",
    requested_by: str = "",
) -> tuple[str, str]:
    title = f"Material Shortage Note {job_ref}".strip()
    body = "\n".join(
        [
            "# Material Shortage Note",
            "",
            f"- Date: {date.today().isoformat()}",
            f"- Job: {job_ref or 'TBD'}",
            f"- Release: {release_ref or 'TBD'}",
            f"- Material: {material or 'TBD'}",
            f"- Quantity needed: {quantity_needed or 'TBD'}",
            f"- Issue / Blocker: {shortage or 'TBD'}",
            f"- Needed by: {needed_by_date or 'TBD'}",
            f"- Requested by: {requested_by or 'TBD'}",
            "",
            "## Notes",
            notes_text or "-",
        ]
    )
    create_note(note_type="material_shortage", title=title, body=body, job_ref=job_ref or None, protected=False)
    return title, body


def daily_production_summary(
    *,
    summary_date: date | None = None,
    releases_worked: str = "",
    panels_completed: str = "",
    pallets_completed: str = "",
    cnc_status: str = "",
    assembly_status: str = "",
    shipping_status: str = "",
    blockers: str = "",
    next_steps: str = "",
    notes_text: str = "",
) -> tuple[str, str]:
    actual_date = summary_date or date.today()
    title = f"Daily Production Summary {actual_date.isoformat()}"
    body = "\n".join(
        [
            "# Daily Production Summary",
            "",
            f"- Date: {actual_date.isoformat()}",
            f"- Releases worked: {releases_worked or 'TBD'}",
            f"- Panels completed: {panels_completed or 'TBD'}",
            f"- Pallets completed: {pallets_completed or 'TBD'}",
            f"- CNC status: {cnc_status or 'TBD'}",
            f"- Assembly status: {assembly_status or 'TBD'}",
            f"- Shipping status: {shipping_status or 'TBD'}",
            "",
            "## Completed",
            notes_text or "-",
            "",
            "## Blockers",
            blockers or "-",
            "",
            "## Next Steps",
            next_steps or "-",
        ]
    )
    create_note(note_type="daily_summary", title=title, body=body, protected=False)
    return title, body
