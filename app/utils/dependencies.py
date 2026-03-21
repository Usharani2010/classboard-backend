from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.jwt_handler import decode_token
from app.database import get_database
from bson import ObjectId

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    db = get_database()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


def require_roles(*roles: str):
    allowed_roles = set(roles)

    async def role_dependency(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to: {', '.join(sorted(allowed_roles))}",
            )
        return current_user

    return role_dependency


def ensure_same_college(current_user: dict, resource: dict, field_name: str = "college_id"):
    user_college_id = current_user.get("college_id")
    resource_college_id = resource.get(field_name)
    if current_user.get("role") == "system_admin":
        return
    if user_college_id != resource_college_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resource does not belong to your college",
        )


async def ensure_single_cr_per_class(
    college_id: str,
    class_id: str,
    db,
    exclude_user_id: str | None = None,
):
    query = {
        "college_id": college_id,
        "class_id": class_id,
        "role": "cr",
    }
    if exclude_user_id:
        query["_id"] = {"$ne": ObjectId(exclude_user_id)}

    existing_cr = await db.users.find_one(query)
    if existing_cr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one CR is allowed for a class",
        )


# System Admin - Global access
async def get_system_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System admin access required",
        )
    return current_user


# College Admin - Manage specific college
async def get_college_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "college_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="College admin access required",
        )
    return current_user


# Admin - Either system admin or college admin
async def get_admin_user(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in ["system_admin", "college_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# CR or Admin
async def get_cr_user(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in ["cr", "system_admin", "college_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CR or Admin access required",
        )
    return current_user


# Student or higher
async def get_student_user(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in ["student", "cr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )
    return current_user


# CR (only CR, not admin)
async def get_cr_only(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "cr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Class Representative access required",
        )
    return current_user


# Student (only student, not CR or admin)
async def get_student_only(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )
    return current_user
