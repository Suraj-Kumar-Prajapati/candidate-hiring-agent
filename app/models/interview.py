from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from sqlalchemy import (
    Column, String, DateTime, Text, JSON,
    ForeignKey, Boolean, UUID, Integer, Float
)


class Interview(BaseModel):
    __tablename__ = "interviews"

    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    interviewer_id = Column(UUID(as_uuid=True), ForeignKey("job_interviewers.id"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)

    # Interview Details
    interview_type = Column(String(50), nullable=False)  # technical_round_1, hr_round, etc.
    round_number = Column(Integer, default=1)
    scheduled_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer, default=60)

    # Meeting Information
    meeting_link = Column(String(500))
    meeting_id = Column(String(100))
    meeting_password = Column(String(100))

    # Status Management
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled, rescheduled
    reschedule_count = Column(Integer, default=0)
    max_reschedules = Column(Integer, default=2)

    # Feedback and Results
    feedback_submitted = Column(Boolean, default=False)
    technical_score = Column(Float)
    communication_score = Column(Float)
    problem_solving_score = Column(Float)
    overall_score = Column(Float)
    recommendation = Column(String(50))  # select, reject, next_round, on_hold
    detailed_feedback = Column(Text)
    interviewer_notes = Column(Text)

    # Follow-up
    next_round_required = Column(Boolean, default=False)
    next_round_type = Column(String(50))
    follow_up_actions = Column(JSON, default=list)

    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")
    interviewer = relationship("JobInterviewer", back_populates="interviews")
    job = relationship("Job")


class InterviewFeedback(BaseModel):
    __tablename__ = "interview_feedbacks"

    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id"), nullable=False)

    # Structured Feedback
    criteria_scores = Column(JSON, default=dict)  # flexible scoring criteria
    strengths = Column(JSON, default=list)
    areas_for_improvement = Column(JSON, default=list)
    technical_assessment = Column(Text)
    behavioral_assessment = Column(Text)

    # Recommendations
    hire_recommendation = Column(String(50))  # strong_yes, yes, no, strong_no
    confidence_level = Column(String(50))  # high, medium, low
    next_steps = Column(Text)

    # Interview Relationship
    interview = relationship("Interview")
