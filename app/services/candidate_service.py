from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.models.candidate import Candidate, CandidateEvaluation
from app.models.interview import Interview
from app.models.workflow import EmailLog
from app.schemas.candidate import CandidateUpdate
from app.core.exceptions import CandidateNotFoundError, ValidationError


class CandidateService:
    """Service class for candidate operations"""

    def __init__(self, db: Session):
        self.db = db

    async def create_candidate_with_resume(
        self,
        candidate_info: Dict[str, Any],
        resume_text: str,
        resume_file_path: str,
        job_id: str
    ) -> Candidate:
        """Create a new candidate with resume"""
        try:
            candidate = Candidate(
                name=candidate_info.get("name", ""),
                email=candidate_info.get("email", ""),
                phone=candidate_info.get("phone", ""),
                experience_years=candidate_info.get("experience_years", 0),
                technologies=candidate_info.get("technologies", []),
                interview_availability=candidate_info.get("interview_availability", ""),
                time_availability=candidate_info.get("time_availability", ""),
                resume_text=resume_text,
                resume_file_path=resume_file_path,
                job_id=UUID(job_id),
                current_stage="resume_received"
            )

            self.db.add(candidate)
            self.db.commit()
            self.db.refresh(candidate)

            return candidate

        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to create candidate: {str(e)}")

    async def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """Get candidate by ID"""
        try:
            return self.db.query(Candidate)\
                .options(
                    joinedload(Candidate.evaluations),
                    joinedload(Candidate.interviews),
                    joinedload(Candidate.job)
                )\
                .filter(Candidate.id == UUID(candidate_id))\
                .first()
        except Exception as e:
            raise ValidationError(f"Failed to get candidate: {str(e)}")

    async def list_candidates(
        self,
        skip: int = 0,
        limit: int = 100,
        stage: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> List[Candidate]:
        """List candidates with filtering"""
        try:
            query = self.db.query(Candidate)\
                .options(joinedload(Candidate.job))

            if stage:
                query = query.filter(Candidate.current_stage == stage)

            if job_id:
                query = query.filter(Candidate.job_id == UUID(job_id))

            return query.offset(skip).limit(limit).all()

        except Exception as e:
            raise ValidationError(f"Failed to list candidates: {str(e)}")

    async def update_candidate(
        self,
        candidate_id: str,
        candidate_update: CandidateUpdate
    ) -> Optional[Candidate]:
        """Update candidate information"""
        try:
            candidate = await self.get_candidate(candidate_id)
            if not candidate:
                raise CandidateNotFoundError(f"Candidate {candidate_id} not found")

            update_data = candidate_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(candidate, field, value)

            self.db.commit()
            self.db.refresh(candidate)

            return candidate

        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to update candidate: {str(e)}")

    async def update_candidate_stage(
        self, candidate_id: str, new_stage: str
    ) -> Optional[Candidate]:
        """Update candidate stage"""
        try:
            candidate = await self.get_candidate(candidate_id)
            if not candidate:
                return None

            candidate.current_stage = new_stage
            self.db.commit()
            self.db.refresh(candidate)

            return candidate

        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to update candidate stage: {str(e)}")

    async def get_candidate_evaluations(
        self, candidate_id: str
    ) -> List[CandidateEvaluation]:
        """Get all evaluations for a candidate"""
        try:
            return self.db.query(CandidateEvaluation)\
                .filter(CandidateEvaluation.candidate_id == UUID(candidate_id))\
                .order_by(CandidateEvaluation.created_at.desc())\
                .all()
        except Exception as e:
            raise ValidationError(f"Failed to get candidate evaluations: {str(e)}")

    async def get_comprehensive_status(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive candidate status"""
        try:
            candidate = await self.get_candidate(candidate_id)
            if not candidate:
                return None

            # Get evaluations
            evaluations = await self.get_candidate_evaluations(candidate_id)

            # Get interviews
            interviews = self.db.query(Interview)\
                .filter(Interview.candidate_id == UUID(candidate_id))\
                .order_by(Interview.created_at.desc())\
                .all()

            # Get email logs
            emails = self.db.query(EmailLog)\
                .filter(EmailLog.candidate_id == UUID(candidate_id))\
                .order_by(EmailLog.created_at.desc())\
                .limit(10)\
                .all()

            # Determine next steps
            next_steps = self._determine_next_steps(candidate, evaluations, interviews)

            return {
                "candidate": candidate,
                "evaluations": evaluations,
                "interviews": [
                    {
                        "id": str(interview.id),
                        "type": interview.interview_type,
                        "scheduled_time": interview.scheduled_time.isoformat() if interview.scheduled_time else None,
                        "status": interview.status,
                        "recommendation": interview.recommendation
                    } for interview in interviews
                ],
                "recent_emails": [
                    {
                        "type": email.email_type,
                        "recipient": email.recipient_email,
                        "subject": email.subject,
                        "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                        "status": "sent" if email.sent_successfully else "failed"
                    } for email in emails
                ],
                "next_steps": next_steps,
                "overall_progress": self._calculate_progress(candidate, interviews)
            }

        except Exception as e:
            raise ValidationError(f"Failed to get comprehensive status: {str(e)}")

    def _determine_next_steps(
        self,
        candidate: Candidate,
        evaluations: List[CandidateEvaluation],
        interviews: List[Interview]
    ) -> List[str]:
        """Determine next steps for candidate"""
        steps = []
        
        if candidate.current_stage == "resume_received":
            steps.append("Resume evaluation pending")
        elif candidate.current_stage == "pending_tech_lead_review":
            steps.append("Awaiting tech lead approval")
        elif candidate.current_stage == "approved_for_interview":
            steps.append("Schedule interview")
        elif candidate.current_stage == "interview_scheduled":
            next_interview = next(
                (i for i in interviews if i.status == "scheduled"), 
                None
            )
            if next_interview and next_interview.scheduled_time:
                steps.append(f"Interview on {next_interview.scheduled_time.strftime('%Y-%m-%d %H:%M')}")
        elif candidate.current_stage == "interview_completed":
            steps.append("Awaiting final decision")
        elif candidate.current_stage == "selected":
            steps.append("Send offer letter")
        elif candidate.current_stage == "rejected":
            steps.append("Send rejection email")

        return steps

    def _calculate_progress(
        self, candidate: Candidate, interviews: List[Interview]
    ) -> Dict[str, Any]:
        """Calculate overall progress percentage"""
        stages = [
            "resume_received", "resume_screening", "pending_tech_lead_review",
            "approved_for_interview", "interview_scheduled", "interview_completed",
            "selected"
        ]

        try:
            current_index = stages.index(candidate.current_stage)
            progress = int((current_index / len(stages)) * 100)
        except ValueError:
            progress = 0

        return {
            "percentage": progress,
            "current_stage": candidate.current_stage,
            "total_stages": len(stages),
            "completed_stages": current_index + 1 if progress > 0 else 0
        }

    async def delete_candidate(self, candidate_id: str) -> bool:
        """Soft delete candidate"""
        try:
            candidate = await self.get_candidate(candidate_id)
            if not candidate:
                return False

            candidate.is_active = False
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to delete candidate: {str(e)}")

    async def search_candidates(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Candidate]:
        """Search candidates by name, email, or technologies"""
        try:
            search_query = self.db.query(Candidate)

            # Text search
            if query:
                search_query = search_query.filter(
                    or_(
                        Candidate.name.ilike(f"%{query}%"),
                        Candidate.email.ilike(f"%{query}%"),
                        Candidate.technologies.op('?')(query)  # PostgreSQL JSON contains
                    )
                )

            # Apply filters
            if filters:
                if filters.get("min_experience"):
                    search_query = search_query.filter(
                        Candidate.experience_years >= filters["min_experience"]
                    )
                if filters.get("max_experience"):
                    search_query = search_query.filter(
                        Candidate.experience_years <= filters["max_experience"]
                    )
                if filters.get("technologies"):
                    for tech in filters["technologies"]:
                        search_query = search_query.filter(
                            Candidate.technologies.op('?')(tech)
                        )
                if filters.get("min_score"):
                    search_query = search_query.filter(
                        Candidate.overall_score >= filters["min_score"]
                    )

            return search_query.limit(50).all()

        except Exception as e:
            raise ValidationError(f"Failed to search candidates: {str(e)}")
