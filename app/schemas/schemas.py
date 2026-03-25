from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    name: str
    student_id: str
    email: EmailStr
    password: str
    college_id: str
    degree_id: str
    branch_id: str
    year: int
    class_id: Optional[str] = None


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    college_id: Optional[str] = None
    degree_id: Optional[str] = None
    branch_id: Optional[str] = None
    year: Optional[int] = None
    class_id: Optional[str] = None
    student_id: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    college_id: Optional[str] = None
    degree_id: Optional[str] = None
    branch_id: Optional[str] = None
    year: Optional[int] = None
    class_id: Optional[str] = None
    student_id: Optional[str] = None


class CollegeAdminRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    college_id: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: Optional[str] = None
    name: str
    student_id: Optional[str] = None
    email: str
    role: str
    college_id: Optional[str] = None
    degree_id: Optional[str] = None
    branch_id: Optional[str] = None
    year: Optional[int] = None
    class_id: Optional[str] = None
    class_code: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class CollegeCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class CollegeResponse(BaseModel):
    id: Optional[str] = None
    name: str
    code: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DegreeCreate(BaseModel):
    name: str
    college_id: str
    code: str


class DegreeResponse(BaseModel):
    id: Optional[str] = None
    name: str
    college_id: str
    code: str

    class Config:
        from_attributes = True


class BranchCreate(BaseModel):
    name: str
    degree_id: str
    code: str


class BranchResponse(BaseModel):
    id: Optional[str] = None
    name: str
    degree_id: str
    code: str

    class Config:
        from_attributes = True


class ClassCreate(BaseModel):
    degree_id: str
    branch_id: str
    year: int


class ClassResponse(BaseModel):
    id: Optional[str] = None
    college_id: str
    degree_id: str
    branch_id: str
    year: int
    code: str
    name: str

    class Config:
        from_attributes = True


class AnnouncementCreate(BaseModel):
    title: str
    description: str
    tags: Optional[list[str]] = None
    attachments: Optional[list[str]] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    target_class_id: Optional[str] = None


class AnnouncementResponse(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    tags: Optional[list[str]] = None
    attachments: Optional[list[str]] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    created_by: str
    created_by_name: Optional[str] = None
    target_class_id: Optional[str] = None
    archived: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AssignmentCreate(BaseModel):
    title: str
    description: str
    due_date: datetime
    attachments: Optional[list[str]] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    class_id: str


class AssignmentResponse(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    due_date: datetime
    attachments: Optional[list[str]] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    created_by: str
    created_by_name: Optional[str] = None
    class_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class AssignmentTrackerCreate(BaseModel):
    student_id: str


class AssignmentTrackerResponse(BaseModel):
    id: Optional[str] = None
    assignment_id: str
    student_id: str
    completed: bool
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScheduleCreate(BaseModel):
    class_id: str
    day: str
    subject: str
    faculty: str
    start_time: str
    end_time: str


class ScheduleResponse(BaseModel):
    id: Optional[str] = None
    class_id: str
    class_name: Optional[str] = None
    day: str
    subject: str
    faculty: str
    start_time: str
    end_time: str

    class Config:
        from_attributes = True


class MediaUploadResponse(BaseModel):
    url: str
    media_type: str
    public_id: Optional[str] = None


class SystemAdminDashboardStats(BaseModel):
    total_colleges: int
    total_users: int
    total_admins: int


class CollegeAdminDashboardStats(BaseModel):
    degrees_count: int
    branches_count: int
    students_count: int
    classes_count: int
    pending_issues: int
    pending_profile_requests: int


class StudentDashboardStats(BaseModel):
    assignments_count: int
    announcements_count: int
    schedules_count: int
    reminders_count: int
    open_issues_count: int
    recent_assignments: Optional[list[dict]] = None
    recent_announcements: Optional[list[dict]] = None


class ProfileCorrectionCreate(BaseModel):
    field_name: str
    current_value: Optional[str] = None
    requested_value: str
    reason: Optional[str] = None


class ProfileCorrectionResponse(BaseModel):
    id: Optional[str] = None
    user_id: str
    field_name: str
    current_value: Optional[str] = None
    requested_value: str
    reason: Optional[str] = None
    status: str = "pending"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IssueReportCreate(BaseModel):
    issue_type: str
    title: str
    description: str
    attachments: Optional[list[str]] = None


class IssueReportResponse(BaseModel):
    id: Optional[str] = None
    user_id: str
    user_name: Optional[str] = None
    college_id: str
    issue_type: str
    title: str
    description: str
    attachments: Optional[list[str]] = None
    status: str = "open"
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StudentCSVRecord(BaseModel):
    name: str
    student_id: str
    email: EmailStr
    degree_id: str
    branch_id: str
    year: int
    role: str = "student"
    password: Optional[str] = None


class ReminderCreate(BaseModel):
    title: str
    description: str
    remind_date: datetime
    reminder_type: str = "personal"
    class_id: Optional[str] = None


class ReminderResponse(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    user_id: str
    reminder_type: str
    class_id: Optional[str] = None
    remind_date: datetime
    status: str = "pending"

    class Config:
        from_attributes = True


class CollegeOnboard(BaseModel):
    college_name: str
    college_code: str
    college_description: Optional[str] = None
    admin_name: str
    admin_email: EmailStr


class CollegeOnboardResponse(BaseModel):
    college_id: str
    college_name: str
    admin_id: str
    admin_email: str
    message: str


class BranchDetailResponse(BaseModel):
    id: Optional[str] = None
    name: str
    degree_id: str
    code: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DegreeDetailResponse(BaseModel):
    id: Optional[str] = None
    name: str
    college_id: str
    code: str
    branches: Optional[list[dict]] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollegeDetailResponse(BaseModel):
    id: Optional[str] = None
    name: str
    code: str
    description: Optional[str] = None
    degrees: Optional[list[DegreeDetailResponse]] = None
    admin_name: Optional[str] = None
    admin_email: Optional[str] = None
    student_count: Optional[int] = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_colleges: int
    total_users: int
    total_students: int
    total_college_admins: int
    total_crs: int
    colleges: Optional[list] = None
