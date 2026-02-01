"""Progress API - CRUD operations for learning progress."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from studykb_mcp.services.progress_service import ProgressService
from studykb_mcp.models.progress import ProgressStatus, RelatedSection

router = APIRouter()


class RelatedSectionInput(BaseModel):
    """Input for a related section."""
    material: str
    start_line: int
    end_line: int
    desc: str = ""


class ProgressUpdate(BaseModel):
    """Request body for updating progress."""
    status: ProgressStatus
    name: Optional[str] = None
    comment: Optional[str] = None
    related_sections: Optional[list[RelatedSectionInput]] = None


class ProgressCreate(BaseModel):
    """Request body for creating progress entry."""
    progress_id: str
    name: str
    status: ProgressStatus = "pending"
    comment: str = ""
    related_sections: Optional[list[RelatedSectionInput]] = None


@router.get("/{category}")
async def get_progress(
    category: str,
    status_filter: Optional[str] = None,
    show_time: bool = False,
):
    """Get all progress entries for a category."""
    service = ProgressService()

    # Parse status filter
    status_list = None
    if status_filter:
        status_list = [s.strip() for s in status_filter.split(",")]

    progress = await service.get_progress(
        category=category,
        status_filter=status_list,
        since="all",
        limit=-1,
    )

    # Convert to JSON-friendly format
    entries = []
    for entry_id, entry in progress.entries.items():
        entry_dict = {
            "id": entry_id,
            "name": entry.name,
            "status": entry.status,
            "comment": entry.comment,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            "mastered_at": entry.mastered_at.isoformat() if entry.mastered_at else None,
            "review_count": entry.review_count,
            "next_review_at": entry.next_review_at.isoformat() if entry.next_review_at else None,
            "related_sections": [
                {
                    "material": s.material,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "desc": s.desc,
                }
                for s in entry.related_sections
            ],
        }
        entries.append(entry_dict)

    # Sort by status priority then by updated_at
    status_order = {"active": 0, "review": 1, "pending": 2, "done": 3}
    entries.sort(key=lambda x: (status_order.get(x["status"], 99), x["updated_at"] or ""), reverse=True)

    return {
        "category": category,
        "stats": progress.get_stats(),
        "entries": entries,
    }


@router.get("/{category}/{progress_id}")
async def get_progress_entry(category: str, progress_id: str):
    """Get a single progress entry with full details."""
    service = ProgressService()
    progress_file = await service.get_full_progress(category)

    if progress_id not in progress_file.entries:
        raise HTTPException(status_code=404, detail=f"Progress entry '{progress_id}' not found")

    entry = progress_file.entries[progress_id]

    return {
        "id": progress_id,
        "name": entry.name,
        "status": entry.status,
        "comment": entry.comment,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        "mastered_at": entry.mastered_at.isoformat() if entry.mastered_at else None,
        "review_count": entry.review_count,
        "next_review_at": entry.next_review_at.isoformat() if entry.next_review_at else None,
        "related_sections": [
            {
                "material": s.material,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "desc": s.desc,
            }
            for s in entry.related_sections
        ],
    }


@router.put("/{category}/{progress_id}")
async def update_progress_entry(category: str, progress_id: str, body: ProgressUpdate):
    """Update a progress entry."""
    service = ProgressService()

    # Check if entry exists
    progress_file = await service.get_full_progress(category)
    if progress_id not in progress_file.entries:
        raise HTTPException(status_code=404, detail=f"Progress entry '{progress_id}' not found")

    # Convert related sections
    sections = None
    if body.related_sections is not None:
        sections = [
            RelatedSection(
                material=s.material,
                start_line=s.start_line,
                end_line=s.end_line,
                desc=s.desc,
            )
            for s in body.related_sections
        ]

    entry, is_new, old_status = await service.update_progress(
        category=category,
        progress_id=progress_id,
        status=body.status,
        name=body.name,
        comment=body.comment or "",
        related_sections=sections,
    )

    return {
        "success": True,
        "id": progress_id,
        "name": entry.name,
        "status": entry.status,
        "old_status": old_status,
        "comment": entry.comment,
    }


@router.post("/{category}")
async def create_progress_entry(category: str, body: ProgressCreate):
    """Create a new progress entry."""
    service = ProgressService()

    # Check if entry already exists
    progress_file = await service.get_full_progress(category)
    if body.progress_id in progress_file.entries:
        raise HTTPException(status_code=400, detail=f"Progress entry '{body.progress_id}' already exists")

    # Convert related sections
    sections = None
    if body.related_sections is not None:
        sections = [
            RelatedSection(
                material=s.material,
                start_line=s.start_line,
                end_line=s.end_line,
                desc=s.desc,
            )
            for s in body.related_sections
        ]

    entry, is_new, _ = await service.update_progress(
        category=category,
        progress_id=body.progress_id,
        status=body.status,
        name=body.name,
        comment=body.comment,
        related_sections=sections,
    )

    return {
        "success": True,
        "id": body.progress_id,
        "name": entry.name,
        "status": entry.status,
        "is_new": is_new,
    }


@router.delete("/{category}/{progress_id}")
async def delete_progress_entry(category: str, progress_id: str):
    """Delete a progress entry."""
    service = ProgressService()

    success = await service.delete_progress(category, progress_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Progress entry '{progress_id}' not found")

    return {"success": True, "message": f"Progress entry '{progress_id}' deleted"}
