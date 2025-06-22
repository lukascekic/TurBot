#!/usr/bin/env python3
"""
Debug test to simulate the exact conversation flow from chat_log.txt
to see what conversation memory logs show us.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add current directory to Python path so we can import our modules
sys.path.append(str(Path(__file__).parent))

from services.conversation_memory_service import ConversationMemoryService, MessageRole
from services.self_querying_service import SelfQueryingService
from services.query_expansion_service import QueryExpansionService
from services.response_generator import ResponseGenerator
from services.vector_service import VectorService
from services.named_entity_extractor import NamedEntityExtractor
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_conversation_debug():
    """Test the exact conversation flow from chat_log.txt"""
    
    print("=" * 80)
    print("🔍 CONVERSATION MEMORY DEBUG TEST")
    print("Simulating the exact flow from chat_log.txt")
    print("=" * 80)
    
    # Initialize OpenAI client
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Initialize services
    conversation_memory_service = ConversationMemoryService()
    vector_service = VectorService()
    named_entity_extractor = NamedEntityExtractor(openai_client)
    self_querying_service = SelfQueryingService(openai_client)
    # Manually set conversation_memory_service for the test
    self_querying_service.conversation_memory_service = conversation_memory_service
    query_expansion_service = QueryExpansionService(openai_client)
    response_generator = ResponseGenerator(openai_client)
    
    # Test session ID (similar to what would be generated)
    session_id = "test_session_debug_001"
    
    print(f"\n📍 Using session ID: {session_id}")
    
    # ===============================
    # FIRST MESSAGE: "Jel imas nesto za Amsterdam?"
    # ===============================
    
    print("\n" + "="*60)
    print("FIRST MESSAGE")
    print("="*60)
    
    user_message_1 = "Jel imas nesto za Amsterdam?"
    print(f"User: {user_message_1}")
    
    # Process first message
    try:
        # Save user message to memory
        await conversation_memory_service.save_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=user_message_1
        )
        
        # Process with self-querying + context
        structured_query_1 = await self_querying_service.parse_query_with_context(
            user_message_1, session_id
        )
        
        # Simulate search results (minimal for focus on memory)
        print(f"\n🔧 Simulating search and response generation...")
        
        # Simulate AI response
        ai_response_1 = """Zdravo! Pronašao sam nekoliko opcija za putovanje u Amsterdam u periodu od 30. aprila do 4. maja 2025. godine, koje bi mogle biti zanimljive.

DOSTUPNE OPCIJE:
1. **Amsterdam – Prvi Maj 2025**
   - **Datum:** 30. aprila - 4. maja 2025.
   - **Trajanje:** 5 dana / 4 noćenja
   - **Tip:** Direktan let
   - **Uključeno:** Panoramsko razgledanje grada
   - **Cena:** 1504 EUR (detalji u cenovniku)

Da li vas neka od ovih opcija zanima?"""
        
        # Save AI response to memory
        await conversation_memory_service.save_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=ai_response_1,
            sources=["Amsterdam_PRVI_MAJ_2025_Direktan_let_30.04.-04.05.2025._Cenovnik_1504.pdf"]
        )
        
        print(f"AI: {ai_response_1[:100]}...")
        
    except Exception as e:
        print(f"❌ ERROR in first message: {e}")
        return
    
    # ===============================
    # SECOND MESSAGE: "Jel mozes da mi das detaljniji opis putovanja za prvi maj?"
    # ===============================
    
    print("\n" + "="*60)
    print("SECOND MESSAGE")
    print("="*60)
    
    user_message_2 = "Jel mozes da mi das detaljniji opis putovanja za prvi maj?"
    print(f"User: {user_message_2}")
    
    # Process second message
    try:
        # Save user message to memory
        await conversation_memory_service.save_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=user_message_2
        )
        
        # THIS IS THE KEY PART - does it use context from previous message?
        structured_query_2 = await self_querying_service.parse_query_with_context(
            user_message_2, session_id
        )
        
        print(f"\n🧠 MEMORY ANALYSIS:")
        print(f"   Should have context of Amsterdam from first message")
        print(f"   Should recognize 'putovanja za prvi maj' refers to Amsterdam trip")
        print(f"   Should enhance query with Amsterdam context")
        
        # Get conversation context to see what's available
        conversation_context = await conversation_memory_service.build_hybrid_context_for_query(session_id)
        
        print(f"\n📊 FINAL MEMORY STATE:")
        print(f"   Total messages: {conversation_context.get('total_messages', 0)}")
        print(f"   Recent conversation: {len(conversation_context.get('recent_conversation', []))}")
        print(f"   Active entities: {conversation_context.get('active_entities', {})}")
        
        if conversation_context.get('recent_conversation'):
            print(f"\n💬 RECENT CONVERSATION IN MEMORY:")
            for i, msg in enumerate(conversation_context['recent_conversation']):
                print(f"   {i+1}. {msg['role']}: {msg['content'][:80]}...")
        
        print(f"\n🎯 EXPECTED BEHAVIOR:")
        print(f"   - Query should be enhanced with 'Amsterdam' context")
        print(f"   - AI should understand 'putovanja za prvi maj' = Amsterdam trip")
        print(f"   - Response should reference previous conversation")
        
    except Exception as e:
        print(f"❌ ERROR in second message: {e}")
    
    print("\n" + "="*80)
    print("DEBUG TEST COMPLETED")
    print("Review the logs above to see if conversation memory is working")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_conversation_debug()) 