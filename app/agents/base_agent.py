import uuid
import logging

from datetime import datetime
from sqlalchemy.orm import Session
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph


class AgentConfig(BaseModel):
    """Base configuration for all agents"""
    name: str
    description: str = ""
    model_name: str = "gpt-4o"
    temperature: float = 0.6
    max_tokens: Optional[int] = None
    timeout_seconds: int = 300
    max_retries: int = 3
    enable_logging: bool = True
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """Base state for agent operations"""
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    current_step: str = ""
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BaseAgent(ABC):
    """Base class for all AI agents in the platform"""

    def __init__(self, config: AgentConfig, db: Session):
        self.config = config
        self.db = db
        self.logger = self._setup_logger()
        self.llm = self._setup_llm()
        self.graph: Optional[StateGraph] = None

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the agent"""
        logger = logging.getLogger(f"{self.__class__.__name__}_{self.config.name}")
        if not logger.handlers and self.config.enable_logging:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _setup_llm(self) -> ChatOpenAI:
        """Setup the LLM for the agent"""
        return ChatOpenAI(
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout_seconds,
        )

    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the agent's main functionality"""
        pass

    @abstractmethod
    def create_workflow_graph(self) -> StateGraph:
        """Create the LangGraph workflow for this agent"""
        pass

    async def run_workflow(self, initial_state: AgentState) -> AgentState:
        """Run the agent's workflow graph"""
        try:
            if not self.graph:
                self.graph = self.create_workflow_graph()

            self.logger.info(f"Starting workflow for agent {self.config.name}")
            result = await self.graph.ainvoke(initial_state.model_dump())

            # Convert back to AgentState
            final_state = AgentState(**result)
            final_state.updated_at = datetime.now()

            self.logger.info(f"Completed workflow for agent {self.config.name}")
            return final_state

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}")
            initial_state.errors.append(f"Workflow execution failed: {str(e)}")
            return initial_state

    async def validate_input(self, state: AgentState) -> bool:
        """Validate input data for the agent"""
        return True

    async def log_execution(
        self, state: AgentState, step: str,
        message: str, level: str = "INFO"
    ):
        """Log execution details to database"""
        if self.config.enable_logging:
            # This would save to WorkflowLog table
            self.logger.info(f"[{step}] {message}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this agent"""
        return {
            "agent_name": self.config.name,
            "total_executions": 0,  # Would be tracked
            "average_execution_time": 0,
            "success_rate": 0,
            "last_execution": None
        }


class MultiStepAgent(BaseAgent):
    """Base class for agents that execute multiple steps"""

    @abstractmethod
    def get_execution_steps(self) -> List[str]:
        """Return list of execution step names"""
        pass

    async def execute_step(
        self, step_name: str, state: AgentState
    ) -> AgentState:
        """Execute a specific step"""
        state.current_step = step_name
        state.updated_at = datetime.now()

        await self.log_execution(
            state, step_name, f"Starting step: {step_name}"
        )

        try:
            # Call the specific step method
            step_method = getattr(self, f"execute_{step_name}")
            result_state = await step_method(state)
            await self.log_execution(state, step_name, f"Completed step: {step_name}")
            return result_state

        except AttributeError:
            error_msg = f"Step method 'execute_{step_name}' not implemented"
            state.errors.append(error_msg)
            await self.log_execution(state, step_name, error_msg, "ERROR")
            return state
        except Exception as e:
            error_msg = f"Error in step {step_name}: {str(e)}"
            state.errors.append(error_msg)
            await self.log_execution(state, step_name, error_msg, "ERROR")
            return state


class AgentRegistry:
    """Registry for managing all agents in the platform"""

    def __init__(self):
        self._agents: Dict[str, type] = {}
        self._instances: Dict[str, BaseAgent] = {}

    def register(self, name: str, agent_class: type):
        """Register an agent class"""
        if not issubclass(agent_class, BaseAgent):
            raise ValueError("Agent class must inherit from BaseAgent")
        self._agents[name] = agent_class

    def create_agent(
        self, name: str, config: AgentConfig, db: Session
    ) -> BaseAgent:
        """Create an agent instance"""
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not registered")

        agent_class = self._agents[name]
        instance = agent_class(config, db)
        self._instances[config.name] = instance
        return instance

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an existing agent instance"""
        return self._instances.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent types"""
        return list(self._agents.keys())


# Global agent registry
agent_registry = AgentRegistry()
