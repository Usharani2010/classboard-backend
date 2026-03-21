from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database
from app.schemas.schemas import (
    UserRegister, UserLogin, TokenResponse, UserResponse, CollegeAdminRegister
)
from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import create_access_token
from app.utils.dependencies import get_current_user
from app.utils.class_utils import ensure_class_for_combination

router = APIRouter(prefix="/auth", tags=["auth"])


async def build_user_response(user: dict, db) -> UserResponse:
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


@router.post("/register/student", response_model=TokenResponse)
async def register_student(user_data: UserRegister):
    """Register a new student"""
    db = get_database()
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Check if student_id already exists
    existing_student = await db.users.find_one({"student_id": user_data.student_id})
    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID already registered",
        )
    
    # Verify college, degree, branch exist
    college = await db.colleges.find_one({"_id": ObjectId(user_data.college_id)})
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")
    
    degree = await db.degrees.find_one({"_id": ObjectId(user_data.degree_id)})
    if not degree:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Degree not found")
    
    branch = await db.branches.find_one({"_id": ObjectId(user_data.branch_id)})
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    
    # Create new student
    user_dict = {
        "name": user_data.name,
        "student_id": user_data.student_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "role": "student",
        "college_id": user_data.college_id,
        "degree_id": user_data.degree_id,
        "branch_id": user_data.branch_id,
        "year": user_data.year,
        "class_id": user_data.class_id,
        "created_at": datetime.now(timezone.utc),
    }

    if not user_dict["class_id"]:
        class_doc = await ensure_class_for_combination(
            db,
            user_data.college_id,
            user_data.degree_id,
            user_data.branch_id,
            user_data.year,
        )
        user_dict["class_id"] = str(class_doc["_id"])
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    # Create token
    token = create_access_token(data={"sub": str(result.inserted_id)})
    
    user_response = await build_user_response(user_dict, db)
    
    return TokenResponse(access_token=token, user=user_response)


@router.post("/register/college-admin", response_model=TokenResponse)
async def register_college_admin(admin_data: CollegeAdminRegister):
    """Register a new college admin (System admin only)"""
    db = get_database()
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": admin_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Verify college exists
    college = await db.colleges.find_one({"_id": ObjectId(admin_data.college_id)})
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")
    
    # Create new college admin
    user_dict = {
        "name": admin_data.name,
        "student_id": None,
        "email": admin_data.email,
        "password_hash": hash_password(admin_data.password),
        "role": "college_admin",
        "college_id": admin_data.college_id,
        "degree_id": None,
        "branch_id": None,
        "year": None,
        "class_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    # Create token
    token = create_access_token(data={"sub": str(result.inserted_id)})
    
    user_response = await build_user_response(user_dict, db)
    
    return TokenResponse(access_token=token, user=user_response)


@router.post("/login/student", response_model=TokenResponse)
async def login_student(credentials: UserLogin):
    """Student or CR login through the student portal"""
    db = get_database()
    
    user = await db.users.find_one({
        "email": credentials.email,
        "role": {"$in": ["student", "cr"]},
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    if not verify_password(credentials.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    token = create_access_token(data={"sub": str(user["_id"])})
    
    user_response = await build_user_response(user, db)
    
    return TokenResponse(access_token=token, user=user_response)


@router.post("/login/college-admin", response_model=TokenResponse)
async def login_college_admin(credentials: UserLogin):
    """College admin login"""
    db = get_database()
    
    user = await db.users.find_one({
        "email": credentials.email,
        "role": "college_admin"
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    if not verify_password(credentials.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    token = create_access_token(data={"sub": str(user["_id"])})
    
    user_response = await build_user_response(user, db)
    
    return TokenResponse(access_token=token, user=user_response)


@router.post("/login/system-admin", response_model=TokenResponse)
async def login_system_admin(credentials: UserLogin):
    """System admin login"""
    db = get_database()
    
    user = await db.users.find_one({
        "email": credentials.email,
        "role": "system_admin"
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    if not verify_password(credentials.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    token = create_access_token(data={"sub": str(user["_id"])})
    
    user_response = await build_user_response(user, db)
    
    return TokenResponse(access_token=token, user=user_response)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    db = get_database()
    return await build_user_response(current_user, db)


