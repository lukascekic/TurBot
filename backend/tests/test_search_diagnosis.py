#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from services.vector_service import VectorService
from models.document import SearchQuery

async def test_search_diagnosis():
    """Diagnose why searches return 0 results"""
    
    print("🔬 SEARCH DIAGNOSIS - Understanding why no results")
    print("=" * 60)
    
    # Initialize vector service
    vector_service = VectorService()
    
    # Get collection stats first
    stats = vector_service.get_collection_stats()
    print(f"📊 Collection Stats:")
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   Categories: {stats['categories']}")
    print(f"   Locations: {stats['locations']}")
    
    # Test 1: Basic search without filters
    print(f"\n🧪 TEST 1: Basic search without filters")
    query1 = SearchQuery(query="hotel", limit=3)
    results1 = vector_service.search(query1)
    print(f"   Query: 'hotel'")
    print(f"   Results: {len(results1.results)}")
    if results1.results:
        for i, result in enumerate(results1.results[:2]):
            print(f"     • {result.metadata.source_file} (similarity: {result.similarity_score:.3f})")
    
    # Test 2: Search with existing location
    print(f"\n🧪 TEST 2: Search with existing location (Rim)")
    query2 = SearchQuery(query="hotel", filters={"location": "Rim"}, limit=3)
    results2 = vector_service.search(query2)
    print(f"   Query: 'hotel' with location: 'Rim'")
    print(f"   Results: {len(results2.results)}")
    if results2.results:
        for i, result in enumerate(results2.results[:2]):
            print(f"     • {result.metadata.source_file} (similarity: {result.similarity_score:.3f})")
    
    # Test 3: Search with non-existing location
    print(f"\n🧪 TEST 3: Search with non-existing location (Amsterdam)")
    query3 = SearchQuery(query="hotel", filters={"location": "Amsterdam"}, limit=3)
    results3 = vector_service.search(query3)
    print(f"   Query: 'hotel' with location: 'Amsterdam'")
    print(f"   Results: {len(results3.results)}")
    
    # Test 4: Check what locations actually exist
    print(f"\n🧪 TEST 4: Checking all available locations")
    try:
        import chromadb
        from chromadb.config import Settings
        from pathlib import Path
        
        current_file = Path(__file__).parent.parent.parent
        db_path = current_file / "chroma_db_new"
        
        chroma_client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        collection = chroma_client.get_collection("tourism_documents")
        all_data = collection.get()
        
        all_locations = set()
        all_categories = set()
        
        for meta in all_data['metadatas']:
            if meta.get('location'):
                all_locations.add(meta['location'])
            if meta.get('category'):
                all_categories.add(meta['category'])
        
        print(f"   📍 ALL LOCATIONS in DB: {sorted(list(all_locations))}")
        print(f"   🏨 ALL CATEGORIES in DB: {sorted(list(all_categories))}")
        
    except Exception as e:
        print(f"   ❌ Error checking locations: {e}")
    
    # Test 5: Test with complex filters (should fail)
    print(f"\n🧪 TEST 5: Test with multiple filters (should fail due to ChromaDB limitation)")
    complex_filters = {
        "location": "Rim",
        "category": "tour", 
        "price_range": "moderate",
        "travel_month": "august"
    }
    query5 = SearchQuery(query="hotel", filters=complex_filters, limit=3)
    try:
        results5 = vector_service.search(query5)
        print(f"   Results: {len(results5.results)} (if 0, ChromaDB filter issue)")
    except Exception as e:
        print(f"   ❌ ChromaDB Error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 DIAGNOSIS COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_search_diagnosis()) 