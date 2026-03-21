from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ReturnDocument
from app.database import get_database
from app.schemas.schemas import AssignmentTrackerResponse
from app.utils.dependencies import get_cr_only, get_current_user

router = APIRouter(prefix="/assignments", tags=["tracker"])


@router.get("/{assignment_id}/tracker", response_model=list[AssignmentTrackerResponse])
async def get_tracker(
    assignment_id: str, 
    current_user: dict = Depends(get_cr_only)
):
    """Get assignment submission tracker - CR ONLY"""
    db = get_database()
    
    try:
        assignment = await db.assignments.find_one({"_id": ObjectId(assignment_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment ID",
        )
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    
    # Check if user (CR) created this assignment
    if assignment["created_by"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the CR who created this assignment can view tracker",
        )
    
    # Get all students in the CR's class with their submission status
    trackers = await db.assignment_tracker.find({
        "assignment_id": assignment_id
    }).to_list(None)
    
    return [
        AssignmentTrackerResponse(
            id=str(t["_id"]),
            assignment_id=t["assignment_id"],
            student_id=t["student_id"],
            completed=t["completed"],
            completed_at=t.get("completed_at"),
        )
        for t in trackers
    ]


@router.get("/{assignment_id}/tracker/students", response_model=list[dict])
async def get_tracker_with_student_info(
    assignment_id: str,
    current_user: dict = Depends(get_cr_only)
):
    """Get assignment tracker with student info"""
    db = get_database()
    
    try:
        assignment = await db.assignments.find_one({"_id": ObjectId(assignment_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment ID",
        )
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    
    # Check if user (CR) created this assignment
    if assignment["created_by"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the CR who created this assignment can view tracker",
        )
    
    # Get tracker with student information
    trackers = await db.assignment_tracker.find({
        "assignment_id": assignment_id
    }).to_list(None)
    
    result = []
    for tracker in trackers:
        try:
            student = await db.users.find_one({"_id": ObjectId(tracker["student_id"])})
            if student:
                result.append({
                    "tracker_id": str(tracker["_id"]),
                    "student_id": tracker["student_id"],
                    "student_name": student.get("name"),
                    "student_email": student.get("email"),
                    "completed": tracker["completed"],
                    "completed_at": tracker.get("completed_at"),
                })
        except:
            pass
    
    return result


@router.put("/{assignment_id}/tracker/{student_id}", response_model=AssignmentTrackerResponse)
async def mark_assignment_submission(
    assignment_id: str,
    student_id: str,
    completed: bool,
    current_user: dict = Depends(get_cr_only),
):
    """Mark/unmark student assignment submission - CR ONLY"""
    db = get_database()
    
    try:
        assignment = await db.assignments.find_one({"_id": ObjectId(assignment_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment ID",
        )
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    
    # Check if user (CR) created this assignment
    if assignment["created_by"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the CR who created this assignment can update tracker",
        )
    
    try:
        tracker = await db.assignment_tracker.find_one_and_update(
            {
                "assignment_id": assignment_id,
                "student_id": student_id,
            },
            {
                "$set": {
                    "completed": completed,
                    "completed_at": datetime.now(timezone.utc) if completed else None,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating tracker: {str(e)}",
        )
    
    if not tracker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracker entry not found",
        )
    
    return AssignmentTrackerResponse(
        id=str(tracker["_id"]),
        assignment_id=tracker["assignment_id"],
        student_id=tracker["student_id"],
        completed=tracker["completed"],
        completed_at=tracker.get("completed_at"),
    )


@router.post("/{assignment_id}/tracker/bulk-update")
async def bulk_update_submissions(
    assignment_id: str,
    submissions: dict,  # {"student_id": bool, ...}
    current_user: dict = Depends(get_cr_only)
):
    """Bulk update multiple student submissions - CR ONLY"""
    db = get_database()
    
    try:
        assignment = await db.assignments.find_one({"_id": ObjectId(assignment_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment ID",
        )
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    
    # Check if user (CR) created this assignment
    if assignment["created_by"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the CR who created this assignment can update tracker",
        )
    
    updated = 0
    for student_id, completed in submissions.items():
        try:
            result = await db.assignment_tracker.update_one(
                {
                    "assignment_id": assignment_id,
                    "student_id": student_id,
                },
                {
                    "$set": {
                        "completed": completed,
                        "completed_at": datetime.now(timezone.utc) if completed else None,
                    }
                }
            )
            if result.modified_count > 0:
                updated += 1
        except Exception:
            pass
    
    return {
        "updated": updated,
        "total": len(submissions)
    }
