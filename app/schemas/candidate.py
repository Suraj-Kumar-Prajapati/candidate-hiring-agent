from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class CandidateBase(BaseModel):
    """Base candidate schema"""
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    experience_years: int = Field(0, ge=0, le=50)
    technologies: List[str] = Field(default_factory=list)
    interview_availability: str = ""
    time_availability: str = ""


class CandidateCreate(CandidateBase):
    """Schema for creating a candidate"""
    job_id: UUID
    resume_text: Optional[str] = ""
    workflow_id: Optional[UUID] = None


class CandidateUpdate(BaseModel):
    """Schema for updating a candidate"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    experience_years: Optional[int] = Field(None, ge=0, le=50)
    technologies: Optional[List[str]] = None
    interview_availability: Optional[str] = None
    time_availability: Optional[str] = None
    current_stage: Optional[str] = None


class CandidateResponse(CandidateBase):
    """Schema for candidate response"""
    id: UUID
    current_stage: str
    overall_score: float = 0.0
    technical_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    skills_score: float = 0.0
    ats_score: float = 0.0
    match_percentage: int = 0
    job_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    resume_file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class CandidateEvaluationBase(BaseModel):
    """Base evaluation schema"""
    evaluation_type: str
    score: float = Field(..., ge=0, le=10)
    feedback: str = ""
    key_points: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class CandidateEvaluationCreate(CandidateEvaluationBase):
    """Schema for creating evaluation"""
    candidate_id: UUID
    model_used: str = "gpt-4o"


class CandidateEvaluationResponse(CandidateEvaluationBase):
    """Schema for evaluation response"""
    id: UUID
    candidate_id: UUID
    model_used: str
    evaluation_timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateStatusResponse(BaseModel):
    """Comprehensive candidate status response"""
    candidate_info: CandidateResponse
    evaluations: List[CandidateEvaluationResponse]
    interviews: List[Dict[str, Any]] = Field(default_factory=list)
    emails_sent: List[Dict[str, Any]] = Field(default_factory=list)
    workflow_progress: Dict[str, Any] = Field(default_factory=dict)
    next_steps: List[str] = Field(default_factory=list)
