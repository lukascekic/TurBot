"""
Test Filter Hierarchy Implementation
Tests seasonal queries and non-location queries with the new priority system
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from services.self_querying_service import SelfQueryingService
from services.query_expansion_service import QueryExpansionService  
from services.vector_service import VectorService
from models.document import SearchQuery

async def test_filter_hierarchy():
    """Test the new filter hierarchy with various query types"""
    
    # Setup services
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    self_querying = SelfQueryingService(client)
    query_expansion = QueryExpansionService(client)
    vector_service = VectorService()
    
    # Test cases for different query types
    test_queries = [
        "koja letovanja imaš u avgustu",           # Seasonal query (no location)
        "daj mi neke jeftine hotele",              # Price range query (no location)
        "koje restorane preporučuješ",             # Category query (no location)
        "smestaj u Rimu za medeni mesec",          # Location query (should use location)
        "zimovanje u decembru",                    # Winter seasonal query
    ]
    
    print("🚀 TESTING FILTER HIERARCHY IMPLEMENTATION")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n👤 Test {i}: '{query}'")
        print("=" * 50)
        
        try:
            # Step 1: Self-querying
            structured = await self_querying.parse_query(query)
            print("1️⃣ Self-Querying Results:")
            print(f"   Intent: {structured.intent}")
            print(f"   Semantic Query: {structured.semantic_query}")
            print(f"   Filters Extracted ({len(structured.filters)}):")
            for key, value in structured.filters.items():
                if value is not None and value != "" and value != []:
                    print(f"     • {key}: {value}")
            print(f"   Confidence: {structured.confidence}")
            
            # Step 2: Query expansion
            expanded = await query_expansion.expand_query_llm(structured.semantic_query)
            print(f"\n2️⃣ Query Expansion: {expanded[:60]}...")
            
            # Step 3: Vector search with filter hierarchy
            search_query = SearchQuery(
                query=expanded,
                filters=structured.filters,
                limit=3
            )
            
            print("\n3️⃣ Vector Search with Filter Hierarchy:")
            results = vector_service.search(search_query)  # Not async
            print(f"   Found: {len(results.results)} results")
            
            if results.results:
                print("   Top Results:")
                for j, result in enumerate(results.results[:2]):
                    source = result.metadata.source_file or "Unknown"
                    print(f"     {j+1}. {source[:45]}... (similarity: {result.similarity_score:.3f})")
            else:
                print("   ❌ No results found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    print("=" * 60)
    print("✅ Filter hierarchy tests completed!")

if __name__ == "__main__":
    asyncio.run(test_filter_hierarchy()) 