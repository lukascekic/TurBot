import asyncio
import uuid
from datetime import datetime

# Add parent directory to path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.conversation_memory_service import ConversationMemoryService
from models.conversation import MessageRole

async def test_session_isolation():
    """
    Test that different users have completely isolated conversation histories
    """
    print("\n🧪 Testing Session Isolation")
    
    try:
        memory_service = ConversationMemoryService()
        
        # Create sessions for different users
        user1_session = f"user1_{uuid.uuid4().hex[:8]}"
        user2_session = f"user2_{uuid.uuid4().hex[:8]}"
        
        print(f"👤 User 1 Session: {user1_session}")
        print(f"👤 User 2 Session: {user2_session}")
        
        # User 1 conversation
        print("\n1️⃣ User 1 starts conversation about Rome...")
        await memory_service.save_message(
            session_id=user1_session,
            role=MessageRole.USER,
            content="Tražim hotel u Rimu za 2 osobe",
            entities={"destination": "Rim", "group_size": 2}
        )
        
        await memory_service.update_active_entities(user1_session, {
            "destination": "Rim",
            "group_size": 2,
            "budget_max": 300
        })
        
        await memory_service.save_message(
            session_id=user1_session,
            role=MessageRole.ASSISTANT,
            content="Pronašao sam odlične hotele u Rimu za 2 osobe..."
        )
        
        # User 2 conversation (completely different)
        print("2️⃣ User 2 starts conversation about Paris...")
        await memory_service.save_message(
            session_id=user2_session,
            role=MessageRole.USER,
            content="Potreban mi je apartman u Parizu za 4 osobe",
            entities={"destination": "Pariz", "group_size": 4}
        )
        
        await memory_service.update_active_entities(user2_session, {
            "destination": "Pariz", 
            "group_size": 4,
            "budget_max": 500
        })
        
        await memory_service.save_message(
            session_id=user2_session,
            role=MessageRole.ASSISTANT,
            content="Evo odličnih apartmana u Parizu za 4 osobe..."
        )
        
        # Test isolation
        print("\n3️⃣ Testing conversation isolation...")
        
        # Get contexts for both users
        user1_context = await memory_service.build_hybrid_context_for_query(user1_session)
        user2_context = await memory_service.build_hybrid_context_for_query(user2_session)
        
        print(f"   User 1 - Destination: {user1_context['active_entities'].get('destination')}")
        print(f"   User 1 - Group size: {user1_context['active_entities'].get('group_size')}")
        print(f"   User 1 - Budget: {user1_context['active_entities'].get('budget_max')}")
        
        print(f"   User 2 - Destination: {user2_context['active_entities'].get('destination')}")
        print(f"   User 2 - Group size: {user2_context['active_entities'].get('group_size')}")
        print(f"   User 2 - Budget: {user2_context['active_entities'].get('budget_max')}")
        
        # Verify isolation
        assert user1_context['active_entities'].get('destination') == "Rim", "User 1 should have Rome"
        assert user2_context['active_entities'].get('destination') == "Pariz", "User 2 should have Paris"
        
        assert user1_context['active_entities'].get('group_size') == 2, "User 1 should have 2 people"
        assert user2_context['active_entities'].get('group_size') == 4, "User 2 should have 4 people"
        
        assert user1_context['active_entities'].get('budget_max') == 300, "User 1 should have 300 budget"
        assert user2_context['active_entities'].get('budget_max') == 500, "User 2 should have 500 budget"
        
        # Verify no cross-contamination
        assert "Pariz" not in str(user1_context), "User 1 should not see Paris data"
        assert "Rim" not in str(user2_context), "User 2 should not see Rome data"
        
        print("   ✅ Sessions are properly isolated!")
        
        # Test incomplete query context (should only use own context)
        print("\n4️⃣ Testing context-aware queries...")
        
        # User 1 asks incomplete question
        user1_incomplete_context = await memory_service.build_hybrid_context_for_query(user1_session)
        
        # Verify User 1 gets Rome context, not Paris
        has_rome_context = any(
            "rim" in msg["content"].lower() or "rome" in msg["content"].lower()
            for msg in user1_incomplete_context["recent_conversation"]
        )
        
        has_paris_context = any(
            "pariz" in msg["content"].lower() or "paris" in msg["content"].lower()
            for msg in user1_incomplete_context["recent_conversation"]
        )
        
        assert has_rome_context, "User 1 should have Rome context"
        assert not has_paris_context, "User 1 should NOT have Paris context"
        
        print("   ✅ Context queries are properly isolated!")
        
        # Test session reset
        print("\n5️⃣ Testing session reset...")
        
        # Reset User 1 session
        reset_success = await memory_service.reset_session_context(user1_session)
        assert reset_success, "Session reset should succeed"
        
        # Verify User 1 context is cleared
        user1_reset_context = await memory_service.build_hybrid_context_for_query(user1_session)
        assert len(user1_reset_context['active_entities']) == 0, "User 1 entities should be cleared"
        assert user1_reset_context['total_messages'] == 0, "User 1 messages should be cleared"
        
        # Verify User 2 context is unchanged
        user2_unchanged_context = await memory_service.build_hybrid_context_for_query(user2_session)
        assert user2_unchanged_context['active_entities'].get('destination') == "Pariz", "User 2 should still have Paris"
        assert user2_unchanged_context['total_messages'] > 0, "User 2 messages should be preserved"
        
        print("   ✅ Session reset works correctly!")
        
        # Cleanup
        await memory_service.reset_session_context(user2_session)
        
        print("✅ All session isolation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Session isolation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_session_collision_prevention():
    """
    Test that session IDs are properly unique and prevent collisions
    """
    print("\n🧪 Testing Session Collision Prevention")
    
    try:
        memory_service = ConversationMemoryService()
        
        # Simulate multiple users creating sessions at the same time
        sessions = []
        for i in range(10):
            # Simulate different user identifiers
            user_id = f"user_{i}"
            session_id = f"{user_id}_{uuid.uuid4()}"
            sessions.append(session_id)
            
            # Each user saves a message with their identity
            await memory_service.save_message(
                session_id=session_id,
                role=MessageRole.USER,
                content=f"Hello from user {i}",
                entities={"user_id": user_id}
            )
        
        print(f"   Created {len(sessions)} unique sessions")
        
        # Verify all sessions are unique
        assert len(set(sessions)) == len(sessions), "All session IDs should be unique"
        
        # Verify each session has correct content
        for i, session_id in enumerate(sessions):
            context = await memory_service.build_hybrid_context_for_query(session_id)
            
            # Check that this session only contains its own user's message
            user_messages = [
                msg for msg in context["recent_conversation"] 
                if msg["role"] == "user"
            ]
            
            assert len(user_messages) == 1, f"Session {i} should have exactly 1 user message"
            assert f"user {i}" in user_messages[0]["content"], f"Session {i} should contain its own user message"
            
            # Verify no cross-contamination
            for j in range(10):
                if i != j:
                    assert f"user {j}" not in str(context), f"Session {i} should not contain user {j} data"
        
        # Cleanup
        for session_id in sessions:
            await memory_service.reset_session_context(session_id)
        
        print("✅ Session collision prevention test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Session collision test failed: {e}")
        return False

async def main():
    """Run all session isolation tests"""
    print("🚀 Starting Session Isolation Tests")
    print("=" * 60)
    
    tests = [
        test_session_isolation,
        test_session_collision_prevention
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
        print("🎉 All session isolation tests passed!")
    else:
        print("⚠️  Some tests failed - check session management")

if __name__ == "__main__":
    asyncio.run(main()) 