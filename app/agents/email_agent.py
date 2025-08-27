from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END

from app.agents.base_agent import (
    AgentState,
    AgentConfig,
    MultiStepAgent
)
from app.services.email_service import EmailService
from app.services.candidate_service import CandidateService
from app.services.job_service import JobService
from app.utils.email_utils import (
    create_interview_invitation_template,
    create_rejection_email_template,
    create_interviewer_notification_template,
    create_hr_summary_email_template
)


class EmailAgentConfig(AgentConfig):
    """Configuration for email agent"""
    workflow_id: str
    send_interview_invitations: bool = True
    send_rejection_emails: bool = True
    send_interviewer_notifications: bool = True
    send_hr_summary: bool = True
    batch_size: int = 10  # Number of emails to send in parallel


class EmailAgentState(AgentState):
    """State for email agent"""
    approved_candidates: List[str] = []
    rejected_candidates: List[str] = []
    scheduled_interviews: List[Dict[str, Any]] = []
    job_id: str = ""

    # Email results
    emails_sent: List[Dict[str, Any]] = []
    email_failures: List[Dict[str, Any]] = []

    # Templates and data
    candidate_data: Dict[str, Any] = {}
    job_data: Dict[str, Any] = {}


class EmailAgent(MultiStepAgent):
    """Agent responsible for sending emails"""

    def __init__(self, config: EmailAgentConfig, db):
        super().__init__(config, db)
        self.config: EmailAgentConfig = config
        self.email_service = EmailService(db)
        self.candidate_service = CandidateService(db)
        self.job_service = JobService(db)

    def get_execution_steps(self) -> List[str]:
        return [
            "load_email_data",
            "send_interview_invitations", 
            "send_rejection_emails",
            "send_interviewer_notifications",
            "send_hr_summary",
            "compile_email_results"
        ]

    async def execute(self, state: AgentState) -> AgentState:
        """Execute email sending workflow"""
        email_state = EmailAgentState(**state.model_dump())

        for step in self.get_execution_steps():
            email_state = await self.execute_step(step, email_state)
            if email_state.errors:
                break

        return email_state

    def create_workflow_graph(self) -> StateGraph:
        """Create LangGraph workflow for email sending"""
        graph = StateGraph(dict)

        steps = self.get_execution_steps()
        for step in steps:
            graph.add_node(step, self._create_step_node(step))

        # Linear workflow
        graph.add_edge(START, steps[0])
        for i in range(len(steps) - 1):
            graph.add_edge(steps[i], steps[i + 1])
        graph.add_edge(steps[-1], END)

        return graph.compile()

    def _create_step_node(self, step_name: str):
        """Create node function for email steps"""
        async def node_function(state: dict) -> dict:
            email_state = EmailAgentState(**state)
            result_state = await self.execute_step(step_name, email_state)
            return result_state.dict()
        return node_function

    async def execute_load_email_data(
        self, state: EmailAgentState
    ) -> EmailAgentState:
        """Load all required data for email sending"""
        try:
            # Load job data
            job = await self.job_service.get_job(state.job_id)
            if job:
                state.job_data = {
                    "title": job.title,
                    "description": job.description,
                    "technologies_required": job.technologies_required
                }

            # Load candidate data
            all_candidate_ids = list(set(
                state.approved_candidates + 
                state.rejected_candidates + 
                [interview["candidate_id"] for interview in state.scheduled_interviews]
            ))

            for candidate_id in all_candidate_ids:
                candidate = await self.candidate_service.get_candidate(candidate_id)
                if candidate:
                    state.candidate_data[candidate_id] = {
                        "name": candidate.name,
                        "email": candidate.email,
                        "experience_years": candidate.experience_years,
                        "technologies": candidate.technologies,
                        "current_stage": candidate.current_stage
                    }

            await self.log_execution(
                state, "load_email_data", 
                f"Loaded data for {len(all_candidate_ids)} candidates and job {state.job_id}"
            )

            return state

        except Exception as e:
            state.errors.append(f"Failed to load email data: {str(e)}")
            return state

    async def execute_send_interview_invitations(
        self, state: EmailAgentState
    ) -> EmailAgentState:
        """Send interview invitation emails"""
        try:
            if not self.config.send_interview_invitations:
                return state

            for interview in state.scheduled_interviews:
                candidate_id = interview["candidate_id"]
                candidate_info = state.candidate_data.get(candidate_id)

                if not candidate_info or not candidate_info.get("email"):
                    state.email_failures.append({
                        "candidate_id": candidate_id,
                        "type": "interview_invitation",
                        "error": "No email address found"
                    })
                    continue

                # Create mock objects for template (in practice, use actual objects)
                candidate_obj = type('Candidate', (), candidate_info)()
                job_obj = type('Job', (), state.job_data)()
                interview_obj = type('Interview', (), {
                    "scheduled_time": interview["scheduled_time"],
                    "duration_minutes": interview["duration_minutes"],
                    "interview_type": interview["interview_type"],
                    "meeting_link": interview.get("meeting_link", "")
                })()

                # Generate email template
                email_template = create_interview_invitation_template(
                    candidate_obj, interview_obj, job_obj
                )

                # Send email
                result = await self.email_service.send_email(
                    to_email=candidate_info["email"],
                    subject=email_template["subject"],
                    body=email_template["body"],
                    to_name=candidate_info["name"],
                    email_type="interview_invitation",
                    candidate_id=candidate_id,
                    workflow_id=state.workflow_id
                )

                if result["success"]:
                    state.emails_sent.append({
                        "candidate_id": candidate_id,
                        "type": "interview_invitation",
                        "recipient": candidate_info["email"],
                        "subject": email_template["subject"]
                    })
                else:
                    state.email_failures.append({
                        "candidate_id": candidate_id,
                        "type": "interview_invitation",
                        "error": result["error"]
                    })

            await self.log_execution(
                state, "send_interview_invitations", 
                f"Sent {len([e for e in state.emails_sent if e['type'] == 'interview_invitation'])} interview invitations"
            )

            return state

        except Exception as e:
            state.errors.append(f"Failed to send interview invitations: {str(e)}")
            return state

    async def execute_send_rejection_emails(self, state: EmailAgentState) -> EmailAgentState:
        """Send rejection emails to rejected candidates"""
        try:
            if not self.config.send_rejection_emails:
                return state

            for candidate_id in state.rejected_candidates:
                candidate_info = state.candidate_data.get(candidate_id)

                if not candidate_info or not candidate_info.get("email"):
                    state.email_failures.append({
                        "candidate_id": candidate_id,
                        "type": "rejection",
                        "error": "No email address found"
                    })
                    continue

                # Create mock objects for template
                candidate_obj = type('Candidate', (), candidate_info)()
                job_obj = type('Job', (), state.job_data)()
 
                # Generate email template
                email_template = create_rejection_email_template(candidate_obj, job_obj)
  
                # Send email
                result = await self.email_service.send_email(
                    to_email=candidate_info["email"],
                    subject=email_template["subject"],
                    body=email_template["body"],
                    to_name=candidate_info["name"],
                    email_type="rejection",
                    candidate_id=candidate_id,
                    workflow_id=state.workflow_id
                )
                
                if result["success"]:
                    state.emails_sent.append({
                        "candidate_id": candidate_id,
                        "type": "rejection",
                        "recipient": candidate_info["email"],
                        "subject": email_template["subject"]
                    })
                else:
                    state.email_failures.append({
                        "candidate_id": candidate_id,
                        "type": "rejection",
                        "error": result["error"]
                    })
            
            await self.log_execution(
                state, "send_rejection_emails", 
                f"Sent {len([e for e in state.emails_sent if e['type'] == 'rejection'])} rejection emails"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to send rejection emails: {str(e)}")
            return state
    
    async def execute_send_interviewer_notifications(self, state: EmailAgentState) -> EmailAgentState:
        """Send notification emails to interviewers"""
        try:
            if not self.config.send_interviewer_notifications:
                return state
            
            for interview in state.scheduled_interviews:
                candidate_id = interview["candidate_id"]
                candidate_info = state.candidate_data.get(candidate_id)
                interviewer_email = interview.get("interviewer_email")
                
                if not interviewer_email or not candidate_info:
                    state.email_failures.append({
                        "interview_id": interview.get("interview_id"),
                        "type": "interviewer_notification",
                        "error": "Missing interviewer email or candidate info"
                    })
                    continue
                
                # Create mock objects for template
                candidate_obj = type('Candidate', (), candidate_info)()
                job_obj = type('Job', (), state.job_data)()
                interview_obj = type('Interview', (), interview)()
                
                # Generate email template
                email_template = create_interviewer_notification_template(
                    candidate_obj, interview_obj, job_obj
                )
                
                # Send email
                result = await self.email_service.send_email(
                    to_email=interviewer_email,
                    subject=email_template["subject"],
                    body=email_template["body"],
                    to_name=interview.get("interviewer_name", "Interviewer"),
                    email_type="interviewer_notification",
                    candidate_id=candidate_id,
                    workflow_id=state.workflow_id
                )
                
                if result["success"]:
                    state.emails_sent.append({
                        "interview_id": interview.get("interview_id"),
                        "type": "interviewer_notification",
                        "recipient": interviewer_email,
                        "subject": email_template["subject"]
                    })
                else:
                    state.email_failures.append({
                        "interview_id": interview.get("interview_id"),
                        "type": "interviewer_notification",
                        "error": result["error"]
                    })
            
            await self.log_execution(
                state, "send_interviewer_notifications", 
                f"Sent {len([e for e in state.emails_sent if e['type'] == 'interviewer_notification'])} interviewer notifications"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to send interviewer notifications: {str(e)}")
            return state
    
    async def execute_send_hr_summary(self, state: EmailAgentState) -> EmailAgentState:
        """Send workflow summary to HR"""
        try:
            if not self.config.send_hr_summary:
                return state
            
            # Prepare summary data
            workflow_summary = {
                "job_title": state.job_data.get("title", "Unknown Position"),
                "status": "completed",
                "candidates": [
                    {
                        "name": info["name"],
                        "email": info["email"],
                        "stage": info["current_stage"],
                        "overall_score": 0,  # Would be loaded from evaluation
                        "match_percentage": 0,
                        "recommendation": "interview" if candidate_id in state.approved_candidates else "reject"
                    }
                    for candidate_id, info in state.candidate_data.items()
                ],
                "interviews_scheduled": len(state.scheduled_interviews),
                "emails_sent": len(state.emails_sent),
                "pending_actions": [],
                "total_time": "N/A",
                "success_rate": 95,  # Calculate based on actual results
                "agent_stats": {}
            }
            
            # Generate HR summary email
            email_template = create_hr_summary_email_template(workflow_summary)
            
            # Send to HR (configure HR email in settings)
            hr_email = "hr@company.com"  # This should come from configuration
            
            result = await self.email_service.send_email(
                to_email=hr_email,
                subject=email_template["subject"],
                body=email_template["body"],
                to_name="HR Team",
                email_type="hr_summary",
                workflow_id=state.workflow_id
            )
            
            if result["success"]:
                state.emails_sent.append({
                    "type": "hr_summary",
                    "recipient": hr_email,
                    "subject": email_template["subject"]
                })
            else:
                state.email_failures.append({
                    "type": "hr_summary",
                    "error": result["error"]
                })
            
            await self.log_execution(
                state, "send_hr_summary", 
                "Sent HR summary email"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to send HR summary: {str(e)}")
            return state
    
    async def execute_compile_email_results(self, state: EmailAgentState) -> EmailAgentState:
        """Compile final email sending results"""
        try:
            results = {
                "emails_sent": state.emails_sent,
                "email_failures": state.email_failures,
                "success_count": len(state.emails_sent),
                "failure_count": len(state.email_failures),
                "success_rate": len(state.emails_sent) / (len(state.emails_sent) + len(state.email_failures)) * 100 if (state.emails_sent or state.email_failures) else 100,
                "email_types": {}
            }
            
            # Count by email type
            for email in state.emails_sent:
                email_type = email["type"]
                results["email_types"][email_type] = results["email_types"].get(email_type, 0) + 1
            
            state.output_data = results
            
            await self.log_execution(
                state, "compile_email_results", 
                f"Email sending completed: {results['success_count']} sent, {results['failure_count']} failed"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to compile email results: {str(e)}")
            return state
