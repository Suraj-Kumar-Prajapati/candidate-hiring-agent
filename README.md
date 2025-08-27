# About Repo

Teams Hiring Agent is a lightweight automation bot that integrates directly with Microsoft Teams to streamline the hiring workflow. Traditionally, HR teams manually share resumes, tag technical leads, coordinate interview availability, schedule meetings, and send reminders — all of which is time-consuming and error-prone. This project provides a single, focused AI-assisted agent that automates those steps, keeping the workflow inside Teams without requiring an external platform.

- The agent listens for new resumes posted in a Teams channel via Microsoft Graph change notifications. It then:
- Parses candidate details (name, experience, availability) using a simple resume parser.
- Identifies an appropriate interviewer from a configurable pool.
- Schedules a Teams meeting (via Microsoft Graph OnlineMeetings API).
- Posts details back into the Teams thread, ensuring transparency for HR and technical leads.
- Optionally triggers reminders for candidates and interviewers before the meeting.

The implementation is intentionally minimal — no unnecessary APIs, WebSockets, or multi-agent complexity.
This repo is for HR teams or organizations seeking to simplify hiring inside Teams with minimal setup and maximum clarity.


# AI Hiring Agent Platform

## 🚀 Overview
The AI Hiring Agent Platform is a comprehensive, automated hiring solution that leverages AI agents, LangGraph workflows, and modern web technologies to streamline the entire recruitment process. From resume evaluation to interview scheduling and email automation, this platform handles the complete hiring workflow with minimal human intervention.

## ✨ Features
### Core Capabilities- 
- **🤖 AI-Powered Resume Evaluation**: Automated screening using GPT-4 with customizable scoring criteria
- **📋 Multi-Stage Workflow Management**: Complete hiring pipeline from application to final decision
- **📅 Intelligent Interview Scheduling**: Automatic matching of candidate and interviewer availability
- **📧 Advanced Email Automation**: AWS SES integration with beautiful HTML templates
- **👥 Human-in-the-Loop Decision Points**: Pause workflows for critical human approvals
- **⚡ Real-time Updates**: WebSocket support for live workflow monitoring
- **📊 Comprehensive Analytics**: Detailed insights and reporting on hiring metrics

### Technical Features
- **🏗️ Scalable Architecture**: Microservices-ready with FastAPI and PostgreSQL
- **🔧 Extensible Agent Framework**: Easy to add new AI agents for custom workflows
- **📱 RESTful API**: Complete CRUD operations with auto-generated documentation
- **🐳 Docker Support**: Containerized deployment with Docker Compose
- **🔒 Security First**: JWT authentication, rate limiting, and data validation
- **📈 Performance Optimized**: Async operations, connection pooling, and caching

## 🏛️ Architecture
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│   PostgreSQL    │────│      Redis      │
│   (API Layer)   │    │   (Database)    │    │    (Cache)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI Agent Framework                           │
│  ┌───────────────┐ ┌──────────────┐ ┌─────────────────────────┐ │
│  │   Resume      │ │  Interview   │ │    Email & Workflow     │ │
│  │  Evaluator    │ │  Scheduler   │ │     Orchestrator        │ │
│  └───────────────┘ └──────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenAI GPT    │    │    AWS SES      │    │   LangGraph     │
│   (AI Engine)   │    │   (Email)       │    │  (Workflows)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘

## 🛠️ Technology Stack
### Backend
- **FastAPI**: Modern, fast web framework for building APIs  
- **PostgreSQL**: Robust relational database with JSON support  
- **SQLAlchemy**: Python SQL toolkit and ORM  
- **Redis**: In-memory data structure store for caching  
- **Celery**: Distributed task queue for background processing  

### AI & Automation
- **OpenAI GPT-4**: Advanced language model for resume evaluation  
- **LangChain**: Framework for building LLM applications  
- **LangGraph**: State machine for complex AI workflows  
- **Pydantic**: Data validation using Python type annotations  

### Email & Communication
- **AWS SES**: Scalable email sending service  
- **Boto3**: AWS SDK for Python  
- **WebSockets**: Real-time communication  
- **HTML Email Templates**: Responsive email designs  

### DevOps & Deployment
- **Docker**: Containerization platform  
- **Docker Compose**: Multi-container orchestration  
- **Alembic**: Database migration tool  
- **Pytest**: Testing framework  

## 📋 Prerequisites
- Python 3.11+  
- PostgreSQL 13+  
- Redis 6+  
- Docker & Docker Compose  
- OpenAI API Key  
- AWS SES Credentials  

## ⚡ Quick Start
```bash
# 1. Navigate to project directory
cd ai-hiring-agent-platform

# 2. Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up database
alembic upgrade head

# 5. Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API documentation
open http://localhost:8000/docs


## 📖 Configuration
Environment Variables

## Application
PROJECT_NAME="AI Hiring Agent Platform"
ENVIRONMENT="production"
SECRET_KEY="your-super-secret-key"

## Database
POSTGRES_SERVER="localhost"
POSTGRES_USER="hiring_agent"
POSTGRES_PASSWORD="your_password"
POSTGRES_DB="hiring_agent_db"

# #AI Configuration
OPENAI_API_KEY="sk-proj-your-key"
OPENAI_MODEL="gpt-4o"

## AWS SES
AWS_SES_ACCESS_KEY_ID="your-access-key"
AWS_SES_SECRET_ACCESS_KEY="your-secret-key"
AWS_SES_REGION="us-east-1"

## Email Addresses
COMPANY_EMAIL="HR Team <hr@company.com>"
DEVELOPERS_EMAIL="Dev Team <dev@company.com>"


## 🎯 Usage Examples
### 1. Create a Job Posting
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Developer",
    "description": "We are looking for an experienced Python developer...",
    "technologies_required": ["Python", "FastAPI", "PostgreSQL"],
    "experience_required": "3-5 years",
    "location": "Remote"
  }'

### 2. Upload Candidate Resume
curl -X POST "http://localhost:8000/api/v1/candidates/" \
  -H "Content-Type: multipart/form-data" \
  -F 'candidate_data={"name": "John Doe", "email": "john@example.com"}' \
  -F "resume_file=@resume.pdf" \
  -F "job_id=job-uuid-here"

### 3. Start Hiring Workflow
curl -X POST "http://localhost:8000/api/v1/workflows/start-hiring-process" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-uuid-here",
    "name": "Backend Developer Hiring - Dec 2024"
  }'

### 4. Monitor Workflow Progress
// WebSocket connection for real-time updates
const ws = new WebSocket('ws://localhost:8000/ws/workflow/workflow-id');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Workflow Update:', update);
};


## 🤖 AI Agents
### Resume Evaluator Agent
**Evaluates candidates on**:
- Technical skills alignment (35%)
- Experience relevance (25%)
- Education qualifications (15%)
- Soft skills indicators (15%)
- ATS compatibility (10%)

### Outputs:
- Overall score (0-10)
- Match percentage
- Detailed feedback
- Recommendation (interview/reject/review)


### Interview Scheduler Agent
**Features**:
- Automatic interviewer matching
- Calendar conflict resolution
- Meeting link generation
- Multi-timezone support
- Rescheduling automation


### Email Agent
**Capabilities**:
- HTML email templates
- Bulk email processing
- SES integration
- Delivery tracking
- Template customization


## 📊 API Documentation
### Core Endpoints

| Method | Endpoint                                 | Description            |
| ------ | ---------------------------------------- | ---------------------- |
| GET    | `/health`                                | Health check           |
| GET    | `/docs`                                  | Interactive API docs   |
| POST   | `/api/v1/jobs/`                          | Create job posting     |
| GET    | `/api/v1/jobs/{id}`                      | Get job details        |
| POST   | `/api/v1/candidates/`                    | Upload candidate       |
| POST   | `/api/v1/candidates/{id}/evaluate`       | Trigger evaluation     |
| GET    | `/api/v1/candidates/{id}/status`         | Check candidate status |
| POST   | `/api/v1/workflows/start-hiring-process` | Start workflow         |
| GET    | `/api/v1/workflows/{id}/status`          | Workflow status        |
| POST   | `/api/v1/workflows/{id}/human-decision`  | Submit human decision  |



## WebSocket Endpoints
- ws://localhost:8000/ws/workflow/{workflow_id} → Real-time workflow updates


## 🔧 Development
**Project Structure**
hiring_agent_platform/
├── app/
│   ├── agents/           # AI agents and workflows
│   ├── api/             # FastAPI routes
│   ├── core/            # Configuration and database
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── utils/           # Helper functions
│   └── main.py          # Application entry point
├── alembic/             # Database migrations
├── tests/               # Test suite
├── uploads/             # File uploads
├── docker-compose.yml   # Docker configuration
├── requirements.txt     # Python dependencies
└── README.md           # This file


## Adding New Agents
### 1. Create agent class
class MyCustomAgent(BaseAgent):
    async def execute(self, state: AgentState) -> AgentState:
        # Your agent logic here
        return state

### 2. Register agent
agent_registry.register("my_agent", MyCustomAgent)

### 3. Use in workflows
config = MyCustomAgentConfig(name="my_agent")
agent = agent_registry.create_agent("my_agent", config, db)
result = await agent.execute(initial_state)


## Database Migrations
### Create new migration
alembic revision --autogenerate -m "Add new table"

### Apply migrations
alembic upgrade head

### Rollback migrations
alembic downgrade -1


## 📈 Monitoring
Health Checks API


## Logging
### Structured logging format
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "hiring_agent.workflow",
  "message": "Workflow completed successfully",
  "workflow_id": "uuid",
  "duration_ms": 1500,
  "candidates_processed": 5
}


## 📚 Resources
### Documentation
FastAPI Documentation
LangChain Documentation
SQLAlchemy Documentation
PostgreSQL Documentation

## Built with ❤️ using FastAPI, OpenAI, and modern cloud-native tools.