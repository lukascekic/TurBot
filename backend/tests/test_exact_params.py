#!/usr/bin/env python3
"""
Test with EXACT same parameters as vector_service.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.vector_service import VectorService

def test_exact_params():
    """Test with exact same parameters as vector_service.py"""
    print("🔍 TESTING WITH EXACT VECTOR_SERVICE PARAMETERS")
    print("=" * 60)
    
    vector_service = VectorService()
    
    # Create embedding exactly like vector_service does
    test_query = '"hotel OR smeštaj OR apartman OR vila OR pansion OR boutique OR luksuzno OR premium OR spa OR wellness OR vrhunski OR odmor OR more OR plaža OR beach"'
    query_embedding = vector_service.create_embedding(test_query)
    print(f"✅ Created embedding for: '{test_query[:50]}...'")
    
    # Test with EXACT parameters from vector_service.py
    search_params = {
        "query_embeddings": [query_embedding],
        "n_results": 5 * 3,  # query.limit * 3 like in vector_service
        "where": {"location": "Amsterdam"}
    }
    
    print(f"\n🔍 EXACT SEARCH PARAMS:")
    print(f"   n_results: {search_params['n_results']}")
    print(f"   where: {search_params['where']}")
    print(f"   query_embeddings length: {len(search_params['query_embeddings'][0])}")
    
    # Execute ChromaDB query
    results = vector_service.collection.query(**search_params)
    
    print(f"\n📊 CHROMADB RESULTS:")
    print(f"   IDs returned: {len(results['ids'][0]) if results['ids'] else 0}")
    print(f"   Documents returned: {len(results['documents'][0]) if results['documents'] else 0}")
    print(f"   Metadatas returned: {len(results['metadatas'][0]) if results['metadatas'] else 0}")
    
    if results['ids'] and len(results['ids'][0]) > 0:
        print(f"   First 3 document IDs: {results['ids'][0][:3]}")
        for i, metadata in enumerate(results['metadatas'][0][:3]):
            print(f"   Result {i+1} location: {metadata.get('location', 'N/A')}")
    else:
        print(f"   ❌ NO DOCUMENTS RETURNED")

if __name__ == "__main__":
    test_exact_params() 