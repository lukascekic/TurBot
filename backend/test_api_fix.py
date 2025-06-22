#!/usr/bin/env python3
"""
Test API to verify fixes for conversation memory and response generation
"""

import requests
import json

def test_chat_api():
    """Test the chat API with conversation memory"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 TESTING CONVERSATION MEMORY FIXES")
    print("=" * 50)
    
    # Test 1: First message
    print("\n1️⃣ FIRST MESSAGE: Amsterdam query")
    
    payload1 = {
        "message": "Jel imas nesto za Amsterdam?",
        "session_id": "test_session_memory_001",
        "user_type": "client"
    }
    
    try:
        response1 = requests.post(f"{base_url}/chat", json=payload1, timeout=30)
        print(f"Status: {response1.status_code}")
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"✅ SUCCESS!")
            print(f"Response length: {len(data1['response'])} characters")
            print(f"Confidence: {data1['confidence']:.2f}")
            print(f"Sources: {len(data1['sources'])}")
            print(f"Session ID: {data1['session_id']}")
            print(f"Response preview: {data1['response'][:100]}...")
            
            if data1['active_entities']:
                print(f"Active entities: {data1['active_entities']}")
        else:
            print(f"❌ FAILED: {response1.text}")
            return
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return
    
    # Test 2: Follow-up message (should use conversation context)
    print("\n2️⃣ FOLLOW-UP MESSAGE: Details request")
    
    payload2 = {
        "message": "Jel mozes da mi das detaljniji opis putovanja za prvi maj?",
        "session_id": "test_session_memory_001",  # Same session!
        "user_type": "client"
    }
    
    try:
        response2 = requests.post(f"{base_url}/chat", json=payload2, timeout=30)
        print(f"Status: {response2.status_code}")
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"✅ SUCCESS!")
            print(f"Response length: {len(data2['response'])} characters")
            print(f"Confidence: {data2['confidence']:.2f}")
            print(f"Sources: {len(data2['sources'])}")
            print(f"Response preview: {data2['response'][:100]}...")
            
            # Check if conversation context is being used
            if data2['conversation_context']:
                print(f"Conversation context: {data2['conversation_context']}")
            
            if data2['active_entities']:
                print(f"Active entities: {data2['active_entities']}")
                
            # Check if response mentions Amsterdam (context aware)
            if "amsterdam" in data2['response'].lower():
                print("🧠 CONTEXT AWARENESS: ✅ Response mentions Amsterdam!")
            else:
                print("⚠️  CONTEXT AWARENESS: Response doesn't mention Amsterdam")
        else:
            print(f"❌ FAILED: {response2.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 TEST COMPLETED")
    print("Check backend terminal for detailed conversation memory logs!")

if __name__ == "__main__":
    test_chat_api() 