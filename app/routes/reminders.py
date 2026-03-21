from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import ReturnDocument

from app.database import get_database
from app.schemas.schemas import ReminderCreate, ReminderResponse
from app.utils.dependencies import get_student_user

router = APIRouter(prefix="/reminders", tags=["reminders"])


def serialize_reminder(reminder: dict) -> ReminderResponse:
    return ReminderResponse(
        id=str(reminder["_id"]),
        title=reminder["title"],
        description=reminder["description"],
        user_id=reminder["user_id"],
        reminder_type=reminder.get("reminder_type", "personal"),
        class_id=reminder.get("class_id"),
        remind_date=reminder["remind_date"],
        status=reminder.get("status", "pending"),
    )


@router.get("", response_model=list[ReminderResponse])
async def get_reminders(current_user: dict = Depends(get_student_user)):
    db = get_database()
    query = {
        "$or": [
            {"user_id": str(current_user["_id"]), "reminder_type": "personal"},
            {
                "college_id": current_user.get("college_id"),
                "class_id": current_user.get("class_id"),
                "reminder_type": "class",
            },
        ]
    }
    reminders = await db.reminders.find(query).sort("remind_date", 1).to_list(None)
    return [serialize_reminder(reminder) for reminder in reminders]


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(data: ReminderCreate, current_user: dict = Depends(get_student_user)):
    db = get_database()
    if data.reminder_type == "class" and current_user.get("role") != "cr":
        raise HTTPException(status_code=403, detail="Only CR can create class reminders")

    reminder_dict = {
        "title": data.title,
        "description": data.description,
        "user_id": str(current_user["_id"]),
        "college_id": current_user.get("college_id"),
        "class_id": current_user.get("class_id"),
        "reminder_type": data.reminder_type,
        "remind_date": data.remind_date,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.reminders.insert_one(reminder_dict)
    return serialize_reminder(await db.reminders.find_one({"_id": result.inserted_id}))


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(reminder_id: str, data: dict, current_user: dict = Depends(get_student_user)):
    db = get_database()
    reminder = await db.reminders.find_one({"_id": ObjectId(reminder_id)})
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if reminder["user_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = await db.reminders.find_one_and_update(
        {"_id": reminder["_id"]},
        {"$set": data},
        return_document=ReturnDocument.AFTER,
    )
    return serialize_reminder(updated)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(reminder_id: str, current_user: dict = Depends(get_student_user)):
    db = get_database()
    reminder = await db.reminders.find_one({"_id": ObjectId(reminder_id)})
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if reminder["user_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.reminders.delete_one({"_id": reminder["_id"]})
