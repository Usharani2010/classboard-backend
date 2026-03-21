"""
Database Population Script
Run this to create sample data for testing
"""

import asyncio
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.auth.password import hash_password
from app.config import settings
from app.utils.class_utils import ensure_class_for_combination


async def populate_db():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client["classboard"]

    try:
        for collection_name in [
            "users",
            "colleges",
            "degrees",
            "branches",
            "classes",
            "announcements",
            "assignments",
            "assignment_tracker",
            "reminders",
            "schedules",
            "profile_corrections",
            "issue_reports",
        ]:
            await db[collection_name].delete_many({})

        print("Cleared existing data...")

        await db.users.insert_one(
            {
                "name": "System Admin",
                "email": "sysadmin@classboard.com",
                "password_hash": hash_password("admin123"),
                "role": "system_admin",
                "student_id": None,
                "college_id": None,
                "degree_id": None,
                "branch_id": None,
                "year": None,
                "class_id": None,
                "created_at": datetime.now(timezone.utc),
            }
        )
        print("Created system admin user")

        college = await db.colleges.insert_one(
            {
                "name": "ABC College of Engineering",
                "code": "ABC",
                "description": "Leading engineering college",
            }
        )
        college_id = str(college.inserted_id)
        print("Created college")

        await db.users.insert_one(
            {
                "name": "College Admin",
                "email": "collegeadmin@classboard.com",
                "password_hash": hash_password("college123"),
                "role": "college_admin",
                "college_id": college_id,
                "degree_id": None,
                "branch_id": None,
                "year": None,
                "class_id": None,
                "created_at": datetime.now(timezone.utc),
            }
        )
        print("Created college admin user")

        degree = await db.degrees.insert_one(
            {
                "name": "Bachelor of Technology",
                "college_id": college_id,
                "code": "B",
            }
        )
        degree_id = str(degree.inserted_id)

        cse_branch = await db.branches.insert_one(
            {
                "name": "Computer Science and Engineering",
                "degree_id": degree_id,
                "code": "C",
            }
        )
        cse_branch_id = str(cse_branch.inserted_id)

        await db.branches.insert_one(
            {
                "name": "Electronics and Communication Engineering",
                "degree_id": degree_id,
                "code": "E",
            }
        )
        print("Created degree and branches")

        class_doc = await ensure_class_for_combination(db, college_id, degree_id, cse_branch_id, 3)
        class_id = str(class_doc["_id"])
        print(f"Created class {class_doc['code']}")

        cr_user = await db.users.insert_one(
            {
                "name": "Rajesh Kumar",
                "email": "cr@classboard.com",
                "password_hash": hash_password("cr123"),
                "student_id": "CSE001",
                "role": "cr",
                "college_id": college_id,
                "degree_id": degree_id,
                "branch_id": cse_branch_id,
                "year": 3,
                "class_id": class_id,
                "created_at": datetime.now(timezone.utc),
            }
        )
        cr_id = str(cr_user.inserted_id)

        student_ids = []
        for index in range(2, 6):
            student = await db.users.insert_one(
                {
                    "name": f"Student {index}",
                    "email": f"student{index}@classboard.com",
                    "password_hash": hash_password("student123"),
                    "student_id": f"CSE{index:03d}",
                    "role": "student",
                    "college_id": college_id,
                    "degree_id": degree_id,
                    "branch_id": cse_branch_id,
                    "year": 3,
                    "class_id": class_id,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            student_ids.append(str(student.inserted_id))
        print("Created CR and students")

        await db.announcements.insert_one(
            {
                "title": "Welcome to ClassBoard",
                "description": "Stay updated with announcements, assignments, and schedules.",
                "tags": ["welcome", "important"],
                "attachments": [],
                "media_url": None,
                "media_type": None,
                "created_by": cr_id,
                "college_id": college_id,
                "target_class_id": None,
                "archived": False,
                "created_at": datetime.now(timezone.utc),
            }
        )

        assignment = await db.assignments.insert_one(
            {
                "title": "Data Structures Assignment",
                "description": "Implement AVL Trees and Red-Black Trees",
                "due_date": datetime.now(timezone.utc) + timedelta(days=7),
                "attachments": [],
                "media_url": None,
                "media_type": None,
                "created_by": cr_id,
                "class_id": class_id,
                "created_at": datetime.now(timezone.utc),
            }
        )
        assignment_id = str(assignment.inserted_id)
        for student_id in student_ids:
            await db.assignment_tracker.insert_one(
                {
                    "assignment_id": assignment_id,
                    "student_id": student_id,
                    "completed": False,
                    "completed_at": None,
                }
            )

        for student_id in student_ids[:2]:
            await db.reminders.insert_one(
                {
                    "title": "Submission Deadline",
                    "description": "Complete Data Structures assignment",
                    "user_id": student_id,
                    "college_id": college_id,
                    "class_id": class_id,
                    "reminder_type": "personal",
                    "remind_date": datetime.now(timezone.utc) + timedelta(days=1),
                    "status": "pending",
                }
            )

        for schedule in [
            {"day": "Monday", "subject": "Data Structures", "faculty": "Dr. Smith", "start_time": "09:00", "end_time": "10:30"},
            {"day": "Tuesday", "subject": "Algorithms", "faculty": "Prof. Brown", "start_time": "09:00", "end_time": "10:30"},
            {"day": "Wednesday", "subject": "Web Development", "faculty": "Dr. Wilson", "start_time": "14:00", "end_time": "15:30"},
        ]:
            await db.schedules.insert_one(
                {
                    "class_id": class_id,
                    "college_id": college_id,
                    **schedule,
                }
            )

        print("Database populated successfully")
        print("System Admin: sysadmin@classboard.com / admin123")
        print("College Admin: collegeadmin@classboard.com / college123")
        print("CR: cr@classboard.com / cr123")
        print("Students: student2@classboard.com to student5@classboard.com / student123")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(populate_db())
