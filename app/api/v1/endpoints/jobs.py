from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas.job import JobResponse, JobCreate, JobUpdate, JobInterviewerCreate, JobInterviewerResponse
from app.services.job_service import JobService


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse)
async def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """Create a new job posting"""
    try:
        job_service = JobService(db)
        job = await job_service.create_job(job_data)
        return JobResponse.from_orm(job)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create job: {str(e)}")


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List jobs with filtering"""
    job_service = JobService(db)
    jobs = await job_service.list_jobs(skip=skip, limit=limit, status=status, department=department)
    return [JobResponse.from_orm(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Get job by ID"""
    job_service = JobService(db)
    job = await job_service.get_job(str(job_id))
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse.from_orm(job)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id: UUID, job_update: JobUpdate, db: Session = Depends(get_db)):
    """Update job information"""
    job_service = JobService(db)
    job = await job_service.update_job(str(job_id), job_update)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse.from_orm(job)


@router.post("/{job_id}/upload-description")
async def upload_job_description(
    job_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload job description from Word document"""
    try:
        from app.utils.file_processing import process_uploaded_resume
        
        # Process the uploaded file
        job_description_text, file_path = await process_uploaded_resume(file)
        
        # Update job with description
        job_service = JobService(db)
        from app.schemas.job import JobUpdate
        job_update = JobUpdate(
            description=job_description_text,
            job_description_file=file_path
        )
        
        job = await job_service.update_job(str(job_id), job_update)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"status": "success", "message": "Job description uploaded successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to upload job description: {str(e)}")


@router.post("/{job_id}/interviewers", response_model=JobInterviewerResponse)
async def add_interviewer(
    job_id: UUID,
    interviewer_data: JobInterviewerCreate,
    db: Session = Depends(get_db)
):
    """Add interviewer to job"""
    job_service = JobService(db)
    interviewer = await job_service.add_interviewer(str(job_id), interviewer_data)
    return JobInterviewerResponse.from_orm(interviewer)


@router.get("/{job_id}/interviewers", response_model=List[JobInterviewerResponse])
async def get_job_interviewers(job_id: UUID, db: Session = Depends(get_db)):
    """Get all interviewers for a job"""
    job_service = JobService(db)
    interviewers = await job_service.get_job_interviewers(str(job_id))
    return [JobInterviewerResponse.from_orm(interviewer) for interviewer in interviewers]


@router.get("/{job_id}/statistics")
async def get_job_statistics(job_id: UUID, db: Session = Depends(get_db)):
    """Get job statistics"""
    job_service = JobService(db)
    statistics = await job_service.get_job_statistics(str(job_id))
    return statistics
