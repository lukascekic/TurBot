#!/usr/bin/env python3
"""
TESTING TEMPLATE - Use this structure for all future tests

This template is based on test_identical_queries_simple_structure.py which works correctly.
Key components that make tests work:
1. Async functions with proper OpenAI client setup
2. Full RAG pipeline: self-querying → query expansion → vector search → response generation
3. Only location filter used to avoid ChromaDB limitations
4. Direct service initialization (no factory functions)
5. Proper error handling and result display
"""

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

from services.self_querying_service import SelfQueryingService
from services.query_expansion_service import QueryExpansionService
from services.vector_service import VectorService
from services.response_generator import ResponseGenerator

async def test_your_feature():
    """Template test function - replace with your specific test"""
    
    # Initialize services (ALWAYS USE THIS PATTERN)
    self_querying = SelfQueryingService(client)
    query_expansion = QueryExpansionService(client)
    vector_service = VectorService()  # No parameters needed
    response_generator = ResponseGenerator(client)
    
    # Your test queries
    test_queries = [
        "Jel imas neki smestaj u Rimu za 4 osobe?",
        "Daj neku ponudu za letovanje u avgustu."
    ]
    
    print("🔄 TESTING YOUR FEATURE")
    print("=" * 70)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🎯 TEST {i}: '{query}'")
        print("-" * 50)
        
        try:
            # Step 1: Self-Querying (ALWAYS INCLUDE)
            print("1️⃣ Self-Querying Analysis...")
            structured_query = await self_querying.parse_query(query)
            
            print(f"   ✅ Intent: {structured_query.intent}")
            print(f"   ✅ Semantic Query: {structured_query.semantic_query}")
            print(f"   ✅ Location: {structured_query.filters.get('location')}")
            print(f"   ✅ Confidence: {structured_query.confidence}")
            
            # Step 2: Query Expansion (ALWAYS INCLUDE)
            print("\n2️⃣ Query Expansion...")
            expanded_query = await query_expansion.expand_query_llm(structured_query.semantic_query)
            print(f"   ✅ Expanded: {expanded_query[:100]}...")
            
            # Step 3: Vector Search (USE ONLY LOCATION FILTER)
            print("\n3️⃣ Vector Search...")
            
            # CRITICAL: Use only location filter to avoid ChromaDB issues
            simple_filters = {}
            if "location" in structured_query.filters:
                simple_filters["location"] = structured_query.filters["location"]
            
            from models.document import SearchQuery
            search_query = SearchQuery(
                query=expanded_query,  # Use expanded query, not original
                filters=simple_filters,  # ONLY location filter
                limit=3
            )
            search_results = vector_service.search(search_query)
            
            print(f"   ✅ Found {len(search_results.results)} results")
            print(f"   ✅ Filters used: {simple_filters}")
            
            # Display results
            for j, result in enumerate(search_results.results[:2]):
                doc_name = result.metadata.source_file or "Unknown document"
                print(f"     • Result {j+1}: {doc_name} (similarity: {result.similarity_score:.3f})")
            
            # Step 4: Response Generation (OPTIONAL - include if testing full pipeline)
            print("\n4️⃣ Response Generation...")
            if search_results and search_results.results:
                # Convert SearchResult objects to dict format
                search_results_dict = []
                for result in search_results.results:
                    search_results_dict.append({
                        'content': result.text,
                        'metadata': result.metadata.model_dump(),
                        'similarity': result.similarity_score,
                        'document_name': result.metadata.source_file or 'Unknown'
                    })
                
                response = await response_generator.generate_response(
                    search_results=search_results_dict,
                    structured_query=structured_query
                )
                
                print(f"   ✅ Response generated ({len(response.response)} chars)")
                print(f"   ✅ Confidence: {response.confidence}")
                print(f"   ✅ Sources: {len(response.sources)}")
                
                # Display full response
                print(f"\n🎉 **COMPLETE AI RESPONSE:**")
                print("=" * 50)
                print(response.response)
                print("=" * 50)
            else:
                print("   ⚠️ No search results found")
        
        except Exception as e:
            print(f"   ❌ Test {i} failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)
    
    print("\n" + "=" * 70)
    print("🏁 TESTING COMPLETE")

async def test_simple_vector_search():
    """Simple vector search test without full pipeline"""
    
    print("🔍 SIMPLE VECTOR SEARCH TEST")
    print("=" * 50)
    
    vector_service = VectorService()
    
    # Test simple searches
    test_cases = [
        {"query": "hotel", "location": "Amsterdam"},
        {"query": "aranžman", "location": "Istanbul"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: Query='{test_case['query']}', Location='{test_case['location']}'")
        
        from models.document import SearchQuery
        search_query = SearchQuery(
            query=test_case['query'],
            filters={"location": test_case['location']},
            limit=3
        )
        
        results = vector_service.search(search_query)
        print(f"   Results: {len(results.results)}")
        
        for j, result in enumerate(results.results[:1]):
            print(f"   • {result.metadata.source_file} (similarity: {result.similarity_score:.3f})")

if __name__ == "__main__":
    # Run your tests
    asyncio.run(test_your_feature())
    print("\n" + "="*80 + "\n")
    asyncio.run(test_simple_vector_search()) 