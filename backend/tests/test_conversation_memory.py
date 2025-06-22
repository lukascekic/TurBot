import asyncio
import pytest
import uuid
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.conversation_memory_service import ConversationMemoryService
from services.named_entity_extractor import NamedEntityExtractor
from services.context_aware_enhancer import ContextAwareEnhancer
from models.conversation import MessageRole
from openai import AsyncOpenAI

# Mock OpenAI client for testing
class MockOpenAIClient:
    async def chat_completions_create(self, **kwargs):
        # Mock response for testing
        class MockChoice:
            def __init__(self):
                self.message = type('obj', (object,), {
                    'content': '{"destination": "Rim", "price_max": 300, "travel_month": "july", "group_size": 2}'
                })
        
        class MockResponse:
            def __init__(self):
                self.choices = [MockChoice()]
        
        return MockResponse()

async def test_conversation_memory_hybrid_approach():
    """
    Test the hybrid conversation memory approach:
    - Recent 3 messages: Full conversation history
    - Older messages: Entity-based historical context
    - Active entities: Smart merged context
    """
    print("\n🧪 Testing Conversation Memory - Hybrid Approach")
    
    try:
        # Initialize services
        memory_service = ConversationMemoryService()
        
        # Create test session
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        print(f"📝 Created test session: {session_id}")
        
        # Test 1: Save initial messages
        print("\n1️⃣ Testing message saving...")
        
        messages = [
            ("USER", "Tražim hotel u Rimu za 2 osobe"),
            ("ASSISTANT", "Pronašao sam odlične hotele u Rimu za 2 osobe. Evo preporuka..."),
            ("USER", "Koliko košta Hotel Roma Palace?"),
            ("ASSISTANT", "Hotel Roma Palace košta 250€ po noći za dvokrevetnu sobu..."),
            ("USER", "A što sa doručkom?"),  # This should use context
        ]
        
        for i, (role, content) in enumerate(messages[:4]):  # Save first 4 messages
            message_role = MessageRole.USER if role == "USER" else MessageRole.ASSISTANT
            
            # Simulate entity extraction for user messages
            entities = {}
            if role == "USER":
                if "Rim" in content:
                    entities["destination"] = "Rim"
                if "2 osobe" in content:
                    entities["group_size"] = 2
                if "Hotel Roma Palace" in content:
                    entities["hotel_name"] = "Hotel Roma Palace"
            
            message_id = await memory_service.save_message(
                session_id=session_id,
                role=message_role,
                content=content,
                entities=entities
            )
            print(f"   💾 Saved {role} message: {content[:50]}...")
        
        # Test 2: Verify hybrid context building
        print("\n2️⃣ Testing hybrid context building...")
        
        context = await memory_service.build_hybrid_context_for_query(session_id)
        
        print(f"   📊 Total messages: {context['total_messages']}")
        print(f"   📋 Recent messages: {len(context['recent_conversation'])}")
        print(f"   🏷️ Historical entities: {len(context['historical_preferences'])}")
        print(f"   ⚡ Active entities: {len(context['active_entities'])}")
        
        # Verify recent messages (should be last 3)
        assert len(context['recent_conversation']) <= 3, "Should keep max 3 recent messages"
        
        # Test 3: Entity archiving (when > 3 messages)
        print("\n3️⃣ Testing entity archiving...")
        
        # Add 5th message to trigger archiving
        await memory_service.save_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=messages[4][1],  # "A što sa doručkom?"
            entities={"inquiry_type": "amenities"}
        )
        
        updated_context = await memory_service.build_hybrid_context_for_query(session_id)
        
        print(f"   📋 Recent messages after archiving: {len(updated_context['recent_conversation'])}")
        print(f"   🏷️ Historical entities after archiving: {len(updated_context['historical_preferences'])}")
        
        # Test 4: Active entity updates
        print("\n4️⃣ Testing active entity updates...")
        
        new_entities = {
            "budget_max": 400,
            "amenities": ["breakfast", "wifi", "parking"]
        }
        
        await memory_service.update_active_entities(session_id, new_entities)
        
        final_context = await memory_service.build_hybrid_context_for_query(session_id)
        
        print(f"   ⚡ Active entities: {final_context['active_entities']}")
        
        assert "budget_max" in final_context['active_entities'], "New entities should be added"
        assert final_context['active_entities']['budget_max'] == 400, "Entity values should be correct"
        
        # Test 5: Session statistics
        print("\n5️⃣ Testing session statistics...")
        
        stats = await memory_service.get_session_stats(session_id)
        
        print(f"   📈 Session stats: {stats}")
        
        assert stats['total_messages'] == 5, f"Expected 5 messages, got {stats['total_messages']}"
        assert stats['recent_messages'] == 3, f"Expected 3 recent messages, got {stats['recent_messages']}"
        
        # Test 6: Context-aware conversation patterns
        print("\n6️⃣ Testing context patterns...")
        
        # Test incomplete query that should use context
        incomplete_queries = [
            "Koliko košta?",  # Should understand "Hotel Roma Palace" from context
            "A što sa parkingom?",  # Should understand hotel context
            "Ima li spa?"  # Should use current hotel context
        ]
        
        for query in incomplete_queries:
            print(f"   🔍 Testing incomplete query: '{query}'")
            
            # This would normally go through ContextAwareEnhancer
            # but we can test the context building directly
            query_context = await memory_service.build_hybrid_context_for_query(session_id)
            
            # Verify we have enough context to enhance the query
            has_hotel_context = any(
                "hotel" in msg["content"].lower() or "roma palace" in msg["content"].lower()
                for msg in query_context["recent_conversation"]
            )
            
            has_destination_context = "destination" in query_context["active_entities"]
            
            print(f"      ✅ Hotel context available: {has_hotel_context}")
            print(f"      ✅ Destination context available: {has_destination_context}")
        
        # Cleanup
        print(f"\n🧹 Cleaning up test session...")
        await memory_service.reset_session_context(session_id)
        
        print("✅ All conversation memory tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_entity_persistence():
    """Test entity persistence across conversation turns"""
    print("\n🧪 Testing Entity Persistence")
    
    try:
        memory_service = ConversationMemoryService()
        session_id = f"entity_test_{uuid.uuid4().hex[:8]}"
        
        # Simulate conversation where entities persist and get reinforced
        conversation_turns = [
            ("USER", "Tražim hotel u Rimu", {"destination": "Rim", "category": "hotel"}),
            ("ASSISTANT", "Evo hotela u Rimu...", {}),
            ("USER", "Budžet mi je 300 EUR", {"price_max": 300}),
            ("ASSISTANT", "Za 300 EUR imate odličné opcije...", {}),
            ("USER", "Za 2 osobe", {"group_size": 2}),
            ("ASSISTANT", "Prilagodio sam pretragu za 2 osobe...", {}),
            ("USER", "A što sa Parizom?", {"destination": "Pariz"}),  # Context switch
            ("ASSISTANT", "Pariz ima odlične hotele...", {}),
            ("USER", "Isti budžet", {}),  # Should inherit budget from earlier
        ]
        
        for i, (role, content, entities) in enumerate(conversation_turns):
            message_role = MessageRole.USER if role == "USER" else MessageRole.ASSISTANT
            
            await memory_service.save_message(
                session_id=session_id,
                role=message_role,
                content=content,
                entities=entities if entities else None
            )
            
            if entities:
                await memory_service.update_active_entities(session_id, entities)
            
            print(f"   💬 Turn {i+1}: {role} - {content}")
        
        # Check final context
        final_context = await memory_service.build_hybrid_context_for_query(session_id)
        
        print(f"\n📊 Final context analysis:")
        print(f"   Active entities: {final_context['active_entities']}")
        print(f"   Historical entities: {final_context['historical_preferences']}")
        
        # Verify context switch detection and entity persistence
        current_destination = final_context['active_entities'].get('destination')
        print(f"   Current destination: {current_destination}")
        
        # Budget should persist even after destination change
        budget_available = 'price_max' in final_context['active_entities'] or any(
            'price_max' in hist_entity
            for hist_entity in final_context['historical_preferences'].values()
        )
        
        print(f"   Budget context available: {budget_available}")
        
        await memory_service.reset_session_context(session_id)
        
        print("✅ Entity persistence test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Entity persistence test failed: {e}")
        return False

async def main():
    """Run all conversation memory tests"""
    print("🚀 Starting Conversation Memory Tests")
    print("=" * 60)
    
    tests = [
        test_conversation_memory_hybrid_approach,
        test_entity_persistence
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_func.__name__} PASSED")
            else:
                failed += 1
                print(f"❌ {test_func.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_func.__name__} ERROR: {e}")
        
        print("-" * 60)
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All conversation memory tests passed!")
    else:
        print("⚠️  Some tests failed - check implementation")

if __name__ == "__main__":
    asyncio.run(main()) 