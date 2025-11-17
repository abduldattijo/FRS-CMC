"""
Pydantic schemas for Person-related operations
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class PersonBase(BaseModel):
    """Base schema for Person"""

    name: str = Field(..., min_length=1, max_length=255, description="Full name of the person")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    employee_id: Optional[str] = Field(None, max_length=50, description="Employee ID")
    notes: Optional[str] = Field(None, description="Additional notes")


class PersonCreate(PersonBase):
    """Schema for creating a new person"""

    pass


class PersonUpdate(BaseModel):
    """Schema for updating a person"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class PersonResponse(PersonBase):
    """Schema for person response"""

    id: int
    employee_id: Optional[str]
    image_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PersonListResponse(BaseModel):
    """Schema for list of persons"""

    total: int
    persons: list[PersonResponse]
