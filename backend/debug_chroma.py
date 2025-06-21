#!/usr/bin/env python3
"""
Debug ChromaDB connectivity and content
"""

import os
from dotenv import load_dotenv
load_dotenv()

import chromadb
from services.vector_service import VectorService

def debug_chromadb():
    print("🔍 Debug ChromaDB\n")
    
    # 1. Test direct ChromaDB connection
    print("1. Testing direct ChromaDB connection...")
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        print(f"   ✅ Found {len(collections)} collections")
        for col in collections:
            print(f"     - {col.name}")
    except Exception as e:
        print(f"   ❌ ChromaDB connection failed: {e}")
        return
    
    # 2. Test collection access
    print("\n2. Testing collection access...")
    try:
        collection = client.get_collection("tourism_documents")
        count = collection.count()
        print(f"   ✅ Collection has {count} documents")
        
        # Get first few documents
        if count > 0:
            sample = collection.get(limit=3)
            print(f"   📄 Sample document IDs: {sample['ids'][:3] if sample['ids'] else 'None'}")
            if sample['documents']:
                print(f"   📄 Sample text: {sample['documents'][0][:100]}...")
    except Exception as e:
        print(f"   ❌ Collection access failed: {e}")
        return
    
    # 3. Test VectorService
    print("\n3. Testing VectorService...")
    try:
        vector_service = VectorService()
        stats = vector_service.get_collection_stats()
        print(f"   ✅ VectorService stats: {stats}")
    except Exception as e:
        print(f"   ❌ VectorService failed: {e}")
        return
    
    # 4. Test embedding creation
    print("\n4. Testing embedding creation...")
    try:
        vector_service = VectorService()
        embedding = vector_service.create_embedding("test query")
        print(f"   ✅ Created embedding with {len(embedding)} dimensions")
    except Exception as e:
        print(f"   ❌ Embedding creation failed: {e}")
        return
    
    # 5. Test raw query
    print("\n5. Testing raw ChromaDB query...")
    try:
        vector_service = VectorService()
        test_embedding = vector_service.create_embedding("Istanbul")
        
        # Direct ChromaDB query
        results = collection.query(
            query_embeddings=[test_embedding],
            n_results=3
        )
        
        print(f"   ✅ Raw query returned {len(results['documents'][0]) if results['documents'] else 0} results")
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i] if results['distances'] else 0
                print(f"     {i+1}. Distance: {distance:.3f} | {doc[:60]}...")
    except Exception as e:
        print(f"   ❌ Raw query failed: {e}")

if __name__ == "__main__":
    debug_chromadb() 