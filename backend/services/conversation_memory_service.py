import json
import asyncio
import os
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from models.conversation import (
    ConversationMessage, ConversationContext, TourismEntity, 
    EntityExtractionResult, MessageRole
)

logger = logging.getLogger(__name__)

class ConversationMemoryService:
    """
    Hybrid conversation memory service
    - Recent 3 messages: Full conversation history
    - Older messages: Entity-based historical context
    - Active entities: Smart merged context
    """
    
    def __init__(self):
        self.storage_path = Path("./conversation_data/sessions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Hybrid approach configuration
        self.max_recent_messages = 3  # Full context for recent messages
        self.max_historical_entities = 10  # Entity history limit
        self.max_age_hours = 24  # Session expiry
        
        # In-memory cache for active sessions
        self.active_sessions_cache: Dict[str, ConversationContext] = {}
        
        logger.info("✅ ConversationMemoryService initialized with hybrid approach")
    
    # === CORE MESSAGE MANAGEMENT ===
    
    async def save_message(self, session_id: str, role: MessageRole, content: str, 
                          entities: Optional[Dict[str, Any]] = None,
                          sources: Optional[List[str]] = None,
                          confidence: Optional[float] = None) -> str:
        """Save a message to conversation history with hybrid storage"""
        try:
            print(f"\n📝 SAVING MESSAGE TO MEMORY:")
            print(f"   Session ID: {session_id}")
            print(f"   Role: {role.value}")
            print(f"   Content: {content[:100]}...")
            print(f"   Entities: {entities}")
            print(f"   Sources: {sources}")
            
            message_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Create message object
            message = ConversationMessage(
                message_id=message_id,
                session_id=session_id,
                role=role,
                content=content,
                timestamp=timestamp,
                entities_extracted=entities or {},
                sources_used=sources or [],
                confidence=confidence,
                metadata={}
            )
            
            # Load or create conversation context
            context = await self.get_conversation_context(session_id)
            print(f"   Current context - Total messages: {context.total_messages}")
            print(f"   Current context - Recent messages: {len(context.recent_messages)}")
            print(f"   Current context - Active entities: {context.active_entities}")
            
            # Add to recent messages (maintain max 3)
            context.recent_messages.append(message)
            if len(context.recent_messages) > self.max_recent_messages:
                # Move oldest recent message to historical entities
                oldest_message = context.recent_messages.pop(0)
                print(f"   Archiving oldest message: {oldest_message.content[:50]}...")
                await self._archive_message_to_entities(oldest_message, context)
            
            # Update context metadata
            context.total_messages += 1
            context.last_updated = timestamp
            
            # Save to file and cache
            await self._save_context_to_file(context)
            self.active_sessions_cache[session_id] = context
            
            print(f"   ✅ Message saved successfully!")
            print(f"   New total messages: {context.total_messages}")
            print(f"   Recent messages count: {len(context.recent_messages)}")
            
            logger.info(f"💾 Message saved: {role} message in session {session_id[:8]}")
            return message_id
            
        except Exception as e:
            print(f"   ❌ ERROR saving message: {e}")
            logger.error(f"❌ Failed to save message: {e}")
            raise
    
    async def get_conversation_context(self, session_id: str) -> ConversationContext:
        """Get complete conversation context with hybrid approach"""
        try:
            print(f"\n🔍 GETTING CONVERSATION CONTEXT:")
            print(f"   Session ID: {session_id}")
            
            # Check cache first
            if session_id in self.active_sessions_cache:
                cached_context = self.active_sessions_cache[session_id]
                # Check if cache is recent (< 1 hour)
                if (datetime.now() - cached_context.last_updated).seconds < 3600:
                    print(f"   ✅ Found in cache - {len(cached_context.recent_messages)} recent messages")
                    print(f"   Cache active entities: {cached_context.active_entities}")
                    return cached_context
                else:
                    print(f"   ⏰ Cache expired, loading from file...")
            
            # Load from file
            context_file = self.storage_path / f"{session_id}_context.json"
            print(f"   Looking for file: {context_file}")
            
            if context_file.exists():
                print(f"   📁 Context file exists, loading...")
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_data = json.load(f)
                context = ConversationContext(**context_data)
                
                print(f"   ✅ Loaded from file:")
                print(f"      Total messages: {context.total_messages}")
                print(f"      Recent messages: {len(context.recent_messages)}")
                print(f"      Historical entities: {len(context.historical_entities)}")
                print(f"      Active entities: {context.active_entities}")
                
                # Update cache
                self.active_sessions_cache[session_id] = context
                return context
            else:
                # Create new context
                print(f"   🆕 Creating new context for session")
                context = ConversationContext(
                    session_id=session_id,
                    total_messages=0,
                    recent_messages=[],
                    historical_entities={},
                    active_entities={},
                    last_updated=datetime.now()
                )
                
                await self._save_context_to_file(context)
                self.active_sessions_cache[session_id] = context
                print(f"   ✅ New context created and saved")
                return context
                
        except Exception as e:
            print(f"   ❌ ERROR getting context: {e}")
            logger.error(f"❌ Failed to get conversation context: {e}")
            # Return empty context as fallback
            return ConversationContext(
                session_id=session_id,
                total_messages=0,
                recent_messages=[],
                historical_entities={},
                active_entities={},
                last_updated=datetime.now()
            )
    
    # === HYBRID CONTEXT BUILDING ===
    
    async def build_hybrid_context_for_query(self, session_id: str) -> Dict[str, Any]:
        """Build optimized context for LLM query enhancement"""
        try:
            print(f"\n🏗️ BUILDING HYBRID CONTEXT FOR QUERY:")
            print(f"   Session ID: {session_id}")
            
            context = await self.get_conversation_context(session_id)
            
            # Recent conversation (full messages)
            recent_context = []
            print(f"   Processing {len(context.recent_messages)} recent messages:")
            for i, msg in enumerate(context.recent_messages[-3:]):  # Last 3 messages
                message_info = {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "sources": msg.sources_used
                }
                recent_context.append(message_info)
                print(f"      {i+1}. {msg.role.value}: {msg.content[:60]}...")
            
            # Historical entities (structured)
            historical_context = {}
            print(f"   Processing {len(context.historical_entities)} historical entities:")
            for entity_type, entity in context.historical_entities.items():
                if entity.frequency >= 2:  # Only persistent entities
                    historical_context[entity_type] = {
                        "value": entity.entity_value,
                        "confidence": entity.confidence,
                        "frequency": entity.frequency,
                        "last_mentioned": entity.last_mentioned.isoformat()
                    }
                    print(f"      {entity_type}: {entity.entity_value} (freq: {entity.frequency})")
            
            # Active entities (current session)
            active_context = dict(context.active_entities)
            print(f"   Active entities: {active_context}")
            
            hybrid_context = {
                "session_id": session_id,
                "recent_conversation": recent_context,
                "historical_preferences": historical_context,
                "active_entities": active_context,
                "total_messages": context.total_messages,
                "conversation_summary": context.conversation_summary
            }
            
            print(f"   ✅ Hybrid context built:")
            print(f"      Recent conversation: {len(recent_context)} messages")
            print(f"      Historical preferences: {len(historical_context)} entities")
            print(f"      Active entities: {len(active_context)} entities")
            print(f"      Total messages: {context.total_messages}")
            
            return hybrid_context
            
        except Exception as e:
            print(f"   ❌ ERROR building hybrid context: {e}")
            logger.error(f"❌ Failed to build hybrid context: {e}")
            return {"session_id": session_id, "recent_conversation": [], "historical_preferences": {}, "active_entities": {}}
    
    # === ENTITY MANAGEMENT ===
    
    async def update_active_entities(self, session_id: str, new_entities: Dict[str, Any]) -> None:
        """Update active entities from self-querying or user input"""
        try:
            context = await self.get_conversation_context(session_id)
            
            # Merge new entities with existing active entities
            for entity_type, entity_value in new_entities.items():
                if entity_type in context.active_entities:
                    # Update existing entity
                    if isinstance(entity_value, dict) and isinstance(context.active_entities[entity_type], dict):
                        context.active_entities[entity_type].update(entity_value)
                    else:
                        context.active_entities[entity_type] = entity_value
                else:
                    # Add new entity
                    context.active_entities[entity_type] = entity_value
            
            context.last_updated = datetime.now()
            await self._save_context_to_file(context)
            self.active_sessions_cache[session_id] = context
            
            logger.info(f"🎯 Updated active entities for session {session_id[:8]}: {list(new_entities.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update active entities: {e}")
    
    async def _archive_message_to_entities(self, message: ConversationMessage, context: ConversationContext) -> None:
        """Archive old message to historical entities"""
        try:
            # Extract entities from message content and add to historical entities
            if message.entities_extracted:
                timestamp = message.timestamp
                
                for entity_type, entity_value in message.entities_extracted.items():
                    if entity_type in context.historical_entities:
                        # Update existing entity
                        existing_entity = context.historical_entities[entity_type]
                        existing_entity.frequency += 1
                        existing_entity.last_mentioned = timestamp
                        existing_entity.source_messages.append(message.message_id)
                        
                        # Update value if more recent or higher confidence
                        if not hasattr(existing_entity, 'confidence') or existing_entity.confidence < 0.7:
                            existing_entity.entity_value = entity_value
                    else:
                        # Create new historical entity
                        context.historical_entities[entity_type] = TourismEntity(
                            entity_type=entity_type,
                            entity_value=entity_value,
                            confidence=0.8,  # Default confidence for archived entities
                            first_mentioned=timestamp,
                            last_mentioned=timestamp,
                            frequency=1,
                            source_messages=[message.message_id]
                        )
            
            logger.info(f"📚 Archived message to historical entities: {message.message_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to archive message to entities: {e}")
    
    # === FILE I/O OPERATIONS ===
    
    async def _save_context_to_file(self, context: ConversationContext) -> None:
        """Save conversation context to JSON file"""
        try:
            context_file = self.storage_path / f"{context.session_id}_context.json"
            
            # Convert to dict with proper serialization
            context_dict = context.model_dump()
            
            # Handle datetime serialization
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            # Save to file
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context_dict, f, ensure_ascii=False, indent=2, default=serialize_datetime)
            
        except Exception as e:
            logger.error(f"❌ Failed to save context to file: {e}")
    
    # === CLEANUP AND MAINTENANCE ===
    
    async def cleanup_old_sessions(self) -> int:
        """Clean up sessions older than max_age_hours"""
        try:
            cleaned_count = 0
            cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
            
            for context_file in self.storage_path.glob("*_context.json"):
                try:
                    with open(context_file, 'r', encoding='utf-8') as f:
                        context_data = json.load(f)
                    
                    last_updated = datetime.fromisoformat(context_data.get('last_updated', ''))
                    if last_updated < cutoff_time:
                        context_file.unlink()  # Delete file
                        session_id = context_data.get('session_id', '')
                        if session_id in self.active_sessions_cache:
                            del self.active_sessions_cache[session_id]
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to process {context_file}: {e}")
            
            logger.info(f"🧹 Cleaned up {cleaned_count} old sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old sessions: {e}")
            return 0
    
    # === UTILITY METHODS ===
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            context = await self.get_conversation_context(session_id)
            
            return {
                "session_id": session_id,
                "total_messages": context.total_messages,
                "recent_messages": len(context.recent_messages),
                "historical_entities": len(context.historical_entities),
                "active_entities": len(context.active_entities),
                "last_updated": context.last_updated.isoformat(),
                "session_age_hours": (datetime.now() - context.last_updated).total_seconds() / 3600
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get session stats: {e}")
            return {"error": str(e)}
    
    async def reset_session_context(self, session_id: str) -> bool:
        """Reset conversation context for session"""
        try:
            # Remove from cache
            if session_id in self.active_sessions_cache:
                del self.active_sessions_cache[session_id]
            
            # Remove context file
            context_file = self.storage_path / f"{session_id}_context.json"
            if context_file.exists():
                context_file.unlink()
            
            logger.info(f"🔄 Reset context for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to reset session context: {e}")
            return False 