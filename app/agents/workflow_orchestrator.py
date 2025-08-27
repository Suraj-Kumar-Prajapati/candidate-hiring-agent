from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from datetime import datetime

from app.agents.base_agent import AgentState, AgentConfig, MultiStepAgent
from app.agents.resume_evaluator import ResumeEvaluatorAgent, ResumeEvaluatorConfig
from app.agents.interview_scheduler import InterviewSchedulerAgent, InterviewSchedulerConfig
from app.agents.email_agent import EmailAgent, EmailAgentConfig
from app.services.workflow_service import WorkflowService
from app.api.websockets.workflow_updates import notify_workflow_stage_change


class WorkflowOrchestratorConfig(AgentConfig):
    """Configuration for workflow orchestrator"""
    job_id: str
    workflow_type: str = "hiring_workflow"
    enable_human_decisions: bool = True
    auto_schedule_interviews: bool = True
    send_automated_emails: bool = True
    max_parallel_candidates: int = 5


class WorkflowOrchestratorState(AgentState):
    """State for workflow orchestrator"""
    job_id: str = ""
    candidates: List[Dict[str, Any]] = []
    current_batch: List[str] = []  # Current batch of candidate IDs being processed
    
    # Stage tracking
    resume_evaluation_complete: bool = False
    human_decisions_complete: bool = False
    interviews_scheduled: bool = False
    emails_sent: bool = False
    
    # Results
    evaluation_results: Dict[str, Any] = {}
    scheduling_results: Dict[str, Any] = {}
    email_results: Dict[str, Any] = {}
    
    # Human intervention
    pending_human_decisions: List[Dict[str, Any]] = []
    human_decision_responses: List[Dict[str, Any]] = []


class WorkflowOrchestrator(MultiStepAgent):
    """Orchestrator agent that manages the complete hiring workflow"""
    
    def __init__(self, config: WorkflowOrchestratorConfig, db):
        super().__init__(config, db)
        self.config: WorkflowOrchestratorConfig = config
        self.workflow_service = WorkflowService(db)
        
    def get_execution_steps(self) -> List[str]:
        return [
            "initialize_workflow",
            "load_candidates",
            "batch_process_candidates",
            "evaluate_resumes",
            "check_human_decisions",
            "wait_for_human_input",
            "process_approved_candidates",
            "schedule_interviews",
            "send_notifications",
            "finalize_workflow"
        ]
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the complete workflow orchestration"""
        orchestrator_state = WorkflowOrchestratorState(**state.dict())
        
        # Execute workflow steps
        for step in self.get_execution_steps():
            orchestrator_state = await self.execute_step(step, orchestrator_state)
            
            # Check if we need to pause for human input
            if step == "check_human_decisions" and orchestrator_state.pending_human_decisions:
                await self.log_execution(orchestrator_state, step, "Pausing workflow for human decisions")
                orchestrator_state.current_step = "waiting_for_human_input"
                break
                
            if orchestrator_state.errors:
                break
        
        return orchestrator_state
    
    def create_workflow_graph(self) -> StateGraph:
        """Create LangGraph workflow for orchestration"""
        graph = StateGraph(dict)
        
        # Add nodes
        steps = self.get_execution_steps()
        for step in steps:
            graph.add_node(step, self._create_step_node(step))
        
        # Create conditional flow
        graph.add_edge(START, "initialize_workflow")
        graph.add_edge("initialize_workflow", "load_candidates")
        graph.add_edge("load_candidates", "batch_process_candidates")
        graph.add_edge("batch_process_candidates", "evaluate_resumes")
        graph.add_edge("evaluate_resumes", "check_human_decisions")
        
        # Conditional edge for human decisions
        graph.add_conditional_edges(
            "check_human_decisions",
            lambda state: "human_required" if state.get("pending_human_decisions") else "proceed",
            {
                "human_required": "wait_for_human_input",
                "proceed": "process_approved_candidates"
            }
        )
        
        graph.add_edge("wait_for_human_input", "process_approved_candidates")
        graph.add_edge("process_approved_candidates", "schedule_interviews")
        graph.add_edge("schedule_interviews", "send_notifications")
        graph.add_edge("send_notifications", "finalize_workflow")
        graph.add_edge("finalize_workflow", END)
        
        return graph.compile()
    
    def _create_step_node(self, step_name: str):
        """Create a node function for orchestrator steps"""
        async def node_function(state: dict) -> dict:
            orchestrator_state = WorkflowOrchestratorState(**state)
            result_state = await self.execute_step(step_name, orchestrator_state)
            return result_state.dict()
        return node_function
    
    async def execute_initialize_workflow(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Initialize the workflow"""
        try:
            # Create or get workflow record
            workflow = await self.workflow_service.get_workflow(state.workflow_id)
            if not workflow:
                from app.schemas.workflow import WorkflowCreate
                workflow_data = WorkflowCreate(
                    job_id=state.job_id,
                    name=f"Hiring Workflow - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    workflow_type=self.config.workflow_type
                )
                workflow = await self.workflow_service.create_workflow(workflow_data)
                state.workflow_id = str(workflow.id)
            
            # Update workflow status
            await self.workflow_service.update_workflow_status(
                state.workflow_id, "running", "initialized", 10
            )
            
            # Notify via WebSocket
            await notify_workflow_stage_change(
                state.workflow_id, 
                "initialized",
                {"message": "Workflow initialized successfully"}
            )
            
            await self.log_execution(state, "initialize_workflow", "Workflow initialized")
            return state
            
        except Exception as e:
            state.errors.append(f"Workflow initialization failed: {str(e)}")
            return state
    
    async def execute_load_candidates(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Load candidates for processing"""
        try:
            from app.services.candidate_service import CandidateService
            candidate_service = CandidateService(self.db)
            
            # Get candidates for this job who are in initial stage
            candidates = await candidate_service.list_candidates(
                job_id=state.job_id,
                stage="resume_received"
            )
            
            state.candidates = [
                {
                    "id": str(candidate.id),
                    "name": candidate.name,
                    "email": candidate.email,
                    "stage": candidate.current_stage
                } for candidate in candidates
            ]
            
            await self.log_execution(
                state, "load_candidates", 
                f"Loaded {len(state.candidates)} candidates for processing"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to load candidates: {str(e)}")
            return state
    
    async def execute_batch_process_candidates(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Organize candidates into processing batches"""
        try:
            # Split candidates into batches for parallel processing
            candidate_ids = [c["id"] for c in state.candidates]
            batch_size = min(self.config.max_parallel_candidates, len(candidate_ids))
            
            # For now, process first batch
            state.current_batch = candidate_ids[:batch_size]
            
            await self.log_execution(
                state, "batch_process_candidates", 
                f"Created batch with {len(state.current_batch)} candidates"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Batch processing failed: {str(e)}")
            return state
    
    async def execute_evaluate_resumes(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Evaluate resumes for current batch"""
        try:
            evaluation_tasks = []
            
            for candidate_id in state.current_batch:
                # Create resume evaluator for each candidate
                config = ResumeEvaluatorConfig(
                    name=f"evaluator_{candidate_id}",
                    enable_logging=True
                )
                evaluator = ResumeEvaluatorAgent(config, self.db)
                
                # Create evaluation state
                eval_state = AgentState(
                    workflow_id=state.workflow_id,
                    input_data={
                        "candidate_id": candidate_id,
                        "job_id": state.job_id
                    }
                )
                
                # Create evaluation task
                task = evaluator.execute(eval_state)
                evaluation_tasks.append((candidate_id, task))
            
            # Execute evaluations in parallel
            results = {}
            for candidate_id, task in evaluation_tasks:
                try:
                    result = await task
                    results[candidate_id] = {
                        "success": len(result.errors) == 0,
                        "errors": result.errors,
                        "output": result.output_data
                    }
                except Exception as e:
                    results[candidate_id] = {
                        "success": False,
                        "errors": [f"Evaluation failed: {str(e)}"],
                        "output": {}
                    }
            
            state.evaluation_results = results
            state.resume_evaluation_complete = True
            
            # Update workflow progress
            await self.workflow_service.update_workflow_status(
                state.workflow_id, "running", "resume_evaluation_complete", 40
            )
            
            await self.log_execution(
                state, "evaluate_resumes", 
                f"Completed resume evaluation for {len(results)} candidates"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Resume evaluation failed: {str(e)}")
            return state
    
    async def execute_check_human_decisions(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Check if human decisions are required"""
        try:
            if not self.config.enable_human_decisions:
                return state
            
            # Check evaluation results to determine which candidates need human review
            pending_decisions = []
            
            for candidate_id, result in state.evaluation_results.items():
                if result["success"]:
                    output = result["output"]
                    recommendation = output.get("recommendation", "review_required")
                    
                    if recommendation in ["reject", "review_required"]:
                        candidate_info = next(
                            (c for c in state.candidates if c["id"] == candidate_id), 
                            {"id": candidate_id, "name": "Unknown"}
                        )
                        
                        pending_decisions.append({
                            "candidate_id": candidate_id,
                            "candidate_name": candidate_info["name"],
                            "decision_type": "approve_for_interview" if recommendation == "review_required" else "reject_candidate",
                            "evaluation_summary": output.get("summary", "No summary available"),
                            "recommendation": recommendation,
                            "scores": {
                                "overall": output.get("overall_score", 0),
                                "match_percentage": output.get("match_percentage", 0)
                            }
                        })
            
            state.pending_human_decisions = pending_decisions
            
            if pending_decisions:
                # Update workflow to show human decision required
                await self.workflow_service.update_workflow_status(
                    state.workflow_id, "paused", "awaiting_human_decisions", 50
                )
                
                # Send notification about pending decisions
                from app.api.websockets.workflow_updates import notify_human_decision_required
                await notify_human_decision_required(
                    state.workflow_id,
                    "candidate_approval",
                    pending_decisions
                )
            
            await self.log_execution(
                state, "check_human_decisions", 
                f"Found {len(pending_decisions)} candidates requiring human decisions"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Human decision check failed: {str(e)}")
            return state
    
    async def execute_wait_for_human_input(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Wait for human input (this creates a breakpoint in the workflow)"""
        try:
            # This step pauses the workflow until human input is received
            # The workflow will resume when process_human_decision is called
            await self.log_execution(
                state, "wait_for_human_input", 
                f"Waiting for human decisions on {len(state.pending_human_decisions)} candidates"
            )
            
            # In practice, this would be handled by the workflow engine's interrupt mechanism
            return state
            
        except Exception as e:
            state.errors.append(f"Human input wait failed: {str(e)}")
            return state
    
    async def execute_process_approved_candidates(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Process candidates after human decisions"""
        try:
            approved_candidates = []
            rejected_candidates = []
            
            # If no human decisions were required, approve based on evaluation
            if not state.pending_human_decisions:
                for candidate_id, result in state.evaluation_results.items():
                    if result["success"]:
                        recommendation = result["output"].get("recommendation", "review_required")
                        if recommendation in ["interview", "fast_track"]:
                            approved_candidates.append(candidate_id)
                        else:
                            rejected_candidates.append(candidate_id)
            else:
                # Process human decision responses
                for decision in state.human_decision_responses:
                    if decision.get("decision") == "approve":
                        approved_candidates.append(decision["candidate_id"])
                    else:
                        rejected_candidates.append(decision["candidate_id"])
            
            # Update candidate stages
            from app.services.candidate_service import CandidateService
            candidate_service = CandidateService(self.db)
            
            for candidate_id in approved_candidates:
                await candidate_service.update_candidate_stage(candidate_id, "approved_for_interview")
            
            for candidate_id in rejected_candidates:
                await candidate_service.update_candidate_stage(candidate_id, "rejected")
            
            state.output_data["approved_candidates"] = approved_candidates
            state.output_data["rejected_candidates"] = rejected_candidates
            
            await self.log_execution(
                state, "process_approved_candidates", 
                f"Approved: {len(approved_candidates)}, Rejected: {len(rejected_candidates)}"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Candidate processing failed: {str(e)}")
            return state
    
    async def execute_schedule_interviews(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Schedule interviews for approved candidates"""
        try:
            if not self.config.auto_schedule_interviews:
                return state
            
            approved_candidates = state.output_data.get("approved_candidates", [])
            if not approved_candidates:
                return state
            
            # Create interview scheduler
            scheduler_config = InterviewSchedulerConfig(
                name="interview_scheduler",
                job_id=state.job_id
            )
            scheduler = InterviewSchedulerAgent(scheduler_config, self.db)
            
            # Schedule interviews for approved candidates
            scheduler_state = AgentState(
                workflow_id=state.workflow_id,
                input_data={
                    "candidate_ids": approved_candidates,
                    "job_id": state.job_id
                }
            )
            
            result = await scheduler.execute(scheduler_state)
            
            if result.errors:
                state.errors.extend(result.errors)
            else:
                state.scheduling_results = result.output_data
                state.interviews_scheduled = True
            
            # Update workflow progress
            await self.workflow_service.update_workflow_status(
                state.workflow_id, "running", "interviews_scheduled", 80
            )
            
            await self.log_execution(
                state, "schedule_interviews", 
                f"Scheduled interviews for {len(approved_candidates)} candidates"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Interview scheduling failed: {str(e)}")
            return state
    
    async def execute_send_notifications(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Send email notifications to candidates and interviewers"""
        try:
            if not self.config.send_automated_emails:
                return state
            
            # Create email agent
            email_config = EmailAgentConfig(
                name="email_agent",
                workflow_id=state.workflow_id
            )
            email_agent = EmailAgent(email_config, self.db)
            
            # Prepare email data
            email_data = {
                "approved_candidates": state.output_data.get("approved_candidates", []),
                "rejected_candidates": state.output_data.get("rejected_candidates", []),
                "scheduled_interviews": state.scheduling_results.get("scheduled_interviews", []),
                "job_id": state.job_id
            }
            
            email_state = AgentState(
                workflow_id=state.workflow_id,
                input_data=email_data
            )
            
            result = await email_agent.execute(email_state)
            
            if result.errors:
                state.errors.extend(result.errors)
            else:
                state.email_results = result.output_data
                state.emails_sent = True
            
            await self.log_execution(
                state, "send_notifications", 
                f"Sent notifications for workflow {state.workflow_id}"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Email notifications failed: {str(e)}")
            return state
    
    async def execute_finalize_workflow(self, state: WorkflowOrchestratorState) -> WorkflowOrchestratorState:
        """Finalize the workflow"""
        try:
            # Update workflow to completed
            await self.workflow_service.update_workflow_status(
                state.workflow_id, "completed", "finalized", 100
            )
            
            # Generate final summary
            summary = {
                "total_candidates": len(state.candidates),
                "approved_candidates": len(state.output_data.get("approved_candidates", [])),
                "rejected_candidates": len(state.output_data.get("rejected_candidates", [])),
                "interviews_scheduled": len(state.scheduling_results.get("scheduled_interviews", [])),
                "emails_sent": len(state.email_results.get("emails_sent", [])),
                "execution_time": (datetime.now() - state.created_at).total_seconds(),
                "success": len(state.errors) == 0
            }
            
            state.output_data["workflow_summary"] = summary
            
            # Send final notification
            await notify_workflow_stage_change(
                state.workflow_id,
                "completed", 
                {"summary": summary}
            )
            
            await self.log_execution(
                state, "finalize_workflow", 
                f"Workflow completed successfully. Summary: {summary}"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Workflow finalization failed: {str(e)}")
            return state
    
    async def handle_human_decision(self, decision_data: Dict[str, Any]) -> bool:
        """Handle human decision input and resume workflow"""
        try:
            # This would be called when human input is received
            # It would update the workflow state and resume execution
            
            # Add decision to workflow
            await self.workflow_service.process_human_decision(
                self.config.workflow_id,
                decision_data
            )
            
            # Resume workflow execution
            # This would trigger the workflow to continue from where it was paused
            return True
            
        except Exception as e:
            await self.log_execution(
                None, "handle_human_decision", 
                f"Failed to handle human decision: {str(e)}", "ERROR"
            )
            return False