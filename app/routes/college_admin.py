from datetime import datetime, timezone
import csv
import io

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pymongo import ReturnDocument

from app.auth.password import hash_password
from app.database import get_database
from app.schemas.schemas import (
    ClassResponse,
    ScheduleCreate,
    ScheduleResponse,
    StudentCSVRecord,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.utils.class_utils import ensure_class_for_combination
from app.utils.dependencies import ensure_single_cr_per_class, get_college_admin

router = APIRouter(prefix="/college-admin", tags=["college-admin"])

REQUIRED_CSV_COLUMNS = ["name", "student_id", "email", "degree_id", "branch_id", "year"]


async def serialize_user(user: dict, db) -> UserResponse:
    class_doc = await db.classes.find_one({"_id": ObjectId(user["class_id"])}) if user.get("class_id") else None
    return UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        student_id=user.get("student_id"),
        email=user["email"],
        role=user["role"],
        college_id=user.get("college_id"),
        degree_id=user.get("degree_id"),
        branch_id=user.get("branch_id"),
        year=user.get("year"),
        class_id=user.get("class_id"),
        class_code=class_doc.get("code") if class_doc else None,
        created_at=user.get("created_at"),
    )


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


async def ensure_owned_student(student_id: str, college_id: str, db):
    try:
        student = await db.users.find_one({"_id": ObjectId(student_id), "college_id": college_id})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid student ID")
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/classes", response_model=list[ClassResponse])
async def get_college_classes(current_user: dict = Depends(get_college_admin)):
    db = get_database()
    classes = await db.classes.find({"college_id": current_user.get("college_id")}).sort([("year", 1), ("code", 1)]).to_list(None)
    return [
        ClassResponse(
            id=str(class_doc["_id"]),
            college_id=class_doc["college_id"],
            degree_id=class_doc["degree_id"],
            branch_id=class_doc["branch_id"],
            year=class_doc["year"],
            code=class_doc["code"],
            name=class_doc["name"],
        )
        for class_doc in classes
    ]


@router.get("/students", response_model=list[dict])
async def get_college_students(current_user: dict = Depends(get_college_admin)):
    db = get_database()
    users = await db.users.find(
        {"college_id": current_user.get("college_id"), "role": {"$in": ["student", "cr"]}}
    ).sort([("year", 1), ("student_id", 1)]).to_list(None)

    grouped = {}
    for user in users:
        class_doc = await db.classes.find_one({"_id": ObjectId(user["class_id"])}) if user.get("class_id") else None
        class_key = class_doc.get("code") if class_doc else "Unassigned"
        grouped.setdefault(
            class_key,
            {
                "class_id": str(class_doc["_id"]) if class_doc else None,
                "class_code": class_key,
                "class_name": class_doc.get("name") if class_doc else "Unassigned",
                "students": [],
            },
        )
        grouped[class_key]["students"].append((await serialize_user(user, db)).model_dump())

    return list(grouped.values())


@router.post("/students", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_student(data: UserCreate, current_user: dict = Depends(get_college_admin)):
    db = get_database()
    payload = data.model_dump()
    payload["role"] = payload.get("role") or "student"
    payload["college_id"] = current_user.get("college_id")

    if payload["role"] not in {"student", "cr"}:
        raise HTTPException(status_code=400, detail="College admins can create only students or CRs")

    if await db.users.find_one({"email": payload["email"]}):
        raise HTTPException(status_code=400, detail="Email already exists")
    if payload.get("student_id") and await db.users.find_one({"student_id": payload["student_id"]}):
        raise HTTPException(status_code=400, detail="Student ID already exists")

    class_doc = await ensure_class_for_combination(
        db,
        payload["college_id"],
        payload["degree_id"],
        payload["branch_id"],
        payload["year"],
    )
    payload["class_id"] = str(class_doc["_id"])

    if payload["role"] == "cr":
        await ensure_single_cr_per_class(payload["college_id"], payload["class_id"], db)

    password = payload.pop("password")
    payload["password_hash"] = hash_password(password)
    payload["created_at"] = datetime.now(timezone.utc)

    result = await db.users.insert_one(payload)
    created_student = await db.users.find_one({"_id": result.inserted_id})
    return await serialize_user(created_student, db)


@router.put("/students/{student_id}", response_model=UserResponse)
async def update_student(student_id: str, data: UserUpdate, current_user: dict = Depends(get_college_admin)):
    db = get_database()
    student = await ensure_owned_student(student_id, current_user.get("college_id"), db)
    update_data = {key: value for key, value in data.model_dump().items() if value is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    if (
        update_data.get("degree_id", student.get("degree_id"))
        and update_data.get("branch_id", student.get("branch_id"))
        and update_data.get("year", student.get("year"))
    ):
        class_doc = await ensure_class_for_combination(
            db,
            current_user.get("college_id"),
            update_data.get("degree_id", student.get("degree_id")),
            update_data.get("branch_id", student.get("branch_id")),
            update_data.get("year", student.get("year")),
        )
        update_data["class_id"] = str(class_doc["_id"])

    if update_data.get("role", student.get("role")) == "cr":
        await ensure_single_cr_per_class(
            current_user.get("college_id"),
            update_data.get("class_id", student.get("class_id")),
            db,
            exclude_user_id=student_id,
        )

    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    updated_student = await db.users.find_one_and_update(
        {"_id": student["_id"]},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )
    return await serialize_user(updated_student, db)


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(student_id: str, current_user: dict = Depends(get_college_admin)):
    db = get_database()
    student = await ensure_owned_student(student_id, current_user.get("college_id"), db)
    await db.users.delete_one({"_id": student["_id"]})


@router.post("/students/{student_id}/assign-cr", response_model=UserResponse)
async def assign_cr_to_student(student_id: str, current_user: dict = Depends(get_college_admin)):
    db = get_database()
    student = await ensure_owned_student(student_id, current_user.get("college_id"), db)
    await ensure_single_cr_per_class(current_user.get("college_id"), student.get("class_id"), db, exclude_user_id=student_id)
    updated_student = await db.users.find_one_and_update(
        {"_id": student["_id"]},
        {"$set": {"role": "cr"}},
        return_document=ReturnDocument.AFTER,
    )
    return await serialize_user(updated_student, db)


@router.post("/students/import-csv")
async def import_students_csv(file: UploadFile = File(...), current_user: dict = Depends(get_college_admin)):
    db = get_database()
    try:
        contents = (await file.read()).decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to read CSV file")

    if not csv_reader.fieldnames or any(column not in csv_reader.fieldnames for column in REQUIRED_CSV_COLUMNS):
        raise HTTPException(
            status_code=400,
            detail=f"CSV format is invalid. Required columns: {', '.join(REQUIRED_CSV_COLUMNS)}",
        )

    imported = 0
    errors = []
    total_rows = 0

    for total_rows, row in enumerate(csv_reader, start=2):
        try:
            record = StudentCSVRecord(
                name=row["name"],
                student_id=row["student_id"],
                email=row["email"],
                degree_id=row["degree_id"],
                branch_id=row["branch_id"],
                year=int(row["year"]),
            )
            if await db.users.find_one({"$or": [{"email": record.email}, {"student_id": record.student_id}]}):
                errors.append(f"Row {total_rows}: duplicate student email or ID")
                continue

            class_doc = await ensure_class_for_combination(
                db,
                current_user.get("college_id"),
                record.degree_id,
                record.branch_id,
                record.year,
            )

            await db.users.insert_one(
                {
                    "name": record.name,
                    "student_id": record.student_id,
                    "email": record.email,
                    "password_hash": hash_password("TempPassword123"),
                    "role": "student",
                    "college_id": current_user.get("college_id"),
                    "degree_id": record.degree_id,
                    "branch_id": record.branch_id,
                    "year": record.year,
                    "class_id": str(class_doc["_id"]),
                    "created_at": datetime.now(timezone.utc),
                }
            )
            imported += 1
        except Exception as exc:
            errors.append(f"Row {total_rows}: {exc}")

    return {"imported": imported, "total_rows": max(total_rows - 1, 0), "errors": errors}


@router.get("/students/export-csv")
async def export_students_csv(current_user: dict = Depends(get_college_admin)):
    db = get_database()
    students = await db.users.find(
        {"college_id": current_user.get("college_id"), "role": {"$in": ["student", "cr"]}}
    ).sort("student_id", 1).to_list(None)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["name", "student_id", "email", "degree_id", "branch_id", "year", "class_id", "role"],
    )
    writer.writeheader()
    for student in students:
        writer.writerow(
            {
                "name": student["name"],
                "student_id": student.get("student_id", ""),
                "email": student["email"],
                "degree_id": student.get("degree_id", ""),
                "branch_id": student.get("branch_id", ""),
                "year": student.get("year", ""),
                "class_id": student.get("class_id", ""),
                "role": student.get("role", "student"),
            }
        )
    return {"content": output.getvalue(), "filename": "students.csv"}


@router.get("/structure")
async def get_structure(current_user: dict = Depends(get_college_admin)):
    db = get_database()
    college_id = current_user.get("college_id")
    degrees = await db.degrees.find({"college_id": college_id}).to_list(None)
    classes = await db.classes.find({"college_id": college_id}).sort([("year", 1), ("code", 1)]).to_list(None)

    classes_by_degree = {}
    for class_doc in classes:
        key = class_doc["degree_id"]
        classes_by_degree.setdefault(key, {}).setdefault(class_doc["branch_id"], []).append(
            {
                "id": str(class_doc["_id"]),
                "code": class_doc["code"],
                "name": class_doc["name"],
                "year": class_doc["year"],
            }
        )

    branches = await db.branches.find({"degree_id": {"$in": [str(degree["_id"]) for degree in degrees]}}).to_list(None)
    branches_map = {}
    for branch in branches:
        branches_map.setdefault(branch["degree_id"], []).append(
            {
                "id": str(branch["_id"]),
                "name": branch["name"],
                "code": branch["code"],
                "classes": classes_by_degree.get(branch["degree_id"], {}).get(str(branch["_id"]), []),
            }
        )

    return [
        {
            "id": str(degree["_id"]),
            "name": degree["name"],
            "code": degree["code"],
            "branches": branches_map.get(str(degree["_id"]), []),
        }
        for degree in degrees
    ]


@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(data: ScheduleCreate, current_user: dict = Depends(get_college_admin)):
    db = get_database()
    try:
        class_doc = await db.classes.find_one({"_id": ObjectId(data.class_id), "college_id": current_user.get("college_id")})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid class ID")
    if not class_doc:
        raise HTTPException(status_code=404, detail="Class not found")

    schedule_dict = {
        "college_id": current_user.get("college_id"),
        "class_id": data.class_id,
        "day": data.day,
        "subject": data.subject,
        "faculty": data.faculty,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.schedules.insert_one(schedule_dict)
    created_schedule = await db.schedules.find_one({"_id": result.inserted_id})
    return await serialize_schedule(created_schedule, db)


@router.get("/schedules", response_model=list[ScheduleResponse])
async def get_college_schedules(current_user: dict = Depends(get_college_admin)):
    db = get_database()
    schedules = await db.schedules.find({"college_id": current_user.get("college_id")}).sort([("day", 1), ("start_time", 1)]).to_list(None)
    return [await serialize_schedule(schedule, db) for schedule in schedules]


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: str, data: ScheduleCreate, current_user: dict = Depends(get_college_admin)):
    db = get_database()
    try:
        schedule = await db.schedules.find_one_and_update(
            {"_id": ObjectId(schedule_id), "college_id": current_user.get("college_id")},
            {"$set": data.model_dump()},
            return_document=ReturnDocument.AFTER,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid schedule ID")
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return await serialize_schedule(schedule, db)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: str, current_user: dict = Depends(get_college_admin)):
    db = get_database()
    try:
        result = await db.schedules.delete_one({"_id": ObjectId(schedule_id), "college_id": current_user.get("college_id")})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid schedule ID")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
