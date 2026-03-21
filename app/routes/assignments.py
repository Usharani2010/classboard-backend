from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_database
from app.schemas.schemas import AssignmentCreate, AssignmentResponse
from app.utils.dependencies import get_cr_only, get_student_user

router = APIRouter(prefix="/assignments", tags=["assignments"])


async def serialize_assignment(assignment: dict, db) -> AssignmentResponse:
    creator = await db.users.find_one({"_id": ObjectId(assignment["created_by"])})
    return AssignmentResponse(
        id=str(assignment["_id"]),
        title=assignment["title"],
        description=assignment["description"],
        due_date=assignment["due_date"],
        attachments=assignment.get("attachments"),
        media_url=assignment.get("media_url"),
        media_type=assignment.get("media_type"),
        created_by=assignment["created_by"],
        created_by_name=creator.get("name") if creator else None,
        class_id=assignment["class_id"],
        created_at=assignment["created_at"],
    )


@router.get("", response_model=list[AssignmentResponse])
async def get_assignments(current_user: dict = Depends(get_student_user)):
    db = get_database()
    if not current_user.get("class_id"):
        return []
    assignments = await db.assignments.find({"class_id": current_user["class_id"]}).sort("due_date", 1).to_list(None)
    return [await serialize_assignment(assignment, db) for assignment in assignments]


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(data: AssignmentCreate, current_user: dict = Depends(get_cr_only)):
    db = get_database()
    if data.class_id != current_user.get("class_id"):
        raise HTTPException(status_code=403, detail="CR can create assignments only for their own class")

    assignment_dict = {
        "title": data.title,
        "description": data.description,
        "due_date": data.due_date,
        "attachments": data.attachments or [],
        "media_url": data.media_url,
        "media_type": data.media_type,
        "created_by": str(current_user["_id"]),
        "class_id": data.class_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.assignments.insert_one(assignment_dict)

    students = await db.users.find(
        {
            "college_id": current_user.get("college_id"),
            "class_id": current_user.get("class_id"),
            "role": "student",
        }
    ).to_list(None)
    if students:
        await db.assignment_tracker.insert_many(
            [
                {
                    "assignment_id": str(result.inserted_id),
                    "student_id": str(student["_id"]),
                    "completed": False,
                    "completed_at": None,
                }
                for student in students
            ]
        )

    created_assignment = await db.assignments.find_one({"_id": result.inserted_id})
    return await serialize_assignment(created_assignment, db)


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(assignment_id: str, current_user: dict = Depends(get_student_user)):
    db = get_database()
    try:
        assignment = await db.assignments.find_one({"_id": ObjectId(assignment_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid assignment ID")
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment["class_id"] != current_user.get("class_id"):
        raise HTTPException(status_code=403, detail="Not authorized to view this assignment")
    return await serialize_assignment(assignment, db)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(assignment_id: str, current_user: dict = Depends(get_cr_only)):
    db = get_database()
    try:
        assignment = await db.assignments.find_one({"_id": ObjectId(assignment_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid assignment ID")
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment["created_by"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Only the creator can delete this assignment")
    await db.assignments.delete_one({"_id": assignment["_id"]})
    await db.assignment_tracker.delete_many({"assignment_id": assignment_id})
