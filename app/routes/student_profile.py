"""
Student Profile and Correction Routes
Handles profile viewing, correction requests, and issue reporting
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database
from app.schemas.schemas import (
    UserResponse, ProfileCorrectionCreate, ProfileCorrectionResponse,
    IssueReportCreate, IssueReportResponse
)
from app.utils.dependencies import get_current_user, get_student_user, get_college_admin

router = APIRouter(tags=["student-profile"])


# Profile Routes
@router.get("/profile", response_model=UserResponse)
async def get_student_profile(current_user: dict = Depends(get_student_user)):
    """Get current student profile"""
    return UserResponse(
        id=str(current_user["_id"]),
        name=current_user["name"],
        student_id=current_user.get("student_id"),
        email=current_user["email"],
        role=current_user["role"],
        college_id=current_user.get("college_id"),
        degree_id=current_user.get("degree_id"),
        branch_id=current_user.get("branch_id"),
        year=current_user.get("year"),
        class_id=current_user.get("class_id"),
        created_at=current_user.get("created_at"),
    )


@router.post("/profile-corrections", response_model=ProfileCorrectionResponse)
async def request_profile_correction(
    correction: ProfileCorrectionCreate,
    current_user: dict = Depends(get_student_user)
):
    """Request a profile correction"""
    db = get_database()
    
    # Validate field name
    valid_fields = {
        "name", "email", "student_id", "college_id", 
        "degree_id", "branch_id", "year", "class_id"
    }
    
    if correction.field_name not in valid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid field name. Must be one of: {valid_fields}"
        )
    
    correction_dict = {
        "user_id": str(current_user["_id"]),
        "college_id": current_user.get("college_id"),
        "field_name": correction.field_name,
        "current_value": str(correction.current_value) if correction.current_value else None,
        "requested_value": str(correction.requested_value),
        "reason": correction.reason,
        "status": "pending",
        "reviewed_by": None,
        "reviewed_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    
    result = await db.profile_corrections.insert_one(correction_dict)
    
    return ProfileCorrectionResponse(
        id=str(result.inserted_id),
        user_id=correction_dict["user_id"],
        field_name=correction_dict["field_name"],
        current_value=correction_dict["current_value"],
        requested_value=correction_dict["requested_value"],
        reason=correction_dict["reason"],
        status=correction_dict["status"],
        reviewed_by=correction_dict["reviewed_by"],
        reviewed_at=correction_dict["reviewed_at"],
        created_at=correction_dict["created_at"],
    )


@router.get("/profile-corrections", response_model=list[ProfileCorrectionResponse])
async def get_profile_corrections(
    current_user: dict = Depends(get_student_user)
):
    """Get profile corrections for current user"""
    db = get_database()
    
    corrections = await db.profile_corrections.find({
        "user_id": str(current_user["_id"])
    }).sort("created_at", -1).to_list(None)
    
    return [
        ProfileCorrectionResponse(
            id=str(c["_id"]),
            user_id=c["user_id"],
            field_name=c["field_name"],
            current_value=c.get("current_value"),
            requested_value=c["requested_value"],
            reason=c.get("reason"),
            status=c["status"],
            reviewed_by=c.get("reviewed_by"),
            reviewed_at=c.get("reviewed_at"),
            created_at=c["created_at"],
        )
        for c in corrections
    ]


@router.get("/college-admin/profile-corrections", response_model=list[ProfileCorrectionResponse])
async def get_pending_corrections(
    current_user: dict = Depends(get_college_admin),
    status_filter: str = "pending"
):
    """Get pending profile corrections for college admin"""
    db = get_database()
    college_id = current_user.get("college_id")
    
    corrections = await db.profile_corrections.find({
        "college_id": college_id,
        "status": status_filter
    }).sort("created_at", -1).to_list(None)
    
    return [
        ProfileCorrectionResponse(
            id=str(c["_id"]),
            user_id=c["user_id"],
            field_name=c["field_name"],
            current_value=c.get("current_value"),
            requested_value=c["requested_value"],
            reason=c.get("reason"),
            status=c["status"],
            reviewed_by=c.get("reviewed_by"),
            reviewed_at=c.get("reviewed_at"),
            created_at=c["created_at"],
        )
        for c in corrections
    ]


@router.post("/college-admin/profile-corrections/{correction_id}/approve")
async def approve_correction(
    correction_id: str,
    current_user: dict = Depends(get_college_admin)
):
    """Approve a profile correction - updates user profile"""
    db = get_database()
    
    try:
        correction = await db.profile_corrections.find_one({
            "_id": ObjectId(correction_id),
            "college_id": current_user.get("college_id")
        })
    except:
        correction = None
    
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction request not found",
        )
    
    if correction["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Correction already {correction['status']}",
        )
    
    # Update user field
    try:
        await db.users.update_one(
            {"_id": ObjectId(correction["user_id"])},
            {"$set": {correction["field_name"]: correction["requested_value"]}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating user: {str(e)}"
        )
    
    # Update correction status
    await db.profile_corrections.update_one(
        {"_id": ObjectId(correction_id)},
        {
            "$set": {
                "status": "approved",
                "reviewed_by": str(current_user["_id"]),
                "reviewed_at": datetime.now(timezone.utc),
            }
        }
    )
    
    return {"status": "approved"}


@router.post("/college-admin/profile-corrections/{correction_id}/reject")
async def reject_correction(
    correction_id: str,
    current_user: dict = Depends(get_college_admin)
):
    """Reject a profile correction"""
    db = get_database()
    
    try:
        correction = await db.profile_corrections.find_one({
            "_id": ObjectId(correction_id),
            "college_id": current_user.get("college_id")
        })
    except:
        correction = None
    
    if not correction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correction request not found",
        )
    
    if correction["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Correction already {correction['status']}",
        )
    
    # Update correction status
    await db.profile_corrections.update_one(
        {"_id": ObjectId(correction_id)},
        {
            "$set": {
                "status": "rejected",
                "reviewed_by": str(current_user["_id"]),
                "reviewed_at": datetime.now(timezone.utc),
            }
        }
    )
    
    return {"status": "rejected"}


# Issue Reporting Routes
@router.post("/issues", response_model=IssueReportResponse)
async def report_issue(
    issue: IssueReportCreate,
    current_user: dict = Depends(get_student_user)
):
    """Report an issue to college admin"""
    db = get_database()
    
    valid_types = {"profile_data", "schedule", "assignment", "system_bug", "other"}
    if issue.issue_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid issue type. Must be one of: {valid_types}"
        )
    
    issue_dict = {
        "user_id": str(current_user["_id"]),
        "college_id": current_user.get("college_id"),
        "issue_type": issue.issue_type,
        "title": issue.title,
        "description": issue.description,
        "attachments": issue.attachments or [],
        "status": "open",
        "assigned_to": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
        "resolved_at": None,
    }
    
    result = await db.issue_reports.insert_one(issue_dict)
    
    return IssueReportResponse(
        id=str(result.inserted_id),
        user_id=issue_dict["user_id"],
        user_name=current_user.get("name"),
        college_id=issue_dict["college_id"],
        issue_type=issue_dict["issue_type"],
        title=issue_dict["title"],
        description=issue_dict["description"],
        attachments=issue_dict["attachments"],
        status=issue_dict["status"],
        assigned_to=issue_dict["assigned_to"],
        created_at=issue_dict["created_at"],
        updated_at=issue_dict["updated_at"],
        resolved_at=issue_dict["resolved_at"],
    )


@router.get("/issues", response_model=list[IssueReportResponse])
async def get_student_issues(
    current_user: dict = Depends(get_student_user)
):
    """Get issues reported by student"""
    db = get_database()
    
    issues = await db.issue_reports.find({
        "user_id": str(current_user["_id"])
    }).sort("created_at", -1).to_list(None)
    
    return [
        IssueReportResponse(
            id=str(i["_id"]),
            user_id=i["user_id"],
            user_name=current_user.get("name"),
            college_id=i["college_id"],
            issue_type=i["issue_type"],
            title=i["title"],
            description=i["description"],
            attachments=i.get("attachments"),
            status=i["status"],
            assigned_to=i.get("assigned_to"),
            created_at=i["created_at"],
            updated_at=i.get("updated_at"),
            resolved_at=i.get("resolved_at"),
        )
        for i in issues
    ]


@router.get("/college-admin/issues", response_model=list[IssueReportResponse])
async def get_college_issues(
    current_user: dict = Depends(get_college_admin),
    status_filter: str = None
):
    """Get all issues for college"""
    db = get_database()
    college_id = current_user.get("college_id")
    
    query = {"college_id": college_id}
    if status_filter:
        query["status"] = status_filter
    
    issues = await db.issue_reports.find(query).sort("created_at", -1).to_list(None)
    user_ids = [ObjectId(i["user_id"]) for i in issues]
    users = await db.users.find({"_id": {"$in": user_ids}}).to_list(None) if user_ids else []
    user_names = {str(user["_id"]): user["name"] for user in users}
    
    return [
        IssueReportResponse(
            id=str(i["_id"]),
            user_id=i["user_id"],
            user_name=user_names.get(i["user_id"]),
            college_id=i["college_id"],
            issue_type=i["issue_type"],
            title=i["title"],
            description=i["description"],
            attachments=i.get("attachments"),
            status=i["status"],
            assigned_to=i.get("assigned_to"),
            created_at=i["created_at"],
            updated_at=i.get("updated_at"),
            resolved_at=i.get("resolved_at"),
        )
        for i in issues
    ]


@router.post("/college-admin/issues/{issue_id}/update-status")
async def update_issue_status(
    issue_id: str,
    new_status: str,
    current_user: dict = Depends(get_college_admin)
):
    """Update issue status (open, in_progress, resolved, closed)"""
    db = get_database()
    
    valid_statuses = {"open", "in_progress", "resolved", "closed"}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    try:
        result = await db.issue_reports.update_one(
            {
                "_id": ObjectId(issue_id),
                "college_id": current_user.get("college_id")
            },
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc),
                    "resolved_at": datetime.now(timezone.utc) if new_status == "resolved" else None,
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )
        
        return {"status": new_status}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
