from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.models.job import Job, JobInterviewer
from app.schemas.job import JobCreate, JobUpdate, JobInterviewerCreate
from app.core.exceptions import JobNotFoundError, ValidationError


class JobService:
    """Service class for job operations"""

    def __init__(self, db: Session):
        self.db = db

    async def create_job(self, job_data: JobCreate) -> Job:
        """Create a new job posting"""
        try:
            job = Job(**job_data.dict())

            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

            return job

        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to create job: {str(e)}")

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        try:
            return self.db.query(Job)\
                .options(
                    joinedload(Job.candidates),
                    joinedload(Job.interviewers),
                    joinedload(Job.workflows)
                )\
                .filter(Job.id == UUID(job_id))\
                .first()
        except Exception as e:
            raise ValidationError(f"Failed to get job: {str(e)}")

    async def list_jobs(
        self,
        skip: int = 0, 
        limit: int = 100, 
        status: Optional[str] = None,
        department: Optional[str] = None
    ) -> List[Job]:
        """List jobs with filtering"""
        try:
            query = self.db.query(Job)

            if status:
                query = query.filter(Job.status == status)

            if department:
                query = query.filter(Job.department == department)

            return query.filter(Job.is_active == True)\
                .offset(skip)\
                .limit(limit)\
                .all()
       
        except Exception as e:
            raise ValidationError(f"Failed to list jobs: {str(e)}")

    async def update_job(self, job_id: str, job_update: JobUpdate) -> Optional[Job]:
        """Update job information"""
        try:
            job = await self.get_job(job_id)
            if not job:
                raise JobNotFoundError(f"Job {job_id} not found")
            
            update_data = job_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(job, field, value)
            
            self.db.commit()
            self.db.refresh(job)
            
            return job
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to update job: {str(e)}")
    
    async def add_interviewer(
        self, 
        job_id: str, 
        interviewer_data: JobInterviewerCreate
    ) -> JobInterviewer:
        """Add interviewer to job"""
        try:
            job = await self.get_job(job_id)
            if not job:
                raise JobNotFoundError(f"Job {job_id} not found")
            
            interviewer = JobInterviewer(
                job_id=UUID(job_id),
                **interviewer_data.dict(exclude={'job_id'})
            )
            
            self.db.add(interviewer)
            self.db.commit()
            self.db.refresh(interviewer)
            
            return interviewer
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to add interviewer: {str(e)}")
    
    async def get_job_interviewers(self, job_id: str) -> List[JobInterviewer]:
        """Get all interviewers for a job"""
        try:
            return self.db.query(JobInterviewer)\
                .filter(JobInterviewer.job_id == UUID(job_id))\
                .filter(JobInterviewer.is_active == True)\
                .all()
        except Exception as e:
            raise ValidationError(f"Failed to get job interviewers: {str(e)}")
    
    async def find_matching_interviewers(
        self, 
        job_id: str, 
        required_technologies: List[str]
    ) -> List[JobInterviewer]:
        """Find interviewers matching required technologies"""
        try:
            interviewers = await self.get_job_interviewers(job_id)
            
            matching_interviewers = []
            for interviewer in interviewers:
                interviewer_techs = set(tech.lower() for tech in interviewer.technologies)
                required_techs = set(tech.lower() for tech in required_technologies)
                
                # Calculate match score
                match_score = len(interviewer_techs.intersection(required_techs))
                if match_score > 0:
                    # Add match score to interviewer object for sorting
                    interviewer.match_score = match_score
                    matching_interviewers.append(interviewer)
            
            # Sort by match score (highest first)
            return sorted(matching_interviewers, key=lambda x: x.match_score, reverse=True)
            
        except Exception as e:
            raise ValidationError(f"Failed to find matching interviewers: {str(e)}")
    
    async def get_job_statistics(self, job_id: str) -> Dict[str, Any]:
        """Get job statistics"""
        try:
            job = await self.get_job(job_id)
            if not job:
                return {}
            
            from app.models.candidate import Candidate
            candidates = self.db.query(Candidate)\
                .filter(Candidate.job_id == UUID(job_id))\
                .all()
            
            # Calculate statistics
            total_candidates = len(candidates)
            stage_counts = {}
            score_stats = {}
            
            if candidates:
                # Stage distribution
                for candidate in candidates:
                    stage = candidate.current_stage
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1
                
                # Score statistics
                scores = [c.overall_score for c in candidates if c.overall_score > 0]
                if scores:
                    score_stats = {
                        "average_score": sum(scores) / len(scores),
                        "highest_score": max(scores),
                        "lowest_score": min(scores)
                    }
            
            return {
                "job_id": job_id,
                "total_candidates": total_candidates,
                "stage_distribution": stage_counts,
                "score_statistics": score_stats,
                "positions_available": job.positions_available,
                "job_status": job.status
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to get job statistics: {str(e)}")
