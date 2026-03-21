from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_database
from app.schemas.schemas import AnnouncementCreate, AnnouncementResponse
from app.utils.dependencies import require_roles

router = APIRouter(prefix="/announcements", tags=["announcements"])


async def serialize_announcement(announcement: dict, db) -> AnnouncementResponse:
    creator = await db.users.find_one({"_id": ObjectId(announcement["created_by"])})
    return AnnouncementResponse(
        id=str(announcement["_id"]),
        title=announcement["title"],
        description=announcement["description"],
        tags=announcement.get("tags"),
        attachments=announcement.get("attachments"),
        media_url=announcement.get("media_url"),
        media_type=announcement.get("media_type"),
        created_by=announcement["created_by"],
        created_by_name=creator.get("name") if creator else None,
        target_class_id=announcement.get("target_class_id"),
        archived=announcement.get("archived", False),
        created_at=announcement["created_at"],
    )


@router.get("", response_model=list[AnnouncementResponse])
async def get_announcements(
    current_user: dict = Depends(require_roles("student", "cr", "college_admin")),
    include_archived: bool = Query(False),
):
    db = get_database()
    query = {"college_id": current_user.get("college_id")}
    if not include_archived:
        query["archived"] = {"$ne": True}

    if current_user.get("role") in {"student", "cr"}:
        query["$or"] = [
            {"target_class_id": None},
            {"target_class_id": current_user.get("class_id")},
        ]

    announcements = await db.announcements.find(query).sort("created_at", -1).to_list(None)
    return [await serialize_announcement(announcement, db) for announcement in announcements]


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    data: AnnouncementCreate,
    current_user: dict = Depends(require_roles("student", "cr", "college_admin")),
):
    db = get_database()
    target_class_id = data.target_class_id
    if current_user.get("role") == "student":
        target_class_id = current_user.get("class_id")
    if current_user.get("role") == "cr":
        target_class_id = current_user.get("class_id")

    announcement_dict = {
        "title": data.title,
        "description": data.description,
        "tags": data.tags or [],
        "attachments": data.attachments or [],
        "media_url": data.media_url,
        "media_type": data.media_type,
        "created_by": str(current_user["_id"]),
        "college_id": current_user.get("college_id"),
        "target_class_id": target_class_id,
        "archived": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.announcements.insert_one(announcement_dict)
    created_announcement = await db.announcements.find_one({"_id": result.inserted_id})
    return await serialize_announcement(created_announcement, db)


@router.post("/{announcement_id}/archive")
async def archive_announcement(
    announcement_id: str,
    current_user: dict = Depends(require_roles("student", "cr", "college_admin")),
):
    db = get_database()
    try:
        announcement = await db.announcements.find_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if announcement["created_by"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Only the creator can archive this announcement")

    await db.announcements.update_one({"_id": announcement["_id"]}, {"$set": {"archived": True}})
    return {"status": "archived"}
