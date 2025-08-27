from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import Dict, List
import json
import asyncio
from uuid import UUID
from app.core.database import get_db
from datetime import datetime


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # workflow_id -> list of connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # connection -> workflow_id mapping
        self.connection_mappings: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, workflow_id: str):
        """Connect a client to workflow updates"""
        await websocket.accept()
        
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = []
        
        self.active_connections[workflow_id].append(websocket)
        self.connection_mappings[websocket] = workflow_id
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a client"""
        if websocket in self.connection_mappings:
            workflow_id = self.connection_mappings[websocket]
            self.active_connections[workflow_id].remove(websocket)
            del self.connection_mappings[websocket]
            
            # Clean up empty workflow connections
            if not self.active_connections[workflow_id]:
                del self.active_connections[workflow_id]
    
    async def send_workflow_update(self, workflow_id: str, message: dict):
        """Send update to all clients watching a specific workflow"""
        if workflow_id in self.active_connections:
            dead_connections = []
            
            for connection in self.active_connections[workflow_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    dead_connections.append(connection)
            
            # Remove dead connections
            for connection in dead_connections:
                self.disconnect(connection)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        for workflow_connections in self.active_connections.values():
            for connection in workflow_connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    pass


manager = ConnectionManager()


class WorkflowUpdateWebSocket:
    """WebSocket endpoint for workflow updates"""
    
    @staticmethod
    async def websocket_endpoint(
        websocket: WebSocket, 
        workflow_id: UUID,
        db: Session = Depends(get_db)
    ):
        """WebSocket endpoint for receiving real-time workflow updates"""
        workflow_id_str = str(workflow_id)
        
        # Verify workflow exists
        from app.models.workflow import Workflow
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            await websocket.close(code=1008, reason="Workflow not found")
            return
        
        await manager.connect(websocket, workflow_id_str)
        
        try:
            # Send initial workflow status
            await manager.send_workflow_update(workflow_id_str, {
                "type": "workflow_status",
                "data": {
                    "workflow_id": workflow_id_str,
                    "current_stage": workflow.current_stage,
                    "status": workflow.status,
                    "progress_percentage": workflow.progress_percentage
                }
            })
            
            # Keep connection alive and handle incoming messages
            while True:
                try:
                    # Wait for messages from client (like ping/pong)
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    message = json.loads(data)
                    
                    # Handle different message types
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    elif message.get("type") == "subscribe_candidate":
                        # Subscribe to specific candidate updates
                        candidate_id = message.get("candidate_id")
                        await handle_candidate_subscription(websocket, candidate_id, db)
                        
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    await websocket.send_text(json.dumps({"type": "heartbeat"}))
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                    
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            print(f"WebSocket error: {e}")
            manager.disconnect(websocket)


async def handle_candidate_subscription(websocket: WebSocket, candidate_id: str, db: Session):
    """Handle subscription to specific candidate updates"""
    from app.models.candidate import Candidate
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    
    if candidate:
        await websocket.send_text(json.dumps({
            "type": "candidate_status",
            "data": {
                "candidate_id": candidate_id,
                "name": candidate.name,
                "current_stage": candidate.current_stage,
                "overall_score": candidate.overall_score,
                "match_percentage": candidate.match_percentage
            }
        }))


# Helper functions for sending updates from other parts of the application
async def notify_workflow_stage_change(workflow_id: str, new_stage: str, additional_data: dict = None):
    """Notify clients of workflow stage changes"""
    message = {
        "type": "stage_change",
        "data": {
            "workflow_id": workflow_id,
            "new_stage": new_stage,
            "timestamp": datetime.now().isoformat(),
            **(additional_data or {})
        }
    }
    await manager.send_workflow_update(workflow_id, message)


async def notify_candidate_evaluation_complete(workflow_id: str, candidate_id: str, evaluation_results: dict):
    """Notify clients when candidate evaluation is complete"""
    message = {
        "type": "candidate_evaluated",
        "data": {
            "workflow_id": workflow_id,
            "candidate_id": candidate_id,
            "evaluation_results": evaluation_results,
            "timestamp": datetime.now().isoformat()
        }
    }
    await manager.send_workflow_update(workflow_id, message)

async def notify_human_decision_required(workflow_id: str, decision_type: str, candidates: List[dict]):
    """Notify clients that human decision is required"""
    message = {
        "type": "human_decision_required",
        "data": {
            "workflow_id": workflow_id,
            "decision_type": decision_type,
            "candidates": candidates,
            "timestamp": datetime.now().isoformat()
        }
    }
    await manager.send_workflow_update(workflow_id, message)

async def notify_interview_scheduled(workflow_id: str, candidate_id: str, interview_details: dict):
    """Notify clients when interview is scheduled"""
    message = {
        "type": "interview_scheduled",
        "data": {
            "workflow_id": workflow_id,
            "candidate_id": candidate_id,
            "interview_details": interview_details,
            "timestamp": datetime.now().isoformat()
        }
    }
    await manager.send_workflow_update(workflow_id, message)
