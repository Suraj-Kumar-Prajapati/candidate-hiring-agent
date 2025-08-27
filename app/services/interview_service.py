from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from app.models.interview import Interview, InterviewFeedback
from app.schemas.interview import (
    InterviewCreate, InterviewUpdate,
    InterviewFeedbackCreate
)
from app.core.exceptions import InterviewNotFoundError, ValidationError


class InterviewService:
    """Service class for interview operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_interview(self, interview_data: InterviewCreate) -> Interview:
        """Create a new interview"""
        try:
            interview = Interview(**interview_data.dict())
            
            self.db.add(interview)
            self.db.commit()
            self.db.refresh(interview)
            
            return interview
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to create interview: {str(e)}")
    
    async def get_interview(self, interview_id: str) -> Optional[Interview]:
        """Get interview by ID"""
        try:
            return self.db.query(Interview)\
                .options(
                    joinedload(Interview.candidate),
                    joinedload(Interview.interviewer)
                )\
                .filter(Interview.id == UUID(interview_id))\
                .first()
        except Exception as e:
            raise ValidationError(f"Failed to get interview: {str(e)}")
    
    async def update_interview(
        self,
        interview_id: str,
        interview_update: InterviewUpdate
    ) -> Optional[Interview]:
        """Update interview information"""
        try:
            interview = await self.get_interview(interview_id)
            if not interview:
                raise InterviewNotFoundError(f"Interview {interview_id} not found")
            
            update_data = interview_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(interview, field, value)
            
            self.db.commit()
            self.db.refresh(interview)
            
            return interview
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to update interview: {str(e)}")
    
    async def submit_feedback(
        self,
        interview_id: str,
        feedback_data: InterviewFeedbackCreate
    ) -> InterviewFeedback:
        """Submit interview feedback"""
        try:
            interview = await self.get_interview(interview_id)
            if not interview:
                raise InterviewNotFoundError(f"Interview {interview_id} not found")
            
            # Create feedback
            feedback = InterviewFeedback(
                interview_id=UUID(interview_id),
                **feedback_data.dict(exclude={'interview_id'})
            )
            
            # Update interview with feedback summary
            interview.feedback_submitted = True
            interview.technical_score = feedback_data.technical_score
            interview.communication_score = feedback_data.communication_score
            interview.problem_solving_score = feedback_data.problem_solving_score
            interview.overall_score = feedback_data.overall_score
            interview.recommendation = feedback_data.recommendation
            interview.detailed_feedback = feedback_data.detailed_feedback
            interview.next_round_required = feedback_data.next_round_required
            interview.status = "completed"
            
            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)
            
            return feedback
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to submit feedback: {str(e)}")
    
    async def get_candidate_interviews(self, candidate_id: str) -> List[Interview]:
        """Get all interviews for a candidate"""
        try:
            return self.db.query(Interview)\
                .options(joinedload(Interview.interviewer))\
                .filter(Interview.candidate_id == UUID(candidate_id))\
                .order_by(Interview.created_at.desc())\
                .all()
        except Exception as e:
            raise ValidationError(f"Failed to get candidate interviews: {str(e)}")
    
    async def get_interviewer_schedule(
        self, 
        interviewer_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Interview]:
        """Get interviewer's schedule for a date range"""
        try:
            return self.db.query(Interview)\
                .filter(Interview.interviewer_id == UUID(interviewer_id))\
                .filter(Interview.scheduled_time >= start_date)\
                .filter(Interview.scheduled_time <= end_date)\
                .filter(Interview.status.in_(["scheduled", "in_progress"]))\
                .order_by(Interview.scheduled_time)\
                .all()
        except Exception as e:
            raise ValidationError(f"Failed to get interviewer schedule: {str(e)}")
    
    async def find_available_slots(
        self, 
        interviewer_id: str, 
        preferred_dates: List[datetime], 
        duration_minutes: int = 60
    ) -> List[datetime]:
        """Find available time slots for an interviewer"""
        try:
            available_slots = []
            
            for date in preferred_dates:
                # Get existing interviews for this date
                start_of_day = date.replace(hour=9, minute=0, second=0, microsecond=0)
                end_of_day = date.replace(hour=17, minute=0, second=0, microsecond=0)
                
                existing_interviews = await self.get_interviewer_schedule(
                    interviewer_id, start_of_day, end_of_day
                )
                
                # Find gaps between interviews
                busy_slots = [
                    (interview.scheduled_time, 
                     interview.scheduled_time + timedelta(minutes=interview.duration_minutes))
                    for interview in existing_interviews
                    if interview.scheduled_time
                ]
                
                # Check hourly slots from 9 AM to 5 PM
                current_time = start_of_day
                while current_time <= end_of_day - timedelta(minutes=duration_minutes):
                    slot_end = current_time + timedelta(minutes=duration_minutes)
                    
                    # Check if slot conflicts with existing interviews
                    is_available = True
                    for busy_start, busy_end in busy_slots:
                        if (current_time < busy_end and slot_end > busy_start):
                            is_available = False
                            break
                    
                    if is_available:
                        available_slots.append(current_time)
                    
                    current_time += timedelta(hours=1)
            
            return available_slots
            
        except Exception as e:
            raise ValidationError(f"Failed to find available slots: {str(e)}")
    
    async def reschedule_interview(
        self, 
        interview_id: str, 
        new_time: datetime
    ) -> Optional[Interview]:
        """Reschedule an interview"""
        try:
            interview = await self.get_interview(interview_id)
            if not interview:
                raise InterviewNotFoundError(f"Interview {interview_id} not found")
            
            # Check reschedule limit
            if interview.reschedule_count >= interview.max_reschedules:
                raise ValidationError("Maximum reschedule attempts exceeded")
            
            interview.scheduled_time = new_time
            interview.reschedule_count += 1
            interview.status = "rescheduled"
            
            self.db.commit()
            self.db.refresh(interview)
            
            return interview
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to reschedule interview: {str(e)}")
    
    async def cancel_interview(
        self, 
        interview_id: str, 
        reason: Optional[str] = None
    ) -> Optional[Interview]:
        """Cancel an interview"""
        try:
            interview = await self.get_interview(interview_id)
            if not interview:
                raise InterviewNotFoundError(f"Interview {interview_id} not found")
            
            interview.status = "cancelled"
            if reason:
                interview.interviewer_notes = f"Cancelled: {reason}"
            
            self.db.commit()
            self.db.refresh(interview)
            
            return interview
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to cancel interview: {str(e)}")
