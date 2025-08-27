from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import (
    CandidateResponse,
    CandidateEvaluationResponse
)
from app.services.candidate_service import CandidateService
from app.agents.resume_evaluator import (
    ResumeEvaluatorAgent, ResumeEvaluatorConfig
)
from app.utils.file_processing import process_uploaded_resume

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/", response_model=CandidateResponse)
async def create_candidate(
    candidate_data: str = Form(...),
    resume_file: UploadFile = File(...),
    job_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    """Create a new candidate with resume upload"""
    try:
        # Parse candidate data
        import json
        candidate_info = json.loads(candidate_data)

        # Process resume file
        resume_text, file_path = await process_uploaded_resume(resume_file)

        # Create candidate
        candidate_service = CandidateService(db)
        candidate = await candidate_service.create_candidate_with_resume(
            candidate_info=candidate_info,
            resume_text=resume_text,
            resume_file_path=file_path,
            job_id=str(job_id)
        )

        return CandidateResponse.from_orm(candidate)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create candidate: {str(e)}"
        )


@router.get("/", response_model=List[CandidateResponse])
async def list_candidates(
    skip: int = 0,
    limit: int = 100,
    stage: Optional[str] = None,
    job_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """List candidates with filtering options"""
    candidate_service = CandidateService(db)
    candidates = await candidate_service.list_candidates(
        skip=skip,
        limit=limit,
        stage=stage,
        job_id=str(job_id) if job_id else None
    )
    return [CandidateResponse.from_orm(candidate) for candidate in candidates]


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(candidate_id: UUID, db: Session = Depends(get_db)):
    """Get candidate by ID"""
    candidate_service = CandidateService(db)
    candidate = await candidate_service.get_candidate(str(candidate_id))

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return CandidateResponse.from_orm(candidate)


@router.post("/{candidate_id}/evaluate")
async def evaluate_candidate(
    candidate_id: UUID,
    db: Session = Depends(get_db)
):
    """Trigger resume evaluation for a candidate"""
    try:
        # Get candidate
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Create and run evaluation agent
        config = ResumeEvaluatorConfig(name=f"evaluator_{candidate_id}")
        evaluator = ResumeEvaluatorAgent(config, db)

        # Create initial state
        from app.agents.base_agent import AgentState
        initial_state = AgentState(
            workflow_id=str(candidate.workflow_id),
            input_data={
                "candidate_id": str(candidate_id),
                "job_id": str(candidate.job_id)
            }
        )

        # Execute evaluation
        result = await evaluator.execute(initial_state)

        if result.errors:
            raise HTTPException(
                status_code=400,
                detail=f"Evaluation failed: {', '.join(result.errors)}"
            )

        return {
            "status": "completed",
            "message": "Candidate evaluation completed successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}"
        )


@router.get("/{candidate_id}/evaluations", response_model=List[CandidateEvaluationResponse])
async def get_candidate_evaluations(candidate_id: UUID, db: Session = Depends(get_db)):
    """Get all evaluations for a candidate"""
    candidate_service = CandidateService(db)
    evaluations = await candidate_service.get_candidate_evaluations(str(candidate_id))
    return [CandidateEvaluationResponse.from_orm(eval) for eval in evaluations]


@router.put("/{candidate_id}/stage")
async def update_candidate_stage(
    candidate_id: UUID,
    new_stage: str,
    db: Session = Depends(get_db)
):
    """Update candidate stage (for human decisions)"""
    candidate_service = CandidateService(db)
    candidate = await candidate_service.update_candidate_stage(str(candidate_id), new_stage)
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    return {"status": "updated", "new_stage": new_stage}


@router.get("/{candidate_id}/status")
async def get_candidate_status(candidate_id: UUID, db: Session = Depends(get_db)):
    """Get comprehensive candidate status including workflow progress"""
    candidate_service = CandidateService(db)
    status = await candidate_service.get_comprehensive_status(str(candidate_id))
    
    if not status:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    return status
