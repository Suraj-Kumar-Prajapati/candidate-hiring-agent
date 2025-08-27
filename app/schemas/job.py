from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class JobBase(BaseModel):
    """Base job schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    department: Optional[str] = Field(None, max_length=100)
    location: str = Field("Remote", max_length=255)
    employment_type: str = Field("Full-time", max_length=50)
    experience_required: str = ""
    technologies_required: List[str] = Field(default_factory=list)
    education_requirements: Optional[str] = None
    skills_required: List[str] = Field(default_factory=list)


class JobCreate(JobBase):
    """Schema for creating a job"""
    salary_range_min: Optional[int] = Field(None, ge=0)
    salary_range_max: Optional[int] = Field(None, ge=0)
    currency: str = "USD"
    remote_allowed: bool = False
    positions_available: int = Field(1, ge=1)
    job_description_file: Optional[str] = None


class JobUpdate(BaseModel):
    """Schema for updating a job"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    employment_type: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = None
    positions_available: Optional[int] = Field(None, ge=1)


class JobResponse(JobBase):
    """Schema for job response"""
    id: UUID
    salary_range_min: Optional[int] = None
    salary_range_max: Optional[int] = None
    currency: str = "USD"
    remote_allowed: bool = False
    status: str = "active"
    positions_available: int = 1
    job_description_file: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class JobInterviewerBase(BaseModel):
    """Base job interviewer schema"""
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., max_length=255)
    role: str = Field(..., max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    technologies: List[str] = Field(default_factory=list)
    interview_types: List[str] = Field(default_factory=list)
    seniority_level: str = "mid"
    availability_slots: List[str] = Field(default_factory=list)
    timezone: str = "UTC"
    max_interviews_per_day: int = Field(3, ge=1, le=10)


class JobInterviewerCreate(JobInterviewerBase):
    """Schema for creating job interviewer"""
    job_id: UUID


class JobInterviewerResponse(JobInterviewerBase):
    """Schema for job interviewer response"""
    id: UUID
    job_id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
