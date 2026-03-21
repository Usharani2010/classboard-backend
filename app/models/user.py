from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from bson import ObjectId


class User(BaseModel):
    id: Optional[str] = None
    name: str
    student_id: Optional[str] = None
    email: EmailStr
    password_hash: str
    role: str  # "system_admin", "college_admin", "cr", "student"
    college_id: Optional[str] = None
    degree_id: Optional[str] = None
    branch_id: Optional[str] = None
    year: Optional[int] = None
    class_id: Optional[str] = None
    created_at: datetime = None

    class Config:
        from_attributes = True

    def dict(self, **kwargs):
        d = super().dict(**kwargs)
        if self.id:
            d['_id'] = self.id
            d.pop('id', None)
        return d
