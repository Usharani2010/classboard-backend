from bson import ObjectId
from fastapi import APIRouter, Depends

from app.database import get_database
from app.schemas.schemas import CollegeAdminDashboardStats, StudentDashboardStats, SystemAdminDashboardStats
from app.utils.dependencies import get_college_admin, get_student_user, get_system_admin

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/system-admin", response_model=SystemAdminDashboardStats)
async def get_system_admin_dashboard(current_user: dict = Depends(get_system_admin)):
    db = get_database()
    return SystemAdminDashboardStats(
        total_colleges=await db.colleges.count_documents({}),
        total_users=await db.users.count_documents({}),
        total_admins=await db.users.count_documents({"role": {"$in": ["system_admin", "college_admin"]}}),
    )


@router.get("/college-admin", response_model=CollegeAdminDashboardStats)
async def get_college_admin_dashboard(current_user: dict = Depends(get_college_admin)):
    db = get_database()
    college_id = current_user.get("college_id")
    degrees = await db.degrees.find({"college_id": college_id}).to_list(None)
    degree_ids = [str(degree["_id"]) for degree in degrees]
    branches = await db.branches.find({"degree_id": {"$in": degree_ids}}).to_list(None)
    return CollegeAdminDashboardStats(
        degrees_count=len(degrees),
        branches_count=len(branches),
        students_count=await db.users.count_documents({"college_id": college_id, "role": {"$in": ["student", "cr"]}}),
        classes_count=await db.classes.count_documents({"college_id": college_id}),
        pending_issues=await db.issue_reports.count_documents({"college_id": college_id, "status": {"$in": ["open", "in_progress"]}}),
        pending_profile_requests=await db.profile_corrections.count_documents({"college_id": college_id, "status": "pending"}),
    )


@router.get("/student", response_model=StudentDashboardStats)
async def get_student_dashboard(current_user: dict = Depends(get_student_user)):
    db = get_database()
    announcements_query = {
        "college_id": current_user.get("college_id"),
        "archived": {"$ne": True},
        "$or": [{"target_class_id": None}, {"target_class_id": current_user.get("class_id")}],
    }
    recent_assignments_docs = await db.assignments.find({"class_id": current_user.get("class_id")}).sort("created_at", -1).to_list(5)
    recent_announcements_docs = await db.announcements.find(announcements_query).sort("created_at", -1).to_list(5)
    creator_ids = list({doc["created_by"] for doc in [*recent_assignments_docs, *recent_announcements_docs]})
    creators = {}
    if creator_ids:
        users = await db.users.find({"_id": {"$in": [ObjectId(user_id) for user_id in creator_ids]}}).to_list(None)
        creators = {str(user["_id"]): user["name"] for user in users}

    return StudentDashboardStats(
        assignments_count=await db.assignments.count_documents({"class_id": current_user.get("class_id")}),
        announcements_count=await db.announcements.count_documents(announcements_query),
        schedules_count=await db.schedules.count_documents({"class_id": current_user.get("class_id")}),
        reminders_count=await db.reminders.count_documents(
            {
                "$or": [
                    {"user_id": str(current_user["_id"]), "reminder_type": "personal"},
                    {"class_id": current_user.get("class_id"), "reminder_type": "class"},
                ]
            }
        ),
        open_issues_count=await db.issue_reports.count_documents({"user_id": str(current_user["_id"]), "status": {"$in": ["open", "in_progress"]}}),
        recent_assignments=[
            {
                "id": str(doc["_id"]),
                "title": doc["title"],
                "due_date": doc["due_date"],
                "created_by_name": creators.get(doc["created_by"]),
            }
            for doc in recent_assignments_docs
        ],
        recent_announcements=[
            {
                "id": str(doc["_id"]),
                "title": doc["title"],
                "created_at": doc["created_at"],
                "created_by_name": creators.get(doc["created_by"]),
            }
            for doc in recent_announcements_docs
        ],
    )
