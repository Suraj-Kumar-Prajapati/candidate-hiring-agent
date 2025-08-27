from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from app.models.workflow import Workflow, WorkflowLog
from app.schemas.workflow import WorkflowCreate, HumanDecisionRequest
from app.core.exceptions import WorkflowNotFoundError, ValidationError


class WorkflowService:
    """Service class for workflow operations"""

    def __init__(self, db: Session):
        self.db = db

    async def create_workflow(self, workflow_data: WorkflowCreate) -> Workflow:
        """Create a new workflow"""
        try:
            workflow = Workflow(
                **workflow_data.dict(),
                current_stage="initiated",
                status="running",
                started_at=datetime.now(),
                last_activity_at=datetime.now()
            )
            
            self.db.add(workflow)
            self.db.commit()
            self.db.refresh(workflow)
            
            return workflow
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to create workflow: {str(e)}")
    
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        try:
            return self.db.query(Workflow)\
                .options(
                    joinedload(Workflow.candidates),
                    joinedload(Workflow.job),
                    joinedload(Workflow.workflow_logs)
                )\
                .filter(Workflow.id == UUID(workflow_id))\
                .first()
        except Exception as e:
            raise ValidationError(f"Failed to get workflow: {str(e)}")
    
    async def update_workflow_status(
        self, 
        workflow_id: str, 
        new_status: str, 
        new_stage: Optional[str] = None,
        progress_percentage: Optional[int] = None
    ) -> Optional[Workflow]:
        """Update workflow status and stage"""
        try:
            workflow = await self.get_workflow(workflow_id)
            if not workflow:
                raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
            
            workflow.status = new_status
            workflow.last_activity_at = datetime.now()
            
            if new_stage:
                workflow.current_stage = new_stage
            
            if progress_percentage is not None:
                workflow.progress_percentage = progress_percentage
            
            if new_status == "completed":
                workflow.completed_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(workflow)
            
            return workflow
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to update workflow status: {str(e)}")
    
    async def log_workflow_activity(
        self, 
        workflow_id: str, 
        level: str, 
        message: str, 
        agent_name: Optional[str] = None,
        node_name: Optional[str] = None,
        candidate_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None
    ) -> WorkflowLog:
        """Log workflow activity"""
        try:
            log_entry = WorkflowLog(
                workflow_id=UUID(workflow_id),
                log_level=level,
                message=message,
                agent_name=agent_name,
                node_name=node_name,
                candidate_id=UUID(candidate_id) if candidate_id else None,
                details=details or {},
                execution_time_ms=execution_time_ms
            )
            
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            
            return log_entry
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to log workflow activity: {str(e)}")
    
    async def process_human_decision(
        self, 
        workflow_id: str, 
        decision_data: HumanDecisionRequest
    ) -> Dict[str, Any]:
        """Process human decision input"""
        try:
            workflow = await self.get_workflow(workflow_id)
            if not workflow:
                raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
            
            # Add decision to history
            decision_record = {
                "timestamp": datetime.now().isoformat(),
                "decision_type": decision_data.decision_type,
                "candidate_id": str(decision_data.candidate_id),
                "decision": decision_data.decision,
                "comments": decision_data.comments,
                "additional_data": decision_data.additional_data
            }
            
            # Update workflow state
            history = workflow.human_decision_history or []
            history.append(decision_record)
            workflow.human_decision_history = history
            
            # Remove from pending decisions
            pending = workflow.human_decisions_pending or []
            pending = [d for d in pending if d.get("candidate_id") != str(decision_data.candidate_id)]
            workflow.human_decisions_pending = pending
            
            # Update candidate stage based on decision
            if decision_data.decision == "approve":
                new_stage = "approved_for_interview"
            elif decision_data.decision == "reject":
                new_stage = "rejected"
            else:
                new_stage = "on_hold"
            
            # Update candidate
            from app.services.candidate_service import CandidateService
            candidate_service = CandidateService(self.db)
            await candidate_service.update_candidate_stage(
                str(decision_data.candidate_id), 
                new_stage
            )
            
            # Log the decision
            await self.log_workflow_activity(
                workflow_id,
                "INFO",
                f"Human decision processed: {decision_data.decision} for candidate {decision_data.candidate_id}",
                details=decision_record
            )
            
            self.db.commit()
            
            return {"status": "processed", "decision": decision_record}
            
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to process human decision: {str(e)}")
    
    async def get_pending_decisions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get pending human decisions for workflow"""
        try:
            workflow = await self.get_workflow(workflow_id)
            if not workflow:
                return []
            
            return workflow.human_decisions_pending or []
            
        except Exception as e:
            raise ValidationError(f"Failed to get pending decisions: {str(e)}")
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a workflow"""
        try:
            result = await self.update_workflow_status(workflow_id, "paused")
            return result is not None
        except Exception as e:
            raise ValidationError(f"Failed to pause workflow: {str(e)}")
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        try:
            result = await self.update_workflow_status(workflow_id, "running")
            return result is not None
        except Exception as e:
            raise ValidationError(f"Failed to resume workflow: {str(e)}")
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive workflow status"""
        try:
            workflow = await self.get_workflow(workflow_id)
            if not workflow:
                return None
            
            # Get recent logs
            recent_logs = self.db.query(WorkflowLog)\
                .filter(WorkflowLog.workflow_id == UUID(workflow_id))\
                .order_by(WorkflowLog.created_at.desc())\
                .limit(10)\
                .all()
            
            # Calculate performance metrics
            total_logs = self.db.query(WorkflowLog)\
                .filter(WorkflowLog.workflow_id == UUID(workflow_id))\
                .count()
            
            error_logs = self.db.query(WorkflowLog)\
                .filter(WorkflowLog.workflow_id == UUID(workflow_id))\
                .filter(WorkflowLog.log_level == "ERROR")\
                .count()
            
            return {
                "workflow": workflow,
                "candidates": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "stage": c.current_stage,
                        "score": c.overall_score
                    } for c in workflow.candidates
                ],
                "pending_decisions": workflow.human_decisions_pending or [],
                "recent_activities": [
                    {
                        "timestamp": log.created_at.isoformat(),
                        "level": log.log_level,
                        "agent": log.agent_name,
                        "message": log.message
                    } for log in recent_logs
                ],
                "performance_metrics": {
                    "total_logs": total_logs,
                    "error_count": error_logs,
                    "success_rate": ((total_logs - error_logs) / total_logs * 100) if total_logs > 0 else 0,
                    "execution_time": (
                        (workflow.completed_at or datetime.now()) - workflow.started_at
                    ).total_seconds() if workflow.started_at else 0
                }
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to get workflow status: {str(e)}")

    async def list_workflows(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        status: Optional[str] = None
    ) -> List[Workflow]:
        """List workflows with filtering"""
        try:
            query = self.db.query(Workflow)
            
            if status:
                query = query.filter(Workflow.status == status)
            
            return query.filter(Workflow.is_active == True)\
                .order_by(Workflow.created_at.desc())\
                .offset(skip)\
                .limit(limit)\
                .all()
                
        except Exception as e:
            raise ValidationError(f"Failed to list workflows: {str(e)}")
