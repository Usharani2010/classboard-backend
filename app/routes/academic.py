"""
Academic Management Routes
Handles colleges, degrees, branches, classes
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database
from app.schemas.schemas import (
    CollegeCreate,
    CollegeResponse,
    CollegeOnboard,
    CollegeOnboardResponse,
    CollegeDetailResponse,
    DegreeDetailResponse,
    BranchDetailResponse,
    DegreeCreate,
    DegreeResponse,
    BranchCreate,
    BranchResponse,
    DashboardStats,
)
from app.auth.password import hash_password
from app.services.email_service import EmailService
from app.utils.dependencies import ensure_same_college, get_admin_user, get_system_admin
import secrets
from pymongo import ReturnDocument

router = APIRouter(prefix="/academic", tags=["academic"])


# COLLEGES
@router.get("/colleges", response_model=list[CollegeResponse])
async def get_colleges(current_user: dict = Depends(get_admin_user)):
    db = get_database()
    query = {}
    if current_user.get("role") == "college_admin":
        query["_id"] = ObjectId(current_user["college_id"])
    colleges = await db.colleges.find(query).to_list(100)
    return [
        CollegeResponse(
            id=str(c["_id"]),
            name=c["name"],
            code=c["code"],
            description=c.get("description"),
        )
        for c in colleges
    ]


@router.get("/public/catalog")
async def get_public_catalog():
    db = get_database()
    colleges = await db.colleges.find().to_list(None)
    degrees = await db.degrees.find().to_list(None)
    branches = await db.branches.find().to_list(None)
    classes = await db.classes.find().to_list(None)

    return {
        "colleges": [
            {
                "id": str(college["_id"]),
                "name": college["name"],
                "code": college["code"],
            }
            for college in colleges
        ],
        "degrees": [
            {
                "id": str(degree["_id"]),
                "name": degree["name"],
                "college_id": degree["college_id"],
                "code": degree["code"],
            }
            for degree in degrees
        ],
        "branches": [
            {
                "id": str(branch["_id"]),
                "name": branch["name"],
                "degree_id": branch["degree_id"],
                "code": branch["code"],
            }
            for branch in branches
        ],
        "classes": [
            {
                "id": str(class_doc["_id"]),
                "name": class_doc["name"],
                "branch_id": class_doc["branch_id"],
                "year": class_doc["year"],
                "code": class_doc["code"],
            }
            for class_doc in classes
        ],
    }


@router.post("/colleges", response_model=CollegeResponse)
async def create_college(data: CollegeCreate, current_user: dict = Depends(get_system_admin)):
    db = get_database()
    
    college_dict = {
        "name": data.name,
        "code": data.code,
        "description": data.description,
        "created_at": datetime.now(timezone.utc),
    }
    
    result = await db.colleges.insert_one(college_dict)
    
    return CollegeResponse(
        id=str(result.inserted_id),
        name=college_dict["name"],
        code=college_dict["code"],
        description=college_dict["description"],
    )


@router.put("/colleges/{college_id}", response_model=CollegeResponse)
async def update_college(
    college_id: str,
    data: CollegeCreate,
    current_user: dict = Depends(get_system_admin),
):
    db = get_database()
    try:
        college = await db.colleges.find_one_and_update(
            {"_id": ObjectId(college_id)},
            {"$set": data.model_dump()},
            return_document=ReturnDocument.AFTER,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid college ID")

    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    return CollegeResponse(
        id=str(college["_id"]),
        name=college["name"],
        code=college["code"],
        description=college.get("description"),
    )


@router.delete("/colleges/{college_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_college(college_id: str, current_user: dict = Depends(get_system_admin)):
    db = get_database()
    try:
        result = await db.colleges.delete_one({"_id": ObjectId(college_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid college ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="College not found")


# DEGREES
@router.get("/degrees", response_model=list[DegreeResponse])
async def get_degrees(current_user: dict = Depends(get_admin_user)):
    db = get_database()
    query = {}
    if current_user.get("role") == "college_admin":
        query["college_id"] = current_user.get("college_id")
    degrees = await db.degrees.find(query).to_list(100)
    return [
        DegreeResponse(
            id=str(d["_id"]),
            name=d["name"],
            college_id=d["college_id"],
            code=d["code"],
        )
        for d in degrees
    ]


@router.post("/degrees", response_model=DegreeResponse)
async def create_degree(data: DegreeCreate, current_user: dict = Depends(get_admin_user)):
    db = get_database()
    
    # Verify college exists
    college = await db.colleges.find_one({"_id": ObjectId(data.college_id)})
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found",
        )
    
    ensure_same_college(current_user, {"college_id": data.college_id})

    degree_dict = {
        "name": data.name,
        "college_id": data.college_id,
        "code": data.code,
        "created_at": datetime.now(timezone.utc),
    }
    
    result = await db.degrees.insert_one(degree_dict)
    
    return DegreeResponse(
        id=str(result.inserted_id),
        name=degree_dict["name"],
        college_id=degree_dict["college_id"],
        code=degree_dict["code"],
    )


# BRANCHES
@router.get("/branches", response_model=list[BranchResponse])
async def get_branches(current_user: dict = Depends(get_admin_user)):
    db = get_database()
    if current_user.get("role") == "college_admin":
        degrees = await db.degrees.find({"college_id": current_user.get("college_id")}).to_list(None)
        degree_ids = [str(degree["_id"]) for degree in degrees]
        branches = await db.branches.find({"degree_id": {"$in": degree_ids}}).to_list(100)
    else:
        branches = await db.branches.find().to_list(100)
    return [
        BranchResponse(
            id=str(b["_id"]),
            name=b["name"],
            degree_id=b["degree_id"],
            code=b["code"],
        )
        for b in branches
    ]


@router.post("/branches", response_model=BranchResponse)
async def create_branch(data: BranchCreate, current_user: dict = Depends(get_admin_user)):
    db = get_database()
    
    # Verify degree exists
    degree = await db.degrees.find_one({"_id": ObjectId(data.degree_id)})
    if not degree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Degree not found",
        )

    ensure_same_college(current_user, {"college_id": degree["college_id"]})
    
    branch_dict = {
        "name": data.name,
        "degree_id": data.degree_id,
        "code": data.code,
        "created_at": datetime.now(timezone.utc),
    }
    
    result = await db.branches.insert_one(branch_dict)
    
    return BranchResponse(
        id=str(result.inserted_id),
        name=branch_dict["name"],
        degree_id=branch_dict["degree_id"],
        code=branch_dict["code"],
    )


# COLLEGE ONBOARDING (System Admin only)
@router.post("/colleges/onboard", response_model=CollegeOnboardResponse)
async def onboard_college(data: CollegeOnboard, current_user: dict = Depends(get_system_admin)):
    """
    Onboard a new college with college admin
    Creates college, creates college admin user, and sends credentials via email
    """
    db = get_database()
    
    # Check if college code already exists
    existing_college = await db.colleges.find_one({"code": data.college_code})
    if existing_college:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="College code already exists",
        )
    
    # Check if admin email already exists
    existing_admin = await db.users.find_one({"email": data.admin_email})
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Generate temporary password
    temp_password = secrets.token_urlsafe(12)
    
    # Create college
    college_dict = {
        "name": data.college_name,
        "code": data.college_code,
        "description": data.college_description,
        "created_at": datetime.now(timezone.utc),
    }
    college_result = await db.colleges.insert_one(college_dict)
    college_id = str(college_result.inserted_id)
    
    # Create college admin user
    admin_dict = {
        "name": data.admin_name,
        "student_id": None,
        "email": data.admin_email,
        "password_hash": hash_password(temp_password),
        "role": "college_admin",
        "college_id": college_id,
        "degree_id": None,
        "branch_id": None,
        "year": None,
        "class_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    admin_result = await db.users.insert_one(admin_dict)
    admin_id = str(admin_result.inserted_id)
    
    # Send credentials via email
    await EmailService.send_college_admin_credentials(
        email=data.admin_email,
        admin_name=data.admin_name,
        college_name=data.college_name,
        password=temp_password,
    )
    
    return CollegeOnboardResponse(
        college_id=college_id,
        college_name=data.college_name,
        admin_id=admin_id,
        admin_email=data.admin_email,
        message=f"College '{data.college_name}' onboarded successfully. Credentials sent to {data.admin_email}",
    )


# GET COLLEGE WITH DETAILED STRUCTURE (degrees and branches)
@router.get("/colleges/{college_id}/detailed", response_model=CollegeDetailResponse)
async def get_college_detailed(college_id: str, current_user: dict = Depends(get_admin_user)):
    """Get college with all degrees, branches, and student count"""
    db = get_database()
    
    try:
        college = await db.colleges.find_one({"_id": ObjectId(college_id)})
        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College not found",
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid college ID",
        )

    ensure_same_college(current_user, {"college_id": college_id})
    
    # Get all degrees for this college
    degrees = await db.degrees.find({"college_id": college_id}).to_list(None)
    
    # Build detailed degrees structure with branches
    degrees_detailed = []
    for degree in degrees:
        degree_id = str(degree["_id"])
        branches = await db.branches.find({"degree_id": degree_id}).to_list(None)
        
        branches_detailed = [
            BranchDetailResponse(
                id=str(b["_id"]),
                name=b["name"],
                degree_id=b["degree_id"],
                code=b["code"],
                created_at=b.get("created_at"),
            )
            for b in branches
        ]
        
        degrees_detailed.append(
            DegreeDetailResponse(
                id=degree_id,
                name=degree["name"],
                college_id=degree["college_id"],
                code=degree["code"],
                branches=branches_detailed,
                created_at=degree.get("created_at"),
            )
        )
    
    # Get college admin details
    admin = await db.users.find_one({
        "college_id": college_id,
        "role": "college_admin"
    })
    admin_name = admin.get("name") if admin else None
    admin_email = admin.get("email") if admin else None
    
    # Get student count for this college
    student_count = await db.users.count_documents({
        "college_id": college_id,
        "role": "student"
    })
    
    return CollegeDetailResponse(
        id=college_id,
        name=college["name"],
        code=college["code"],
        description=college.get("description"),
        degrees=degrees_detailed,
        admin_name=admin_name,
        admin_email=admin_email,
        student_count=student_count,
        created_at=college.get("created_at"),
    )


# DASHBOARD STATISTICS
@router.get("/admin/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_system_admin)):
    """Get dashboard statistics for system admin"""
    db = get_database()
    
    # Get counts
    total_colleges = await db.colleges.count_documents({})
    total_students = await db.users.count_documents({"role": "student"})
    total_college_admins = await db.users.count_documents({"role": "college_admin"})
    total_crs = await db.users.count_documents({"role": "cr"})
    total_users = total_students + total_college_admins + total_crs
    
    # Get colleges with their stats
    colleges = await db.colleges.find().to_list(None)
    colleges_data = []
    
    for college in colleges:
        college_id = str(college["_id"])
        degree_count = await db.degrees.count_documents({"college_id": college_id})
        student_count = await db.users.count_documents({
            "college_id": college_id,
            "role": "student"
        })
        
        colleges_data.append({
            "id": college_id,
            "name": college["name"],
            "code": college["code"],
            "degrees": degree_count,
            "students": student_count,
        })
    
    return DashboardStats(
        total_colleges=total_colleges,
        total_users=total_users,
        total_students=total_students,
        total_college_admins=total_college_admins,
        total_crs=total_crs,
        colleges=colleges_data,
    )
