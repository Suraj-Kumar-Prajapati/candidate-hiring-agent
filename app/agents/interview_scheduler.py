from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, START, END

from app.agents.base_agent import AgentState, AgentConfig, MultiStepAgent
from app.services.interview_service import InterviewService
from app.services.job_service import JobService
from app.utils.time_utils import find_common_availability


class InterviewSchedulerConfig(AgentConfig):
    """Configuration for interview scheduler agent"""
    job_id: str
    default_duration_minutes: int = 60
    advance_scheduling_days: int = 7
    max_interviews_per_day: int = 3
    preferred_time_slots: List[str] = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
    auto_assign_interviewers: bool = True
    send_calendar_invites: bool = True


class InterviewSchedulerState(AgentState):
    """State for interview scheduler"""
    job_id: str = ""
    candidate_ids: List[str] = []
    
    # Interviewer data
    available_interviewers: List[Dict[str, Any]] = []
    interviewer_schedules: Dict[str, List[Dict[str, Any]]] = {}
    
    # Scheduling results
    scheduled_interviews: List[Dict[str, Any]] = []
    scheduling_conflicts: List[Dict[str, Any]] = []
    failed_scheduling: List[Dict[str, Any]] = []


class InterviewSchedulerAgent(MultiStepAgent):
    """Agent responsible for scheduling interviews"""
    
    def __init__(self, config: InterviewSchedulerConfig, db):
        super().__init__(config, db)
        self.config: InterviewSchedulerConfig = config
        self.interview_service = InterviewService(db)
        self.job_service = JobService(db)
    
    def get_execution_steps(self) -> List[str]:
        return [
            "load_job_data",
            "load_available_interviewers",
            "get_interviewer_schedules",
            "load_candidate_preferences",
            "find_optimal_slots",
            "create_interview_records",
            "generate_meeting_links",
            "save_scheduling_results"
        ]
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute interview scheduling workflow"""
        scheduler_state = InterviewSchedulerState(**state.dict())
        
        for step in self.get_execution_steps():
            scheduler_state = await self.execute_step(step, scheduler_state)
            if scheduler_state.errors:
                break
        
        return scheduler_state
    
    def create_workflow_graph(self) -> StateGraph:
        """Create LangGraph workflow for interview scheduling"""
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
        """Create node function for scheduling steps"""
        async def node_function(state: dict) -> dict:
            scheduler_state = InterviewSchedulerState(**state)
            result_state = await self.execute_step(step_name, scheduler_state)
            return result_state.dict()
        return node_function
    
    async def execute_load_job_data(self, state: InterviewSchedulerState) -> InterviewSchedulerState:
        """Load job information"""
        try:
            job = await self.job_service.get_job(state.job_id)
            if not job:
                state.errors.append(f"Job {state.job_id} not found")
                return state
            
            state.context["job_info"] = {
                "title": job.title,
                "technologies_required": job.technologies_required,
                "department": job.department
            }
            
            await self.log_execution(state, "load_job_data", f"Loaded job data for {job.title}")
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to load job data: {str(e)}")
            return state
    
    async def execute_load_available_interviewers(self, state: InterviewSchedulerState) -> InterviewSchedulerState:
        """Load available interviewers for the job"""
        try:
            job_info = state.context.get("job_info", {})
            required_technologies = job_info.get("technologies_required", [])
            
            # Get matching interviewers
            interviewers = await self.job_service.find_matching_interviewers(
                state.job_id, required_technologies
            )
            
            state.available_interviewers = [
                {
                    "id": str(interviewer.id),
                    "name": interviewer.name,
                    "email": interviewer.email,
                    "technologies": interviewer.technologies,
                    "availability_slots": interviewer.availability_slots,
                    "max_interviews_per_day": interviewer.max_interviews_per_day,
                    "match_score": getattr(interviewer, "match_score", 0)
                } for interviewer in interviewers
            ]
            
            await self.log_execution(
                state, "load_available_interviewers", 
                f"Found {len(state.available_interviewers)} matching interviewers"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to load interviewers: {str(e)}")
            return state
    
    async def execute_get_interviewer_schedules(self, state: InterviewSchedulerState) -> InterviewSchedulerState:
        """Get current schedules for all interviewers"""
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=self.config.advance_scheduling_days)
            
            for interviewer in state.available_interviewers:
                interviewer_id = interviewer["id"]
                
                # Get existing interviews
                existing_interviews = await self.interview_service.get_interviewer_schedule(
                    interviewer_id, start_date, end_date
                )
                
                # Convert to schedule format
                busy_slots = []
                for interview in existing_interviews:
                    if interview.scheduled_time:
                        busy_slots.append({
                            "start": interview.scheduled_time,
                            "end": interview.scheduled_time + timedelta(minutes=interview.duration_minutes),
                            "interview_id": str(interview.id)
                        })
                
                state.interviewer_schedules[interviewer_id] = busy_slots
            
            await self.log_execution(
                state, "get_interviewer_schedules", 
                f"Retrieved schedules for {len(state.available_interviewers)} interviewers"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to get interviewer schedules: {str(e)}")
            return state
    
    async def execute_load_candidate_preferences(self, state: InterviewSchedulerState) -> InterviewSchedulerState:
        """Load candidate availability preferences"""
        try:
            from app.services.candidate_service import CandidateService
            candidate_service = CandidateService(self.db)
            
            candidate_preferences = {}
            
            for candidate_id in state.candidate_ids:
                candidate = await candidate_service.get_candidate(candidate_id)
                if candidate:
                    candidate_preferences[candidate_id] = {
                        "name": candidate.name,
                        "email": candidate.email,
                        "time_availability": candidate.time_availability,
                        "interview_availability": candidate.interview_availability
                    }
            
            state.context["candidate_preferences"] = candidate_preferences
            
            await self.log_execution(
                state, "load_candidate_preferences", 
                f"Loaded preferences for {len(candidate_preferences)} candidates"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to load candidate preferences: {str(e)}")
            return state
    
    async def execute_find_optimal_slots(self, state: InterviewSchedulerState) -> InterviewSchedulerState:
        """Find optimal time slots for interviews"""
        try:
            candidate_preferences = state.context.get("candidate_preferences", {})
            optimal_slots = []
            
            for candidate_id in state.candidate_ids:
                candidate_info = candidate_preferences.get(candidate_id, {})
                candidate_availability = candidate_info.get("time_availability", "flexible")
                
                # Find best interviewer for this candidate
                best_interviewer = self._find_best_interviewer(
                    state.available_interviewers,
                    state.interviewer_schedules
                )
                
                if not best_interviewer:
                    state.scheduling_conflicts.append({
                        "candidate_id": candidate_id,
                        "reason": "No available interviewer found"
                    })
                    continue
                
                # Find available time slots
                available_slots = await self.interview_service.find_available_slots(
                    best_interviewer["id"],
                    self._get_preferred_dates(),
                    self.config.default_duration_minutes
                )
                
                # Match with candidate availability
                matching_slots = find_common_availability(
                    candidate_availability,
                    [slot.strftime("%A %H:%M") for slot in available_slots]
                )
                
                if matching_slots:
                    optimal_slot = matching_slots[0]  # Take first available
                    optimal_slots.append({
                        "candidate_id": candidate_id,
                        "interviewer_id": best_interviewer["id"],
                        "interviewer_name": best_interviewer["name"],
                        "interviewer_email": best_interviewer["email"],
                        "scheduled_time": optimal_slot,
                        "duration_minutes": self.config.default_duration_minutes,
                        "interview_type": "technical_round_1"
                    })
                    
                    # Update interviewer schedule to avoid double booking
                    self._update_interviewer_schedule(
                        state.interviewer_schedules,
                        best_interviewer["id"],
                        optimal_slot,
                        self.config.default_duration_minutes
                    )
                else:
                    state.scheduling_conflicts.append({
                        "candidate_id": candidate_id,
                        "interviewer_id": best_interviewer["id"],
                        "reason": "No matching time slots found"
                    })
            
            state.context["optimal_slots"] = optimal_slots
            
            await self.log_execution(
                state, "find_optimal_slots", 
                f"Found {len(optimal_slots)} optimal interview slots"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to find optimal slots: {str(e)}")
            return state
    
    def _find_best_interviewer(
        self, 
        interviewers: List[Dict[str, Any]], 
        schedules: Dict[str, List[Dict[str, Any]]]
    ) -> Optional[Dict[str, Any]]:
        """Find the best available interviewer"""
        # Sort by match score and availability
        available_interviewers = []
        
        for interviewer in interviewers:
            interviewer_id = interviewer["id"]
            busy_slots = schedules.get(interviewer_id, [])
            
            # Count interviews today
            today_interviews = sum(
                1 for slot in busy_slots 
                if slot["start"].date() == datetime.now().date()
            )
            
            # Check if interviewer has capacity
            if today_interviews < interviewer.get("max_interviews_per_day", 3):
                available_interviewers.append({
                    **interviewer,
                    "current_load": today_interviews
                })
        
        if not available_interviewers:
            return None
        
        # Sort by match score (desc) and current load (asc)
        return sorted(
            available_interviewers,
            key=lambda x: (-x.get("match_score", 0), x["current_load"])
        )[0]
    
    def _get_preferred_dates(self) -> List[datetime]:
        """Get list of preferred interview dates"""
        dates = []
        start_date = datetime.now().date() + timedelta(days=1)  # Start tomorrow
        
        for i in range(self.config.advance_scheduling_days):
            check_date = start_date + timedelta(days=i)
            # Skip weekends
            if check_date.weekday() < 5:
                dates.append(datetime.combine(check_date, datetime.min.time()))
        
        return dates
    
    def _update_interviewer_schedule(
        self, 
        schedules: Dict[str, List[Dict[str, Any]]], 
        interviewer_id: str, 
        start_time: datetime, 
        duration_minutes: int
    ):
        """Update interviewer schedule with new appointment"""
        if interviewer_id not in schedules:
            schedules[interviewer_id] = []
        
        schedules[interviewer_id].append({
            "start": start_time,
            "end": start_time + timedelta(minutes=duration_minutes),
            "interview_id": "pending"
        })
    
    async def execute_create_interview_records(self, state: InterviewSchedulerState) -> InterviewSchedulerState:
        """Create interview records in database"""
        try:
            optimal_slots = state.context.get("optimal_slots", [])
            created_interviews = []
            
            for slot in optimal_slots:
                try:
                    from app.schemas.interview import InterviewCreate
                    interview_data = InterviewCreate(
                        candidate_id=slot["candidate_id"],
                        interviewer_id=slot["interviewer_id"],
                        job_id=state.job_id,
                        scheduled_time=slot["scheduled_time"],
                        interview_type=slot["interview_type"],
                        duration_minutes=slot["duration_minutes"]
                    )
                    
                    interview = await self.interview_service.create_interview(interview_data)
                    
                    created_interviews.append({
                        "interview_id": str(interview.id),
                        "candidate_id": slot["candidate_id"],
                        "interviewer_id": slot["interviewer_id"],
                        "interviewer_name": slot["interviewer_name"],
                        "interviewer_email": slot["interviewer_email"],
                        "scheduled_time": slot["scheduled_time"],
                        "duration_minutes": slot["duration_minutes"],
                        "interview_type": slot["interview_type"]
                    })
                    
                except Exception as e:
                    state.failed_scheduling.append({
                        "candidate_id": slot["candidate_id"],
                        "error": f"Failed to create interview record: {str(e)}"
                    })
            
            state.scheduled_interviews = created_interviews
            
            await self.log_execution(
                state, "create_interview_records", 
                f"Created {len(created_interviews)} interview records"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to create interview records: {str(e)}")
            return state
    
    async def execute_generate_meeting_links(self, state: InterviewSchedulerState) -> InterviewSchedulerState:
        """Generate meeting links for interviews"""
        try:
            # This is a placeholder - in practice, you'd integrate with 
            # meeting services like Zoom, Google Meet, etc.
            
            for interview in state.scheduled_interviews:
                # Generate a meeting link (placeholder)
                meeting_link = f"https://meet.company.com/interview/{interview['interview_id']}"
                meeting_id = f"INT-{interview['interview_id'][:8]}"
                
                interview["meeting_link"] = meeting_link
                interview["meeting_id"] = meeting_id
                
                # Update interview record with meeting info
                from app.schemas.interview import InterviewUpdate
                update_data = InterviewUpdate(
                    meeting_link=meeting_link,
                    meeting_id=meeting_id
                )
                
                await self.interview_service.update_interview(
                    interview["interview_id"], 
                    update_data
                )
            
            await self.log_execution(
                state, "generate_meeting_links", 
                f"Generated meeting links for {len(state.scheduled_interviews)} interviews"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to generate meeting links: {str(e)}")
            return state
    
    async def execute_save_scheduling_results(self, state: InterviewSchedulerState) -> InterviewSchedulerState:
        """Save final scheduling results"""
        try:
            results = {
                "scheduled_interviews": state.scheduled_interviews,
                "scheduling_conflicts": state.scheduling_conflicts,
                "failed_scheduling": state.failed_scheduling,
                "success_rate": len(state.scheduled_interviews) / len(state.candidate_ids) * 100 if state.candidate_ids else 0,
                "total_candidates": len(state.candidate_ids),
                "successful_schedules": len(state.scheduled_interviews)
            }
            
            state.output_data = results
            
            await self.log_execution(
                state, "save_scheduling_results", 
                f"Scheduling completed with {results['success_rate']:.1f}% success rate"
            )
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to save scheduling results: {str(e)}")
            return state
