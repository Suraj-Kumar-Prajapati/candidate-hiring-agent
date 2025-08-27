from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID


class InterviewBase(BaseModel):
    """Base interview schema"""
    interview_type: str = Field(..., max_length=50)
    round_number: int = Field(1, ge=1)
    duration_minutes: int = Field(60, ge=15, le=480)
    meeting_link: Optional[str] = Field(None, max_length=500)
    meeting_id: Optional[str] = Field(None, max_length=100)
    meeting_password: Optional[str] = Field(None, max_length=100)


class InterviewCreate(InterviewBase):
    """Schema for creating interview"""
    candidate_id: UUID
    interviewer_id: UUID
    job_id: UUID
    scheduled_time: datetime


class InterviewUpdate(BaseModel):
    """Schema for updating interview"""
    scheduled_time: Optional[datetime] = None
    status: Optional[str] = None
    meeting_link: Optional[str] = None
    meeting_id: Optional[str] = None
    meeting_password: Optional[str] = None


class InterviewResponse(InterviewBase):
    """Schema for interview response"""
    id: UUID
    candidate_id: UUID
    interviewer_id: Optional[UUID] = None
    job_id: UUID
    scheduled_time: Optional[datetime] = None
    status: str = "scheduled"
    reschedule_count: int = 0
    max_reschedules: int = 2
    feedback_submitted: bool = False
    recommendation: Optional[str] = None
    next_round_required: bool = False
    next_round_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class InterviewFeedbackBase(BaseModel):
    """Base interview feedback schema"""
    technical_score: Optional[float] = Field(None, ge=0, le=10)
    communication_score: Optional[float] = Field(None, ge=0, le=10)
    problem_solving_score: Optional[float] = Field(None, ge=0, le=10)
    overall_score: Optional[float] = Field(None, ge=0, le=10)
    recommendation: str = Field(..., regex="^(select|reject|next_round|on_hold)$")
    detailed_feedback: str = ""
    interviewer_notes: Optional[str] = ""
    next_round_required: bool = False
    follow_up_actions: List[str] = Field(default_factory=list)


class InterviewFeedbackCreate(InterviewFeedbackBase):
    """Schema for creating interview feedback"""
    interview_id: UUID
    criteria_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    technical_assessment: Optional[str] = ""
    behavioral_assessment: Optional[str] = ""
    hire_recommendation: str = Field(..., regex="^(strong_yes|yes|no|strong_no)$")
    confidence_level: str = Field("medium", regex="^(high|medium|low)$")
    next_steps: Optional[str] = ""


class InterviewFeedbackResponse(InterviewFeedbackBase):
    """Schema for interview feedback response"""
    id: UUID
    interview_id: UUID
    criteria_scores: Dict[str, float]
    strengths: List[str]
    areas_for_improvement: List[str]
    technical_assessment: Optional[str]
    behavioral_assessment: Optional[str]
    hire_recommendation: str
    confidence_level: str
    next_steps: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
