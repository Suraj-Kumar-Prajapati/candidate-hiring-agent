from sqlalchemy import (
    Column,
    String,
    JSON,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    Integer,
    UUID
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Workflow(BaseModel):
    __tablename__ = "workflows"

    # workflow identity
    workflow_type = Column(String(100), default="hiring_workflow")
    name = Column(String(255))
    description = Column(Text)

    # Associated Job
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)

    # Workflow Status
    current_stage = Column(String(50), default="initiated")
    status = Column(String(50), default="running")  # running, paused, completed, failed
    progress_percentage = Column(Integer, default=0)

    # Configuration
    workflow_config = Column(JSON, default=dict)
    agent_configs = Column(JSON, default=dict)

    # State Management
    current_state = Column(JSON, default=dict)
    state_history = Column(JSON, default=list)
    checkpoints = Column(JSON, default=list)

    # Execution Details
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True))

    # Human Intervention
    human_decisions_pending = Column(JSON, default=list)
    human_decision_history = Column(JSON, default=list)
    auto_resume = Column(Boolean, default=True)

    # Error Handling
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Performance Metrics
    total_execution_time = Column(Integer)  # in seconds
    agent_execution_stats = Column(JSON, default=dict)

    # Relationships
    job = relationship("Job", back_populates="workflows")
    candidates = relationship("Candidate", back_populates="workflow")
    workflow_logs = relationship("WorkflowLog", back_populates="workflow")


class WorkflowLog(BaseModel):
    __tablename__ = "workflow_logs"

    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)

    # Log Details
    log_level = Column(String(20), default="INFO")  # DEBUG, INFO, WARNING, ERROR
    agent_name = Column(String(100))
    node_name = Column(String(100))

    # Message
    message = Column(Text, nullable=False)
    details = Column(JSON, default=dict)

    # Context
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    execution_time_ms = Column(Integer)

    # Relationships
    workflow = relationship("Workflow", back_populates="workflow_logs")


class EmailLog(BaseModel):
    __tablename__ = "email_logs"

    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"))

    # Email Details
    email_type = Column(String(50), nullable=False)  # invitation, rejection, reminder
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255))
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)

    # Sending Details
    sent_at = Column(DateTime(timezone=True))
    sent_successfully = Column(Boolean, default=False)
    error_message = Column(Text)

    # Email Service Details
    message_id = Column(String(255))
    provider = Column(String(50), default="smtp")

    # Relationships
    candidate = relationship("Candidate", back_populates="email_logs")
    workflow = relationship("Workflow")
