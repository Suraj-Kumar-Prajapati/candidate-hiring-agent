from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from sqlalchemy import (
    Column, String, Integer, Text,
    JSON, Boolean, UUID, ForeignKey
)


class Job(BaseModel):
    __tablename__ = "jobs"

    # Job Information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    department = Column(String(100))
    location = Column(String(255))
    employment_type = Column(String(50), default="Full-time")

    # Requirements
    experience_required = Column(String(100))
    technologies_required = Column(JSON, default=list)
    education_requirements = Column(Text)
    skills_required = Column(JSON, default=list)

    # Job Details
    salary_range_min = Column(Integer)
    salary_range_max = Column(Integer)
    currency = Column(String(10), default="INR")
    remote_allowed = Column(Boolean, default=False)

    # File References
    job_description_file = Column(String(500))

    # Status
    status = Column(String(50), default="active")  # active, paused, closed
    positions_available = Column(Integer, default=1)

    # Relationships
    candidates = relationship("Candidate", back_populates="job")
    workflows = relationship("Workflow", back_populates="job")
    interviewers = relationship("JobInterviewer", back_populates="job")


class JobInterviewer(BaseModel):
    __tablename__ = "job_interviewers"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)

    # Interviewer Information
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(100))
    department = Column(String(100))

    # Capabilities
    technologies = Column(JSON, default=list)
    interview_types = Column(JSON, default=list)  # technical, managerial, hr
    seniority_level = Column(String(50))  # junior, mid, senior, lead

    # Availability
    availability_slots = Column(JSON, default=list)
    timezone = Column(String(50), default="UTC")
    max_interviews_per_day = Column(Integer, default=3)

    # Relationships
    job = relationship("Job", back_populates="interviewers")
    interviews = relationship("Interview", back_populates="interviewer")
