from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    # Create indexes
    await create_indexes()

    print("Connected to MongoDB")


async def close_mongo():
    global client
    if client:
        client.close()
        print("Closed MongoDB connection")


async def create_indexes():
    """Create necessary indexes for collections"""

    # Users collection
    await db.users.create_index("email", unique=True)
    await db.users.create_index("student_id", unique=True, sparse=True)
    await db.users.create_index([("college_id", 1), ("role", 1)])
    await db.users.create_index([("college_id", 1), ("class_id", 1)])
    await db.users.create_index([("class_id", 1), ("role", 1)])

    # Classes collection
    await db.classes.create_index([("college_id", 1), ("degree_id", 1), ("branch_id", 1), ("year", 1)], unique=True)
    await db.classes.create_index([("college_id", 1), ("code", 1)], unique=True)

    # Announcements collection
    await db.announcements.create_index("created_at")
    await db.announcements.create_index("tags")
    await db.announcements.create_index("college_id")
    await db.announcements.create_index([("college_id", 1), ("target_class_id", 1)])

    # Assignments collection
    await db.assignments.create_index("class_id")
    await db.assignments.create_index("created_at")
    await db.assignments.create_index([("class_id", 1), ("due_date", 1)])

    # Schedules collection
    await db.schedules.create_index("class_id")
    await db.schedules.create_index("college_id")
    await db.schedules.create_index([("college_id", 1), ("class_id", 1)])

    # Assignment tracker
    await db.assignment_tracker.create_index([("assignment_id", 1), ("student_id", 1)], unique=True)

    # Profile corrections
    await db.profile_corrections.create_index("user_id")
    await db.profile_corrections.create_index([("college_id", 1), ("status", 1)])
    await db.profile_corrections.create_index("created_at")

    # Issue reports
    await db.issue_reports.create_index("user_id")
    await db.issue_reports.create_index([("college_id", 1), ("status", 1)])
    await db.issue_reports.create_index("created_at")
    await db.issue_reports.create_index("issue_type")

    # Reminders
    await db.reminders.create_index([("user_id", 1), ("reminder_type", 1)])
    await db.reminders.create_index("remind_date")
    await db.reminders.create_index([("user_id", 1), ("status", 1)])


def get_database() -> AsyncIOMotorDatabase:
    return db
