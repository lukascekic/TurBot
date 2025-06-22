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

from services.self_querying_service import SelfQueryingService
from services.query_expansion_service import QueryExpansionService
from services.vector_service import VectorService
from services.response_generator import ResponseGenerator

async def test_case_sensitivity_variations():
    """Test case sensitivity using the working pipeline approach"""
    
    # Initialize services (SAME AS working test)
    self_querying = SelfQueryingService(client)
    query_expansion = QueryExpansionService(client)
    vector_service = VectorService()
    
    print("🔄 TESTING CASE SENSITIVITY WITH WORKING PIPELINE")
    print("=" * 70)
    
    # Test different case variations for locations
    case_test_queries = [
        "Tražim hotel u AMSTERDAMU",     # UPPERCASE
        "Tražim hotel u amsterdamu",     # lowercase  
        "Tražim hotel u Amsterdam",      # Title case
        "Tražim hotel u ISTANBULU",      # UPPERCASE
        "Tražim hotel u istanbulu",      # lowercase
        "Tražim hotel u Istanbul",       # Title case
    ]
    
    for i, query in enumerate(case_test_queries, 1):
        print(f"\n🎯 CASE TEST {i}: '{query}'")
        print("-" * 50)
        
        # Step 1: Self-Querying
        print("1️⃣ Self-Querying Analysis...")
        structured_query = await self_querying.parse_query(query)
        
        print(f"   ✅ Location detected: '{structured_query.filters.get('location')}'")
        print(f"   ✅ Semantic Query: '{structured_query.semantic_query}'")
        
        # Step 2: Query Expansion
        print("\n2️⃣ Query Expansion...")
        expanded_query = await query_expansion.expand_query_llm(structured_query.semantic_query)
        print(f"   ✅ Expanded: {expanded_query[:60]}...")
        
        # Step 3: Vector Search
        print("\n3️⃣ Vector Search...")
        try:
            # Use only location filter (same as working approach)
            simple_filters = {}
            if "location" in structured_query.filters:
                simple_filters["location"] = structured_query.filters["location"]
            
            from models.document import SearchQuery
            search_query = SearchQuery(
                query=expanded_query,
                filters=simple_filters,
                limit=3
            )
            search_results = vector_service.search(search_query)
            
            print(f"   ✅ Found {len(search_results.results)} results")
            print(f"   ✅ Location filter used: '{simple_filters.get('location', 'None')}'")
            
            if search_results.results:
                for j, result in enumerate(search_results.results[:1]):
                    doc_name = result.metadata.source_file or "Unknown document"
                    print(f"     • Result {j+1}: {doc_name} (similarity: {result.similarity_score:.3f})")
            else:
                print("     ❌ No results found")
        
        except Exception as e:
            print(f"   ❌ Search error: {e}")
        
        print("-" * 50)
    
    print("\n" + "=" * 70)
    print("🏁 CASE SENSITIVITY TESTING COMPLETE")

async def test_identical_queries_simple_structure():
    """Test identical queries as test_full_response_demo.py but with simple structure like test_case_declension_demo.py"""
    
    # Initialize services (SAME AS test_case_declension_demo.py)
    self_querying = SelfQueryingService(client)
    query_expansion = QueryExpansionService(client)
    vector_service = VectorService()  # No parameters needed
    response_generator = ResponseGenerator(client)
    
    # IDENTICAL test queries as test_full_response_demo.py
    test_queries = [
        "Tražim hotel u Amsterdamu u avgustu do 500 EUR",  # Same as test_full_response_demo.py
        "Preporuči najbolje aranžmane za Istanbul"         # Same as test_full_response_demo.py
    ]
    
    print("🔄 TESTING IDENTICAL QUERIES WITH SIMPLE STRUCTURE")
    print("=" * 70)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🎯 TEST {i}: '{query}'")
        print("-" * 50)
        
        # Step 1: Self-Querying
        print("1️⃣ Self-Querying Analysis...")
        structured_query = await self_querying.parse_query(query)
        
        print(f"   ✅ Intent: {structured_query.intent}")
        print(f"   ✅ Semantic Query: {structured_query.semantic_query}")
        print(f"   ✅ Location: {structured_query.filters.get('location')}")
        print(f"   ✅ All Filters: {structured_query.filters}")
        print(f"   ✅ Confidence: {structured_query.confidence}")
        
        # Step 2: Query Expansion
        print("\n2️⃣ Query Expansion...")
        expanded_query = await query_expansion.expand_query_llm(structured_query.semantic_query)
        print(f"   ✅ Expanded: {expanded_query}")
        
        # Step 3: Vector Search (SAME APPROACH AS test_case_declension_demo.py)
        print("\n3️⃣ Vector Search...")
        try:
            # Use only location filter to avoid ChromaDB issues (SAME AS test_case_declension_demo.py)
            simple_filters = {}
            if "location" in structured_query.filters:
                simple_filters["location"] = structured_query.filters["location"]
            
            from models.document import SearchQuery
            search_query = SearchQuery(
                query=expanded_query,
                filters=simple_filters,  # ONLY location filter like test_case_declension_demo.py
                limit=3
            )
            search_results = vector_service.search(search_query)
            
            print(f"   ✅ Found {len(search_results.results)} results")
            print(f"   ✅ Filters used: {simple_filters}")
            
            for i, result in enumerate(search_results.results[:2]):
                doc_name = result.metadata.source_file or "Unknown document"
                print(f"     • Result {i+1}: {doc_name} (similarity: {result.similarity_score:.3f})")
        
        except Exception as e:
            print(f"   ❌ Search error: {e}")
            search_results = None
        
        # Step 4: Response Generation (SAME AS test_case_declension_demo.py)
        print("\n4️⃣ Response Generation...")
        try:
            if search_results and search_results.results:
                # Convert SearchResult objects to dict format expected by ResponseGenerator
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
                
                # Display first part of response
                response_preview = response.response[:200] + "..." if len(response.response) > 200 else response.response
                print(f"   📝 Response Preview: {response_preview}")
                
            else:
                print("   ⚠️ No search results - generating fallback response")
                
        except Exception as e:
            print(f"   ❌ Response generation error: {e}")
        
        print("-" * 50)
    
    print("\n" + "=" * 70)
    print("🏁 IDENTICAL QUERIES TESTING COMPLETE")
    
    # Summary
    print("\n📊 SUMMARY:")
    print("✅ Same queries as test_full_response_demo.py")
    print("✅ Same structure as test_case_declension_demo.py")
    print("✅ Only location filter used (avoiding ChromaDB issues)")
    print("✅ Direct service initialization (no factory functions)")

if __name__ == "__main__":
    # Run both tests
    asyncio.run(test_case_sensitivity_variations())
    print("\n" + "="*80 + "\n")
    asyncio.run(test_identical_queries_simple_structure()) 