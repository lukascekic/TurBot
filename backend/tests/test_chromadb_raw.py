#!/usr/bin/env python3
"""
Test ChromaDB directly without embeddings
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.vector_service import VectorService

def test_chromadb_raw():
    """Test ChromaDB directly without vector search"""
    print("🔍 TESTING CHROMADB RAW ACCESS")
    print("=" * 60)
    
    vector_service = VectorService()
    
    # Test 1: Get all documents
    print("\n1️⃣ GET ALL DOCUMENTS")
    all_results = vector_service.collection.get()
    print(f"   Total documents: {len(all_results['ids'])}")
    
    # Test 2: Get documents with location filter
    print("\n2️⃣ GET DOCUMENTS WITH LOCATION=Istanbul")
    try:
        istanbul_results = vector_service.collection.get(
            where={"location": "Istanbul"}
        )
        print(f"   Istanbul documents: {len(istanbul_results['ids'])}")
        
        if len(istanbul_results['ids']) > 0:
            print("   ✅ Found Istanbul documents!")
            # Show first few
            for i in range(min(3, len(istanbul_results['ids']))):
                metadata = istanbul_results['metadatas'][i]
                print(f"      Document {i+1}: {metadata}")
        else:
            print("   ❌ No Istanbul documents found!")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Get documents with location filter (case variations)
    print("\n3️⃣ TEST CASE VARIATIONS")
    test_locations = ["Istanbul", "istanbul", "ISTANBUL"]
    
    for location in test_locations:
        try:
            results = vector_service.collection.get(
                where={"location": location}
            )
            print(f"   location='{location}': {len(results['ids'])} documents")
        except Exception as e:
            print(f"   location='{location}': ERROR - {e}")
    
    # Test 4: Query with similarity search (no filters)
    print("\n4️⃣ SIMILARITY SEARCH WITHOUT FILTERS")
    try:
        # Create a simple embedding for testing
        test_embedding = vector_service.create_embedding("Istanbul hotel")
        
        similarity_results = vector_service.collection.query(
            query_embeddings=[test_embedding],
            n_results=5
        )
        
        print(f"   Similarity search results: {len(similarity_results['ids'][0])}")
        
        if len(similarity_results['ids'][0]) > 0:
            print("   ✅ Similarity search works!")
            # Show results with their locations
            for i, metadata in enumerate(similarity_results['metadatas'][0]):
                distance = similarity_results['distances'][0][i]
                location = metadata.get('location', 'N/A')
                print(f"      Result {i+1}: location='{location}', distance={distance:.4f}")
        else:
            print("   ❌ No similarity search results!")
            
    except Exception as e:
        print(f"   ❌ Similarity search error: {e}")
    
    # Test 5: Query with similarity search + location filter
    print("\n5️⃣ SIMILARITY SEARCH WITH LOCATION FILTER")
    try:
        similarity_filtered_results = vector_service.collection.query(
            query_embeddings=[test_embedding],
            n_results=5,
            where={"location": "Istanbul"}
        )
        
        print(f"   Filtered similarity search results: {len(similarity_filtered_results['ids'][0])}")
        
        if len(similarity_filtered_results['ids'][0]) > 0:
            print("   ✅ Filtered similarity search works!")
            for i, metadata in enumerate(similarity_filtered_results['metadatas'][0]):
                distance = similarity_filtered_results['distances'][0][i]
                location = metadata.get('location', 'N/A')
                print(f"      Result {i+1}: location='{location}', distance={distance:.4f}")
        else:
            print("   ❌ No filtered similarity search results!")
            print("   💡 This indicates the problem is with location filtering in similarity search")
            
    except Exception as e:
        print(f"   ❌ Filtered similarity search error: {e}")

if __name__ == "__main__":
    test_chromadb_raw() 