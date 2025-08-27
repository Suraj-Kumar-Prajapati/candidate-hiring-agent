from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.schemas.workflow import (
    WorkflowResponse, WorkflowCreate, HumanDecisionRequest
)
from app.services.workflow_service import WorkflowService


router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/start-hiring-process", response_model=WorkflowResponse)
async def start_hiring_workflow(
    workflow_data: WorkflowCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start a complete hiring workflow"""
    try:
        workflow_service = WorkflowService(db)

        # Create workflow
        workflow = await workflow_service.create_workflow(workflow_data)
        
        # Start workflow execution in background
        background_tasks.add_task(
            execute_workflow_background,
            workflow.id,
            workflow_data.dict()
        )
        
        return WorkflowResponse.from_orm(workflow)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start workflow: {str(e)}")


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    """Get workflow details"""
    workflow_service = WorkflowService(db)
    workflow = await workflow_service.get_workflow(str(workflow_id))
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return WorkflowResponse.from_orm(workflow)


@router.get("/{workflow_id}/status")
async def get_workflow_status(workflow_id: UUID, db: Session = Depends(get_db)):
    """Get current workflow status and progress"""
    workflow_service = WorkflowService(db)
    status = await workflow_service.get_workflow_status(str(workflow_id))
    
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return status


@router.post("/{workflow_id}/human-decision")
async def submit_human_decision(
    workflow_id: UUID,
    decision_data: HumanDecisionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Submit human decision to resume paused workflow"""
    try:
        workflow_service = WorkflowService(db)
        
        # Process human decision
        result = await workflow_service.process_human_decision(
            str(workflow_id),
            decision_data
        )
        
        # Resume workflow in background
        background_tasks.add_task(
            resume_workflow_background,
            workflow_id
        )
        
        return {"status": "decision_processed", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process decision: {str(e)}")


@router.get("/{workflow_id}/pending-decisions")
async def get_pending_decisions(workflow_id: UUID, db: Session = Depends(get_db)):
    """Get all pending human decisions for a workflow"""
    workflow_service = WorkflowService(db)
    decisions = await workflow_service.get_pending_decisions(str(workflow_id))
    return decisions


@router.post("/{workflow_id}/pause")
async def pause_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    """Pause a running workflow"""
    workflow_service = WorkflowService(db)
    result = await workflow_service.pause_workflow(str(workflow_id))
    return {"status": "paused" if result else "failed"}


@router.post("/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Resume a paused workflow"""
    background_tasks.add_task(resume_workflow_background, workflow_id)
    return {"status": "resuming"}


@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db)
):
    """List workflows with filtering"""
    workflow_service = WorkflowService(db)
    workflows = await workflow_service.list_workflows(skip=skip, limit=limit, status=status)
    return [WorkflowResponse.from_orm(wf) for wf in workflows]


# Background task functions
async def execute_workflow_background(workflow_id: UUID, workflow_data: Dict[str, Any]):
    """Execute workflow in background"""
    # This would create and run the WorkflowOrchestrator
    pass


async def resume_workflow_background(workflow_id: UUID):
    """Resume workflow execution in background"""
    # This would resume the paused workflow
    pass
