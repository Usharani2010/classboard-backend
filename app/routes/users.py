from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo import ReturnDocument

from app.auth.password import hash_password
from app.database import get_database
from app.schemas.schemas import UserCreate, UserResponse, UserUpdate
from app.utils.class_utils import ensure_class_for_combination
from app.utils.dependencies import ensure_single_cr_per_class, get_system_admin

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = {"system_admin", "college_admin", "student", "cr"}


async def serialize_user(user: dict, db) -> UserResponse:
    class_doc = None
    if user.get("class_id"):
        class_doc = await db.classes.find_one({"_id": ObjectId(user["class_id"])})
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


async def validate_user_payload(db, payload: dict, current_user_id: Optional[str] = None):
    role = payload.get("role")
    if role and role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")

    email = payload.get("email")
    if email:
        email_query = {"email": email}
        if current_user_id:
            email_query["_id"] = {"$ne": ObjectId(current_user_id)}
        if await db.users.find_one(email_query):
            raise HTTPException(status_code=400, detail="Email already exists")

    student_id = payload.get("student_id")
    if student_id:
        student_query = {"student_id": student_id}
        if current_user_id:
            student_query["_id"] = {"$ne": ObjectId(current_user_id)}
        if await db.users.find_one(student_query):
            raise HTTPException(status_code=400, detail="Student ID already exists")

    if role == "cr":
        if not all(payload.get(field) is not None for field in ["college_id", "degree_id", "branch_id", "year"]):
            raise HTTPException(
                status_code=400,
                detail="CR must belong to a class",
            )
        class_id = payload.get("class_id")
        if not class_id:
            class_doc = await ensure_class_for_combination(
                db,
                payload["college_id"],
                payload["degree_id"],
                payload["branch_id"],
                payload["year"],
            )
            payload["class_id"] = str(class_doc["_id"])
        await ensure_single_cr_per_class(payload["college_id"], payload["class_id"], db, exclude_user_id=current_user_id)


@router.get("/admin/list", response_model=dict)
async def get_users_with_filtering(
    college_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_system_admin),
):
    db = get_database()
    filter_query = {}

    if college_id:
        filter_query["college_id"] = college_id
    if role:
        filter_query["role"] = role
    if search:
        filter_query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"student_id": {"$regex": search, "$options": "i"}},
        ]

    colleges = await db.colleges.find().to_list(None)
    users = await db.users.find(filter_query).sort("created_at", -1).to_list(None)

    colleges_data = [
        {"id": str(college["_id"]), "name": college["name"], "code": college["code"]}
        for college in colleges
    ]
    college_map = {str(college["_id"]): college["name"] for college in colleges}

    grouped_by_college = {}
    for user in users:
        college_name = college_map.get(user.get("college_id"), "No College")
        grouped_by_college.setdefault(college_name, []).append((await serialize_user(user, db)).model_dump())

    return {
        "colleges": colleges_data,
        "users_by_college": grouped_by_college,
        "total_users": len(users),
    }


@router.get("", response_model=list[UserResponse])
async def get_all_users(current_user: dict = Depends(get_system_admin)):
    db = get_database()
    users = await db.users.find().sort("created_at", -1).to_list(None)
    return [await serialize_user(user, db) for user in users]


@router.get("/admins", response_model=list[UserResponse])
async def get_all_admins(current_user: dict = Depends(get_system_admin)):
    db = get_database()
    admins = await db.users.find({"role": {"$in": ["system_admin", "college_admin"]}}).to_list(None)
    return [await serialize_user(admin, db) for admin in admins]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, current_user: dict = Depends(get_system_admin)):
    db = get_database()
    user_dict = data.model_dump()
    if user_dict.get("college_id") and user_dict.get("degree_id") and user_dict.get("branch_id") and user_dict.get("year"):
        class_doc = await ensure_class_for_combination(
            db,
            user_dict["college_id"],
            user_dict["degree_id"],
            user_dict["branch_id"],
            user_dict["year"],
        )
        user_dict["class_id"] = str(class_doc["_id"])
    await validate_user_payload(db, user_dict)

    password = user_dict.pop("password")
    user_dict["password_hash"] = hash_password(password)
    user_dict["created_at"] = datetime.now(timezone.utc)

    result = await db.users.insert_one(user_dict)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    return await serialize_user(created_user, db)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_user: dict = Depends(get_system_admin),
):
    db = get_database()
    update_data = {key: value for key, value in data.model_dump().items() if value is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    base_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not base_user:
        raise HTTPException(status_code=404, detail="User not found")

    if (
        update_data.get("college_id", base_user.get("college_id"))
        and update_data.get("degree_id", base_user.get("degree_id"))
        and update_data.get("branch_id", base_user.get("branch_id"))
        and update_data.get("year", base_user.get("year"))
    ):
        class_doc = await ensure_class_for_combination(
            db,
            update_data.get("college_id", base_user.get("college_id")),
            update_data.get("degree_id", base_user.get("degree_id")),
            update_data.get("branch_id", base_user.get("branch_id")),
            update_data.get("year", base_user.get("year")),
        )
        update_data["class_id"] = str(class_doc["_id"])

    merged_payload = {**base_user, **update_data}
    await validate_user_payload(db, merged_payload, current_user_id=user_id)

    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    try:
        result = await db.users.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return await serialize_user(result, db)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, current_user: dict = Depends(get_system_admin)):
    db = get_database()
    try:
        result = await db.users.delete_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/{user_id}/assign-cr", response_model=UserResponse)
async def assign_cr(user_id: str, current_user: dict = Depends(get_system_admin)):
    db = get_database()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") not in {"student", "cr"}:
        raise HTTPException(status_code=400, detail="Only students can be assigned as CR")

    await ensure_single_cr_per_class(user.get("college_id"), user.get("class_id"), db, exclude_user_id=str(user["_id"]))

    updated_user = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": "cr"}},
        return_document=ReturnDocument.AFTER,
    )
    return await serialize_user(updated_user, db)
