#!/usr/bin/env python3

import sys
import os
sys.path.append('..')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.vector_service import VectorService
from models.document import SearchQuery

def test_case_sensitivity():
    print("🔍 TESTING CASE SENSITIVITY IN CHROMADB FILTERS")
    print("=" * 60)
    
    # Initialize vector service
    vector_service = VectorService()
    
    # Test different case variations
    test_cases = [
        "Istanbul",
        "istanbul", 
        "ISTANBUL",
        "Amsterdam",
        "amsterdam",
        "AMSTERDAM",
        "Rim",
        "rim",
        "RIM"
    ]
    
    for location in test_cases:
        print(f"\n🧪 Testing location: '{location}'")
        
        query = SearchQuery(
            query="test",
            filters={"location": location},
            limit=5,
            threshold=0.1
        )
        
        result = vector_service.search(query)
        print(f"   Results: {len(result.results)} documents")
        
        if result.results:
            print(f"   ✅ FOUND: {location}")
            # Show first result metadata
            first_result = result.results[0]
            print(f"   First result location: '{first_result.metadata.location}'")
        else:
            print(f"   ❌ NOT FOUND: {location}")

if __name__ == "__main__":
    test_case_sensitivity() 