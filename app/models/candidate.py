from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    JSON,
    ForeignKey,
    DateTime,
    func
)


class Candidate(BaseModel):
    __tablename__ = "candidates"

    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))

    # Professional Information
    experience_years = Column(Integer, default=0)
    technologies = Column(JSON, default=list)
    resume_text = Column(Text)
    resume_file_path = Column(String(500))

    # Availability
    interview_availability = Column(String(100))
    time_availability = Column(String(255))

    # Workflow Status
    current_stage = Column(String(50), default="resume_received", index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), index=True)

    # Evaluation Scores
    overall_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    education_score = Column(Float, default=0.0)
    skills_score = Column(Float, default=0.0)
    ats_score = Column(Float, default=0.0)
    match_percentage = Column(Integer, default=0)

    # Relationships
    workflow = relationship("Workflow", back_populates="candidates")
    job = relationship("Job", back_populates="candidates")
    interviews = relationship("Interview", back_populates="candidate")
    evaluations = relationship("CandidateEvaluation", back_populates="candidate")
    email_logs = relationship("EmailLog", back_populates="candidate")


class CandidateEvaluation(BaseModel):
    __tablename__ = "candidate_evaluations"

    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    evaluation_type = Column(String(50), nullable=False)  # technical, experience, etc.

    # Evaluation Results
    score = Column(Float, nullable=False)
    feedback = Column(Text)
    key_points = Column(JSON, default=list)
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)

    # LLM Details
    model_used = Column(String(100))
    evaluation_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    candidate = relationship("Candidate", back_populates="evaluations")
