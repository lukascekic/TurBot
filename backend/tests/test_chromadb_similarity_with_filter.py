#!/usr/bin/env python3
"""
Test ChromaDB similarity search with and without filters
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.vector_service import VectorService

def test_similarity_with_filters():
    """Test similarity search with and without filters"""
    print("🔍 TESTING SIMILARITY SEARCH WITH FILTERS")
    print("=" * 60)
    
    vector_service = VectorService()
    
    # Create test embedding
    test_query = "hotel smeštaj"
    query_embedding = vector_service.create_embedding(test_query)
    print(f"✅ Created embedding for: '{test_query}'")
    
    # Test 1: Similarity search WITHOUT filter
    print(f"\n1️⃣ SIMILARITY SEARCH WITHOUT FILTER")
    results1 = vector_service.collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )
    print(f"   Results: {len(results1['ids'][0])} documents")
    if results1['ids'][0]:
        print(f"   First result location: {results1['metadatas'][0][0].get('location', 'N/A')}")
    
    # Test 2: Similarity search WITH Amsterdam filter
    print(f"\n2️⃣ SIMILARITY SEARCH WITH Amsterdam FILTER")
    results2 = vector_service.collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={"location": "Amsterdam"}
    )
    print(f"   Results: {len(results2['ids'][0])} documents")
    if results2['ids'][0]:
        print(f"   First result location: {results2['metadatas'][0][0].get('location', 'N/A')}")
    
    # Test 3: Similarity search WITH Istanbul filter
    print(f"\n3️⃣ SIMILARITY SEARCH WITH Istanbul FILTER")
    results3 = vector_service.collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={"location": "Istanbul"}
    )
    print(f"   Results: {len(results3['ids'][0])} documents")
    if results3['ids'][0]:
        print(f"   First result location: {results3['metadatas'][0][0].get('location', 'N/A')}")
    
    # Test 4: Get documents with filter (no similarity)
    print(f"\n4️⃣ GET DOCUMENTS WITH Amsterdam FILTER (NO SIMILARITY)")
    results4 = vector_service.collection.get(
        where={"location": "Amsterdam"},
        limit=5
    )
    print(f"   Results: {len(results4['ids'])} documents")
    if results4['ids']:
        print(f"   First result location: {results4['metadatas'][0].get('location', 'N/A')}")
    
    # Test 5: Get documents with filter (no similarity)
    print(f"\n5️⃣ GET DOCUMENTS WITH Istanbul FILTER (NO SIMILARITY)")
    results5 = vector_service.collection.get(
        where={"location": "Istanbul"},
        limit=5
    )
    print(f"   Results: {len(results5['ids'])} documents")
    if results5['ids']:
        print(f"   First result location: {results5['metadatas'][0].get('location', 'N/A')}")

if __name__ == "__main__":
    test_similarity_with_filters() 