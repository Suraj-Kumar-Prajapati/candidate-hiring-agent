import json

from pydantic import Field
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from app.agents.base_agent import AgentState, AgentConfig, MultiStepAgent
from app.models.candidate import Candidate, CandidateEvaluation


class ResumeEvaluatorConfig(AgentConfig):
    """Configuration specific to resume evaluation"""
    evaluation_criteria: List[str] = Field(default=[
        "technical_skills", "experience_relevance", "education_qualifications",
        "soft_skills", "ats_compatibility"
    ])
    scoring_weights: Dict[str, float] = Field(default={
        "technical_skills": 0.35,
        "experience_relevance": 0.25,
        "education_qualifications": 0.15,
        "soft_skills": 0.15,
        "ats_compatibility": 0.10
    })
    minimum_pass_score: float = 6.0
    auto_reject_threshold: float = 3.0


class ResumeEvaluatorState(AgentState):
    """State specific to resume evaluation"""
    candidate_id: str = ""
    job_id: str = ""
    resume_text: str = ""
    job_description: str = ""

    # Evaluation results
    technical_evaluation: Dict[str, Any] = Field(default_factory=dict)
    experience_evaluation: Dict[str, Any] = Field(default_factory=dict)
    education_evaluation: Dict[str, Any] = Field(default_factory=dict)
    skills_evaluation: Dict[str, Any] = Field(default_factory=dict)
    ats_evaluation: Dict[str, Any] = Field(default_factory=dict)

    # Final results
    overall_score: float = 0.0
    weighted_score: float = 0.0
    match_percentage: int = 0
    recommendation: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    summary: str = ""


class ResumeEvaluatorAgent(MultiStepAgent):
    """Agent responsible for evaluating candidate resumes"""

    def __init__(self, config: ResumeEvaluatorConfig, db):
        super().__init__(config, db)
        self.config: ResumeEvaluatorConfig = config

    def get_execution_steps(self) -> List[str]:
        return [
            "load_data",
            "evaluate_technical_skills",
            "evaluate_experience",
            "evaluate_education",
            "evaluate_soft_skills",
            "evaluate_ats_compatibility",
            "calculate_final_score",
            "save_evaluation"
        ]

    async def execute(self, state: AgentState) -> AgentState:
        """Execute the complete resume evaluation workflow"""
        eval_state = ResumeEvaluatorState(**state.model_dump())

        # Execute all steps sequentially
        for step in self.get_execution_steps():
            eval_state = await self.execute_step(step, eval_state)
            if eval_state.errors:
                break

        return eval_state

    def create_workflow_graph(self) -> StateGraph:
        """Create LangGraph workflow for resume evaluation"""
        graph = StateGraph(dict)

        # Add nodes for each step
        for step in self.get_execution_steps():
            graph.add_node(step, self._create_step_node(step))

        # Create linear flow
        steps = self.get_execution_steps()
        graph.add_edge(START, steps[0])

        for i in range(len(steps) - 1):
            graph.add_edge(steps[i], steps[i + 1])

        graph.add_edge(steps[-1], END)

        return graph.compile()

    def _create_step_node(self, step_name: str):
        """Create a node function for a specific step"""
        async def node_function(state: dict) -> dict:
            agent_state = ResumeEvaluatorState(**state)
            result_state = await self.execute_step(step_name, agent_state)
            return result_state.model_dump()
        return node_function

    async def execute_load_data(
        self, state: ResumeEvaluatorState
    ) -> ResumeEvaluatorState:
        """Load candidate and job data from database"""
        try:
            # Load candidate
            candidate = self.db.query(
                Candidate
            ).filter(Candidate.id == state.candidate_id).first()

            if not candidate:
                state.errors.append("Candidate not found")
                return state

            state.resume_text = candidate.resume_text or ""

            # Load job description
            from app.models.job import Job
            job = self.db.query(Job).filter(Job.id == state.job_id).first()
            if not job:
                state.errors.append("Job not found")
                return state

            state.job_description = job.description

            await self.log_execution(
                state, "load_data",
                "Successfully loaded candidate and job data"
            )
            return state

        except Exception as e:
            state.errors.append(f"Data loading failed: {str(e)}")
            return state

    async def execute_evaluate_technical_skills(
        self, state: ResumeEvaluatorState
    ) -> ResumeEvaluatorState:
        """Evaluate technical skills alignment"""
        try:
            prompt = f"""
            Evaluate the technical skills of the candidate based on their resume against the job requirements.

            Job Description: {state.job_description}
            Resume Text: {state.resume_text}

            Assess:
            1. Technical skill alignment with job requirements (0-10)
            2. Depth of technical expertise (0-10)
            3. Relevant technologies and frameworks (0-10)
            4. Technical certifications and achievements (0-10)
            5. Project complexity and technical challenges handled (0-10)

            Return JSON with:
            {{
                "scores": {{
                    "skill_alignment": <score>,
                    "expertise_depth": <score>,
                    "technology_relevance": <score>,
                    "certifications": <score>,
                    "project_complexity": <score>
                }},
                "overall_score": <average_score>,
                "feedback": "<detailed feedback>",
                "key_points": ["<point1>", "<point2>", ...],
                "strengths": ["<strength1>", "<strength2>", ...],
                "weaknesses": ["<weakness1>", "<weakness2>", ...]
            }}
            """

            response = await self.llm.ainvoke(prompt)

            # Parse JSON response
            try:
                evaluation_data = json.loads(response.content)
                state.technical_evaluation = evaluation_data
                await self.log_execution(
                    state, "evaluate_technical_skills",
                    "Technical skills evaluation completed"
                )
            except json.JSONDecodeError:
                state.errors.append("Failed to parse technical evaluation response")  # noqa

            return state

        except Exception as e:
            state.errors.append(f"Technical evaluation failed: {str(e)}")
            return state

    async def execute_evaluate_experience(
        self, state: ResumeEvaluatorState
    ) -> ResumeEvaluatorState:
        """Evaluate work experience relevance"""
        try:
            prompt = f"""
            Evaluate the work experience relevance and career progression of the candidate.

            Job Description: {state.job_description}
            Resume Text: {state.resume_text}

            Assess:
            1. Relevance of work experience to the target role (0-10)
            2. Career progression and growth trajectory (0-10)
            3. Industry experience alignment (0-10)
            4. Leadership and responsibility evolution (0-10)
            5. Consistency and stability in career (0-10)

            Return JSON with same structure as technical evaluation.
            """

            response = await self.llm.ainvoke(prompt)

            try:
                evaluation_data = json.loads(response.content)
                state.experience_evaluation = evaluation_data
                await self.log_execution(
                    state, "evaluate_experience",
                    "Experience evaluation completed"
                )
            except json.JSONDecodeError:
                state.errors.append("Failed to parse experience evaluation response")

            return state

        except Exception as e:
            state.errors.append(f"Experience evaluation failed: {str(e)}")
            return state

    async def execute_evaluate_education(
        self, state: ResumeEvaluatorState
    ) -> ResumeEvaluatorState:
        """Evaluate educational qualifications"""
        try:
            prompt = f"""
            Evaluate the educational qualifications and academic background.

            Job Description: {state.job_description}
            Resume Text: {state.resume_text}

            Assess:
            1. Educational qualification alignment (0-10)
            2. Institution quality and reputation (0-10)
            3. Relevant coursework and specializations (0-10)
            4. Academic achievements and honors (0-10)
            5. Continuous learning and professional development (0-10)

            Return JSON with same structure as technical evaluation.
            """

            response = await self.llm.ainvoke(prompt)

            try:
                evaluation_data = json.loads(response.content)
                state.education_evaluation = evaluation_data
                await self.log_execution(
                    state, "evaluate_education",
                    "Education evaluation completed"
                )
            except json.JSONDecodeError:
                state.errors.append(
                    "Failed to parse education evaluation response"
                )

            return state

        except Exception as e:
            state.errors.append(f"Education evaluation failed: {str(e)}")
            return state

    async def execute_evaluate_soft_skills(
        self, state: ResumeEvaluatorState
    ) -> ResumeEvaluatorState:
        """Evaluate soft skills and interpersonal abilities"""
        try:
            prompt = f"""
            Evaluate soft skills and interpersonal abilities from the resume.

            Job Description: {state.job_description}
            Resume Text: {state.resume_text}

            Assess:
            1. Communication skills evidence (0-10)
            2. Leadership and teamwork examples (0-10)
            3. Problem-solving and analytical thinking (0-10)
            4. Adaptability and learning agility (0-10)
            5. Cultural fit indicators (0-10)

            Return JSON with same structure as technical evaluation.
            """

            response = await self.llm.ainvoke(prompt)

            try:
                evaluation_data = json.loads(response.content)
                state.skills_evaluation = evaluation_data
                await self.log_execution(
                    state, "evaluate_soft_skills",
                    "Soft skills evaluation completed"
                )
            except json.JSONDecodeError:
                state.errors.append(
                    "Failed to parse soft skills evaluation response"
                )

            return state

        except Exception as e:
            state.errors.append(f"Soft skills evaluation failed: {str(e)}")
            return state

    async def execute_evaluate_ats_compatibility(
        self, state: ResumeEvaluatorState
    ) -> ResumeEvaluatorState:
        """Evaluate ATS compatibility and resume formatting"""
        try:
            prompt = f"""
            Evaluate ATS (Applicant Tracking System) compatibility of the resume.

            Job Description: {state.job_description}
            Resume Text: {state.resume_text}

            Assess:
            1. Keyword optimization for the target role (0-10)
            2. Resume structure and formatting clarity (0-10)
            3. Section organization and completeness (0-10)
            4. Contact information completeness (0-10)
            5. Overall parseability and readability (0-10)

            Return JSON with same structure as technical evaluation.
            """

            response = await self.llm.ainvoke(prompt)

            try:
                evaluation_data = json.loads(response.content)
                state.ats_evaluation = evaluation_data
                await self.log_execution(
                    state, "evaluate_ats_compatibility",
                    "ATS compatibility evaluation completed"
                )
            except json.JSONDecodeError:
                state.errors.append("Failed to parse ATS evaluation response")

            return state

        except Exception as e:
            state.errors.append(f"ATS evaluation failed: {str(e)}")
            return state

    async def execute_calculate_final_score(
        self, state: ResumeEvaluatorState
    ) -> ResumeEvaluatorState:
        """Calculate weighted final score and recommendation"""
        try:
            # Extract scores from evaluations
            evaluations = {
                "technical_skills": state.technical_evaluation,
                "experience_relevance": state.experience_evaluation,
                "education_qualifications": state.education_evaluation,
                "soft_skills": state.skills_evaluation,
                "ats_compatibility": state.ats_evaluation
            }

            # Calculate weighted score
            total_weighted_score = 0.0
            component_scores = {}
            all_strengths = []
            all_weaknesses = []

            for criteria, weight in self.config.scoring_weights.items():
                if criteria in evaluations and evaluations[criteria]:
                    score = evaluations[criteria].get("overall_score", 0)
                    component_scores[criteria] = score
                    total_weighted_score += score * weight

                    # Collect strengths and weaknesses
                    all_strengths.extend(evaluations[criteria].get("strengths", []))
                    all_weaknesses.extend(evaluations[criteria].get("weaknesses", []))

            state.weighted_score = round(total_weighted_score, 2)
            state.overall_score = round(sum(component_scores.values()) / len(component_scores), 2)
            state.match_percentage = min(100, int(state.weighted_score * 10))

            # Determine recommendation
            if state.weighted_score >= 8.0:
                state.recommendation = "fast_track"
            elif state.weighted_score >= self.config.minimum_pass_score:
                state.recommendation = "interview"
            elif state.weighted_score <= self.config.auto_reject_threshold:
                state.recommendation = "reject"
            else:
                state.recommendation = "review_required"

            # Deduplicate and limit strengths/weaknesses
            state.strengths = list(set(all_strengths))[:5]
            state.weaknesses = list(set(all_weaknesses))[:5]

            # Generate summary
            state.summary = f"Candidate scored {state.weighted_score}/10 with {state.match_percentage}% job match. " \
                          f"Recommendation: {state.recommendation.replace('_', ' ').title()}."

            await self.log_execution(state, "calculate_final_score", f"Final score calculated: {state.weighted_score}")
            return state

        except Exception as e:
            state.errors.append(f"Score calculation failed: {str(e)}")
            return state

    async def execute_save_evaluation(
        self, state: ResumeEvaluatorState
    ) -> ResumeEvaluatorState:
        """Save evaluation results to database"""
        try:
            # Update candidate with scores
            candidate = self.db.query(Candidate).filter(Candidate.id == state.candidate_id).first()
            if candidate:
                candidate.overall_score = state.overall_score
                candidate.technical_score = state.technical_evaluation.get("overall_score", 0)
                candidate.experience_score = state.experience_evaluation.get("overall_score", 0)
                candidate.education_score = state.education_evaluation.get("overall_score", 0)
                candidate.skills_score = state.skills_evaluation.get("overall_score", 0)
                candidate.ats_score = state.ats_evaluation.get("overall_score", 0)
                candidate.match_percentage = state.match_percentage

                # Update stage based on recommendation
                if state.recommendation == "reject":
                    candidate.current_stage = "rejected_resume_screening"
                elif state.recommendation in ["interview", "fast_track"]:
                    candidate.current_stage = "pending_tech_lead_review"
                else:
                    candidate.current_stage = "pending_manual_review"

            # Save detailed evaluations
            evaluations_to_save = [
                ("technical_skills", state.technical_evaluation),
                ("experience_relevance", state.experience_evaluation),
                ("education_qualifications", state.education_evaluation),
                ("soft_skills", state.skills_evaluation),
                ("ats_compatibility", state.ats_evaluation)
            ]

            for eval_type, eval_data in evaluations_to_save:
                if eval_data:
                    evaluation = CandidateEvaluation(
                        candidate_id=state.candidate_id,
                        evaluation_type=eval_type,
                        score=eval_data.get("overall_score", 0),
                        feedback=eval_data.get("feedback", ""),
                        key_points=eval_data.get("key_points", []),
                        strengths=eval_data.get("strengths", []),
                        weaknesses=eval_data.get("weaknesses", []),
                        model_used=self.config.model_name
                    )
                    self.db.add(evaluation)

            self.db.commit()
            await self.log_execution(
                state, "save_evaluation",
                "Evaluation results saved to database"
            )
            return state

        except Exception as e:
            self.db.rollback()
            state.errors.append(f"Failed to save evaluation: {str(e)}")
            return state
