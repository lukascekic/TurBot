from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/sessions", tags=["sessions"])

# In-memory storage for demo (in production, use Redis or database)
sessions: Dict[str, Dict[str, Any]] = {}

class SessionCreate(BaseModel):
    user_type: str = "client"  # "client" or "agent"
    user_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    user_type: str
    created_at: datetime
    last_active: datetime
    message_count: int

class ConversationHistory(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int

@router.post("/create", response_model=SessionResponse)
async def create_session(session_data: SessionCreate):
    """Create a new conversation session"""
    session_id = str(uuid.uuid4())
    now = datetime.now()
    
    session = {
        "session_id": session_id,
        "user_type": session_data.user_type,
        "user_id": session_data.user_id,
        "created_at": now,
        "last_active": now,
        "messages": [],
        "preferences": {}
    }
    
    sessions[session_id] = session
    
    return SessionResponse(
        session_id=session_id,
        user_type=session_data.user_type,
        created_at=now,
        last_active=now,
        message_count=0
    )

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session information"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return SessionResponse(
        session_id=session_id,
        user_type=session["user_type"],
        created_at=session["created_at"],
        last_active=session["last_active"],
        message_count=len(session["messages"])
    )

@router.get("/{session_id}/history", response_model=ConversationHistory)
async def get_conversation_history(session_id: str, limit: int = 50):
    """Get conversation history for a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    messages = session["messages"][-limit:]  # Get last N messages
    
    return ConversationHistory(
        session_id=session_id,
        messages=messages,
        total_messages=len(session["messages"])
    )

@router.post("/{session_id}/message")
async def add_message_to_session(session_id: str, message_data: Dict[str, Any]):
    """Add a message to session history"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Add timestamp to message
    message_data["timestamp"] = datetime.now()
    
    # Add to session history
    session["messages"].append(message_data)
    session["last_active"] = datetime.now()
    
    return {"status": "message_added", "total_messages": len(session["messages"])}

@router.delete("/{session_id}")
async def reset_session(session_id: str):
    """Reset/clear conversation history for a session"""
    try:
        # Remove from in-memory sessions
        if session_id in sessions:
            del sessions[session_id]
        
        # Reset conversation memory
        from services.conversation_memory_service import ConversationMemoryService
        memory_service = ConversationMemoryService()
        success = await memory_service.reset_session_context(session_id)
        
        if success:
            return {"status": "session_reset", "session_id": session_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to reset session")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting session: {str(e)}")

@router.post("/create-with-user", response_model=SessionResponse)
async def create_session_with_user(session_data: SessionCreate, user_identifier: str = None):
    """Create a new conversation session with user identification"""
    # Generate unique session ID with user context
    if user_identifier:
        session_id = f"{user_identifier}_{str(uuid.uuid4())}"
    else:
        # Fallback to timestamp + random for anonymous users
        session_id = f"anon_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:8]}"
    
    now = datetime.now()
    
    session = {
        "session_id": session_id,
        "user_type": session_data.user_type,
        "user_id": user_identifier,
        "created_at": now,
        "last_active": now,
        "messages": [],
        "preferences": {}
    }
    
    sessions[session_id] = session
    
    return SessionResponse(
        session_id=session_id,
        user_type=session_data.user_type,
        created_at=now,
        last_active=now,
        message_count=0
    )

@router.get("/user/{user_identifier}")
async def get_user_sessions(user_identifier: str):
    """Get all sessions for a specific user"""
    user_sessions = []
    for session_id, session in sessions.items():
        if session.get("user_id") == user_identifier:
            user_sessions.append({
                "session_id": session_id,
                "user_type": session["user_type"],
                "created_at": session["created_at"],
                "last_active": session["last_active"],
                "message_count": len(session["messages"])
            })
    
    return {"user_sessions": user_sessions, "total": len(user_sessions)}

@router.get("/")
async def list_active_sessions():
    """List all active sessions (for admin/debug purposes)"""
    session_list = []
    for session_id, session in sessions.items():
        session_list.append({
            "session_id": session_id,
            "user_type": session["user_type"],
            "created_at": session["created_at"],
            "last_active": session["last_active"],
            "message_count": len(session["messages"])
        })
    
    return {"active_sessions": session_list, "total": len(session_list)}

@router.post("/{session_id}/preferences")
async def update_session_preferences(session_id: str, preferences: Dict[str, Any]):
    """Update user preferences for a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    session["preferences"].update(preferences)
    session["last_active"] = datetime.now()
    
    return {"status": "preferences_updated", "preferences": session["preferences"]}

@router.get("/{session_id}/preferences")
async def get_session_preferences(session_id: str):
    """Get user preferences for a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return {"preferences": session["preferences"]} 