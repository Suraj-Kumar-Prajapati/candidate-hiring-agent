from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.schemas.interview import (
    InterviewResponse, InterviewCreate, InterviewUpdate,
    InterviewFeedbackCreate, InterviewFeedbackResponse
)
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/", response_model=InterviewResponse)
async def create_interview(interview_data: InterviewCreate, db: Session = Depends(get_db)):
    """Create a new interview"""
    try:
        interview_service = InterviewService(db)
        interview = await interview_service.create_interview(interview_data)
        return InterviewResponse.from_orm(interview)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create interview: {str(e)}")


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(interview_id: UUID, db: Session = Depends(get_db)):
    """Get interview by ID"""
    interview_service = InterviewService(db)
    interview = await interview_service.get_interview(str(interview_id))
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    return InterviewResponse.from_orm(interview)


@router.put("/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: UUID, 
    interview_update: InterviewUpdate, 
    db: Session = Depends(get_db)
):
    """Update interview information"""
    interview_service = InterviewService(db)
    interview = await interview_service.update_interview(str(interview_id), interview_update)
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    return InterviewResponse.from_orm(interview)


@router.post("/{interview_id}/feedback", response_model=InterviewFeedbackResponse)
async def submit_interview_feedback(
    interview_id: UUID,
    feedback_data: InterviewFeedbackCreate,
    db: Session = Depends(get_db)
):
    """Submit interview feedback"""
    try:
        interview_service = InterviewService(db)
        feedback = await interview_service.submit_feedback(str(interview_id), feedback_data)
        return InterviewFeedbackResponse.from_orm(feedback)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to submit feedback: {str(e)}")


@router.get("/candidate/{candidate_id}", response_model=List[InterviewResponse])
async def get_candidate_interviews(candidate_id: UUID, db: Session = Depends(get_db)):
    """Get all interviews for a candidate"""
    interview_service = InterviewService(db)
    interviews = await interview_service.get_candidate_interviews(str(candidate_id))
    return [InterviewResponse.from_orm(interview) for interview in interviews]


@router.post("/{interview_id}/reschedule")
async def reschedule_interview(
    interview_id: UUID,
    new_time: datetime,
    db: Session = Depends(get_db)
):
    """Reschedule an interview"""
    try:
        interview_service = InterviewService(db)
        interview = await interview_service.reschedule_interview(str(interview_id), new_time)
        
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        return {"status": "rescheduled", "new_time": new_time}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to reschedule: {str(e)}")


@router.post("/{interview_id}/cancel")
async def cancel_interview(
    interview_id: UUID,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Cancel an interview"""
    try:
        interview_service = InterviewService(db)
        interview = await interview_service.cancel_interview(str(interview_id), reason)
        
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        return {"status": "cancelled", "reason": reason}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to cancel: {str(e)}")
