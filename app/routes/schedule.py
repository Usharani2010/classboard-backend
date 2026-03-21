from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.schemas.schemas import ScheduleResponse
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/schedule", tags=["schedule"])


async def serialize_schedule(schedule: dict, db) -> ScheduleResponse:
    class_doc = await db.classes.find_one({"_id": ObjectId(schedule["class_id"])}) if schedule.get("class_id") else None
    return ScheduleResponse(
        id=str(schedule["_id"]),
        class_id=schedule["class_id"],
        class_name=class_doc.get("name") if class_doc else None,
        day=schedule["day"],
        subject=schedule["subject"],
        faculty=schedule["faculty"],
        start_time=schedule["start_time"],
        end_time=schedule["end_time"],
    )


@router.get("", response_model=list[ScheduleResponse])
async def get_schedules(current_user: dict = Depends(get_current_user)):
    db = get_database()
    query = {}
    if current_user.get("role") != "system_admin":
        query["college_id"] = current_user.get("college_id")
    if current_user.get("role") in {"student", "cr"}:
        query["class_id"] = current_user.get("class_id")

    schedules = await db.schedules.find(query).sort([("day", 1), ("start_time", 1)]).to_list(None)
    return [await serialize_schedule(schedule, db) for schedule in schedules]
