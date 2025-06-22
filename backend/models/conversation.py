from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    """Message role enumeration"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ConversationMessage(BaseModel):
    """Individual conversation message with metadata"""
    message_id: str
    session_id: str
    role: MessageRole
    content: str
    timestamp: datetime
    entities_extracted: Dict[str, Any] = Field(default_factory=dict)
    sources_used: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TourismEntity(BaseModel):
    """Tourism-specific entity with tracking information"""
    entity_type: str  # destination, price_range, travel_dates, etc.
    entity_value: Any
    confidence: float
    first_mentioned: datetime
    last_mentioned: datetime
    frequency: int = 1
    source_messages: List[str] = Field(default_factory=list)  # Message IDs
    
class ConversationContext(BaseModel):
    """Complete conversation context with hybrid approach"""
    session_id: str
    total_messages: int
    
    # HYBRID APPROACH:
    recent_messages: List[ConversationMessage] = Field(default_factory=list)  # Last 3 full messages
    historical_entities: Dict[str, TourismEntity] = Field(default_factory=dict)  # Entity-based history
    active_entities: Dict[str, Any] = Field(default_factory=dict)  # Current context
    
    conversation_summary: str = ""
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime
    context_switch_detected: bool = False

class EntityExtractionResult(BaseModel):
    """Result from entity extraction process"""
    entities: Dict[str, TourismEntity]
    confidence: float
    extraction_method: str  # "llm", "rule_based", "hybrid"
    processing_time: float

class ContextEnhancementResult(BaseModel):
    """Result from context-aware query enhancement"""
    original_query: str
    enhanced_query: str
    implicit_filters: Dict[str, Any] = Field(default_factory=dict)
    context_used: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    enhancement_method: str 