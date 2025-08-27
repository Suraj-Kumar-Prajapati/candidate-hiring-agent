from fastapi import HTTPException
from typing import Optional, Dict, Any


class BaseCustomException(Exception):
    """Base exception class for custom exceptions"""

    def __init__(
        self, message: str, error_code: str = "GENERIC_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseCustomException):
    """Raised when input validation fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class CandidateNotFoundError(BaseCustomException):
    """Raised when candidate is not found"""

    def __init__(self, message: str = "Candidate not found"):
        super().__init__(message, "CANDIDATE_NOT_FOUND")


class JobNotFoundError(BaseCustomException):
    """Raised when job is not found"""

    def __init__(self, message: str = "Job not found"):
        super().__init__(message, "JOB_NOT_FOUND")


class InterviewNotFoundError(BaseCustomException):
    """Raised when interview is not found"""

    def __init__(self, message: str = "Interview not found"):
        super().__init__(message, "INTERVIEW_NOT_FOUND")


class WorkflowNotFoundError(BaseCustomException):
    """Raised when workflow is not found"""
    
    def __init__(self, message: str = "Workflow not found"):
        super().__init__(message, "WORKFLOW_NOT_FOUND")


class FileProcessingError(BaseCustomException):
    """Raised when file processing fails"""
    
    def __init__(self, message: str = "File processing failed"):
        super().__init__(message, "FILE_PROCESSING_ERROR")


class EmailDeliveryError(BaseCustomException):
    """Raised when email delivery fails"""
    
    def __init__(self, message: str = "Email delivery failed"):
        super().__init__(message, "EMAIL_DELIVERY_ERROR")


class AgentExecutionError(BaseCustomException):
    """Raised when agent execution fails"""
    
    def __init__(self, message: str = "Agent execution failed", agent_name: str = ""):
        super().__init__(message, "AGENT_EXECUTION_ERROR", {"agent_name": agent_name})


class WorkflowExecutionError(BaseCustomException):
    """Raised when workflow execution fails"""
    
    def __init__(self, message: str = "Workflow execution failed"):
        super().__init__(message, "WORKFLOW_EXECUTION_ERROR")


# HTTP Exception handlers
def create_http_exception(exc: BaseCustomException, status_code: int = 400) -> HTTPException:
    """Convert custom exception to HTTP exception"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


# Exception status code mapping
EXCEPTION_STATUS_CODES = {
    "VALIDATION_ERROR": 400,
    "CANDIDATE_NOT_FOUND": 404,
    "JOB_NOT_FOUND": 404,
    "INTERVIEW_NOT_FOUND": 404,
    "WORKFLOW_NOT_FOUND": 404,
    "FILE_PROCESSING_ERROR": 400,
    "EMAIL_DELIVERY_ERROR": 500,
    "AGENT_EXECUTION_ERROR": 500,
    "WORKFLOW_EXECUTION_ERROR": 500,
}
