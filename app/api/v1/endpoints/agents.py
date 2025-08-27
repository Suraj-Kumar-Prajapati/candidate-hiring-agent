from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.agents.base_agent import agent_registry, AgentState
from app.agents.resume_evaluator import ResumeEvaluatorConfig
from app.agents.workflow_orchestrator import WorkflowOrchestratorConfig

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/")
async def list_available_agents():
    """List all available agent types"""
    return {
        "available_agents": agent_registry.list_agents(),
        "registered_instances": len(agent_registry._instances)
    }


@router.post("/resume-evaluator/execute")
async def execute_resume_evaluator(
    candidate_id: UUID,
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Execute resume evaluator agent for a candidate"""
    try:
        config = ResumeEvaluatorConfig(
            name=f"evaluator_{candidate_id}",
            enable_logging=True
        )
        
        agent = agent_registry.create_agent("resume_evaluator", config, db)
        
        initial_state = AgentState(
            workflow_id=str(UUID()),
            input_data={
                "candidate_id": str(candidate_id),
                "job_id": str(job_id)
            }
        )
        
        # Execute in background
        background_tasks.add_task(execute_agent_background, agent, initial_state)
        
        return {"status": "started", "agent_id": config.name}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start agent: {str(e)}")


@router.post("/workflow-orchestrator/execute")
async def execute_workflow_orchestrator(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Execute workflow orchestrator for a job"""
    try:
        config = WorkflowOrchestratorConfig(
            name=f"orchestrator_{job_id}",
            job_id=str(job_id),
            enable_logging=True
        )
        
        # This would create the workflow orchestrator
        # For now, return success
        return {"status": "started", "workflow_id": str(UUID())}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start orchestrator: {str(e)}")


@router.get("/metrics")
async def get_agent_metrics():
    """Get metrics for all agents"""
    metrics = {}
    for agent_name, agent_instance in agent_registry._instances.items():
        metrics[agent_name] = agent_instance.get_metrics()
    
    return metrics


async def execute_agent_background(agent, initial_state):
    """Execute agent in background"""
    try:
        result = await agent.execute(initial_state)
        # Handle result or store in database
        print(f"Agent execution completed: {result.workflow_id}")
    except Exception as e:
        print(f"Agent execution failed: {str(e)}")
