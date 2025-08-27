from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class WorkflowBase(BaseModel):
    """Base workflow schema"""
    workflow_type: str = "hiring_workflow"
    name: Optional[str] = None
    description: Optional[str] = None


class WorkflowCreate(WorkflowBase):
    """Schema for creating workflow"""
    job_id: UUID
    workflow_config: Dict[str, Any] = Field(default_factory=dict)
    agent_configs: Dict[str, Any] = Field(default_factory=dict)
    auto_resume: bool = True
    max_retries: int = 3


class WorkflowUpdate(BaseModel):
    """Schema for updating workflow"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    workflow_config: Optional[Dict[str, Any]] = None
    auto_resume: Optional[bool] = None


class WorkflowResponse(WorkflowBase):
    """Schema for workflow response"""
    id: UUID
    job_id: UUID
    current_stage: str
    status: str
    progress_percentage: int = 0
    workflow_config: Dict[str, Any]
    agent_configs: Dict[str, Any]
    current_state: Dict[str, Any]
    human_decisions_pending: List[str]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    auto_resume: bool = True
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class HumanDecisionRequest(BaseModel):
    """Schema for human decision input"""
    decision_type: str = Field(..., regex="^(reject_candidate|approve_for_interview|schedule_interview|final_selection)$")
    candidate_id: UUID
    decision: str = Field(..., regex="^(approve|reject|hold|reschedule)$")
    comments: Optional[str] = ""
    interviewer_id: Optional[UUID] = None
    scheduled_time: Optional[datetime] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)


class WorkflowStatusResponse(BaseModel):
    """Comprehensive workflow status response"""
    workflow: WorkflowResponse
    candidates: List[Dict[str, Any]]
    pending_decisions: List[Dict[str, Any]]
    recent_activities: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    next_steps: List[str]


class WorkflowLogResponse(BaseModel):
    """Schema for workflow log response"""
    id: UUID
    workflow_id: UUID
    log_level: str
    agent_name: Optional[str]
    node_name: Optional[str]
    message: str
    details: Dict[str, Any]
    candidate_id: Optional[UUID]
    execution_time_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
