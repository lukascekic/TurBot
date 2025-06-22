#!/usr/bin/env python3
"""
Simple test to check Amsterdam filters
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.vector_service import VectorService
from models.document import SearchQuery

def test_amsterdam_filters():
    """Test Amsterdam with and without price_range filter"""
    print("🧪 TESTING AMSTERDAM FILTERS")
    print("=" * 60)
    
    vector_service = VectorService()
    
    # Test 1: Amsterdam WITHOUT price_range filter
    print("\n1️⃣ TEST: Amsterdam WITHOUT price_range filter")
    query1 = SearchQuery(
        query="hotel smeštaj",
        limit=5,
        filters={
            "location": "Amsterdam",
            "category": "tour",
            "amenities": [],
            "travel_month": "august"
        }
    )
    
    result1 = vector_service.search(query1)
    print(f"   Results: {len(result1.results)}")
    for i, result in enumerate(result1.results):
        print(f"      {i+1}. {result.metadata.source_file[:50]}...")
        print(f"         Location: {result.metadata.location}")
        print(f"         Category: {result.metadata.category}")
        print(f"         Price Range: {result.metadata.price_range}")
    
    # Test 2: Amsterdam WITH price_range filter
    print("\n2️⃣ TEST: Amsterdam WITH price_range: moderate filter")
    query2 = SearchQuery(
        query="hotel smeštaj",
        limit=5,
        filters={
            "location": "Amsterdam",
            "category": "tour",
            "price_range": "moderate",
            "amenities": [],
            "travel_month": "august"
        }
    )
    
    result2 = vector_service.search(query2)
    print(f"   Results: {len(result2.results)}")
    for i, result in enumerate(result2.results):
        print(f"      {i+1}. {result.metadata.source_file[:50]}...")
        print(f"         Location: {result.metadata.location}")
        print(f"         Category: {result.metadata.category}")
        print(f"         Price Range: {result.metadata.price_range}")
    
    # Test 3: Amsterdam WITH price_range: budget filter
    print("\n3️⃣ TEST: Amsterdam WITH price_range: budget filter")
    query3 = SearchQuery(
        query="hotel smeštaj",
        limit=5,
        filters={
            "location": "Amsterdam",
            "category": "tour",
            "price_range": "budget",
            "amenities": [],
            "travel_month": "august"
        }
    )
    
    result3 = vector_service.search(query3)
    print(f"   Results: {len(result3.results)}")
    for i, result in enumerate(result3.results):
        print(f"      {i+1}. {result.metadata.source_file[:50]}...")
        print(f"         Location: {result.metadata.location}")
        print(f"         Category: {result.metadata.category}")
        print(f"         Price Range: {result.metadata.price_range}")

if __name__ == "__main__":
    test_amsterdam_filters() 