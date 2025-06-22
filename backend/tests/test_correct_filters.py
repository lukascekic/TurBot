#!/usr/bin/env python3
"""
Test with correct filters that match the actual data
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.vector_service import VectorService
from models.document import SearchQuery

def test_correct_filters():
    """Test with filters that match actual data in the database"""
    print("🧪 TESTING WITH CORRECT FILTERS")
    print("=" * 60)
    
    vector_service = VectorService()
    
    # Test cases that should work based on our debug info
    test_cases = [
        {
            "name": "Amsterdam tour (should work)",
            "query": SearchQuery(
                query="hotel", 
                limit=5,
                filters={"location": "Amsterdam", "category": "tour"}
            ),
        },
        {
            "name": "Istanbul tour (should work)",
            "query": SearchQuery(
                query="hotel",
                limit=5,
                filters={"location": "Istanbul", "category": "tour"}
            ),
        },
        {
            "name": "Amsterdam hotel (should fail - no hotel category)",
            "query": SearchQuery(
                query="hotel",
                limit=5,
                filters={"location": "Amsterdam", "category": "hotel"}
            ),
        },
        {
            "name": "Any location with hotel category",
            "query": SearchQuery(
                query="hotel",
                limit=5,
                filters={"category": "hotel"}
            ),
        },
        {
            "name": "Simulate original failed test 1 - correct filters",
            "query": SearchQuery(
                query="hotel smestaj",
                limit=5,
                filters={"location": "Amsterdam", "category": "tour"}  # Changed to tour
            ),
        },
        {
            "name": "Simulate original failed test 2 - correct filters", 
            "query": SearchQuery(
                query="aranžmani za Istanbul",
                limit=5,
                filters={"location": "Istanbul", "category": "tour"}  # Added category
            ),
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test_case['name']}")
        print("-" * 50)
        
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
    
    print(f"\n✅ Correct filter testing complete!")

if __name__ == "__main__":
    test_correct_filters() 