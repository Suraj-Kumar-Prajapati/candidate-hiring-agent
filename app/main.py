from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.core.config import settings
from app.core.database import db_manager
from app.api.v1.api import api_router
from app.api.websockets.workflow_updates import WorkflowUpdateWebSocket

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Powered Hiring Agent Platform with LangGraph Workflows",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


# WebSocket endpoints
@app.websocket("/ws/workflow/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    await WorkflowUpdateWebSocket.websocket_endpoint(websocket, workflow_id)

# Static files (for uploaded resumes, etc.)
app.mount("/static", StaticFiles(directory="uploads"), name="static")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Create database tables
    db_manager.create_tables()
    print("Database tables created/verified")
    
    # Initialize agent registry
    from app.agents.resume_evaluator import ResumeEvaluatorAgent
    from app.agents.base_agent import agent_registry
    
    agent_registry.register("resume_evaluator", ResumeEvaluatorAgent)
    print("Agents registered")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down application")


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
