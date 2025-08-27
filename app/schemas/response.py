from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """Generic base response schema"""
    success: bool = True
    message: str = ""
    data: Optional[T] = None
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response schema"""
    items: List[T]
    total: int
    page: int = 1
    per_page: int = 100
    pages: int
    has_prev: bool = False
    has_next: bool = False


class ErrorResponse(BaseModel):
    """Error response schema"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel):
    """Success response schema"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentExecutionResponse(BaseModel):
    """Response schema for agent execution"""
    agent_name: str
    execution_id: str
    status: str  # running, completed, failed, paused
    result: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    execution_time_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
