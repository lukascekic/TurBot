#!/usr/bin/env python3
"""
Debug vector search with filters
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.vector_service import VectorService
from models.document import SearchQuery

def test_vector_search_with_filters():
    """Test vector search with different filter combinations"""
    print("🔍 TESTING VECTOR SEARCH WITH FILTERS")
    print("=" * 60)
    
    vector_service = VectorService()
    
    # Test cases
    test_cases = [
        {
            "name": "No filters",
            "query": SearchQuery(query="hotel", limit=5),
        },
        {
            "name": "Amsterdam filter only",
            "query": SearchQuery(
                query="hotel", 
                limit=5,
                filters={"location": "Amsterdam"}
            ),
        },
        {
            "name": "Istanbul filter only", 
            "query": SearchQuery(
                query="hotel",
                limit=5,
                filters={"location": "Istanbul"}
            ),
        },
        {
            "name": "Multiple filters (should use only location)",
            "query": SearchQuery(
                query="hotel",
                limit=5,
                filters={
                    "location": "Amsterdam",
                    "category": "hotel",
                    "price_range": "moderate"
                }
            ),
        },
        {
            "name": "Category filter only",
            "query": SearchQuery(
                query="hotel",
                limit=5,
                filters={"category": "tour"}
            ),
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test_case['name']}")
        print("-" * 40)
        
        query = test_case["query"]
        print(f"   Query: '{query.query}'")
        print(f"   Filters: {query.filters}")
        
        # Perform search
        response = vector_service.search(query)
        
        print(f"   Results: {response.total_results}")
        print(f"   Time: {response.processing_time:.3f}s")
        
        # Show first few results
        for j, result in enumerate(response.results[:3]):
            print(f"      {j+1}. {result.metadata.source_file} (sim: {result.similarity_score:.3f})")
            print(f"         Location: '{result.metadata.location}', Category: '{result.metadata.category}'")
    
    print(f"\n✅ Filter testing complete!")

if __name__ == "__main__":
    test_vector_search_with_filters() 