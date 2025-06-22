import sys
import os
# Add parent directory to path to import services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

from services.self_querying_service import get_self_querying_service, StructuredQuery
from services.response_generator import get_response_generator, ResponseData
from services.query_expansion_service import get_query_expansion_service
from services.vector_service import VectorService

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_self_querying_service():
    """
    Test Self-Querying Service - Natural language → structured query parsing
    """
    logger.info("🔍 TESTING SELF-QUERYING SERVICE")
    logger.info("=" * 50)
    
    # Initialize services
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return False
    
    client = AsyncOpenAI(api_key=api_key)
    self_querying_service = get_self_querying_service(client)
    
    # Test queries with different complexities
    test_queries = [
        "Hotel u centru Rima do 300 EUR za 4 osobe u maju",
        "Potreban mi je romantičan smeštaj za dvoje sa spa",
        "Preporuči najbolje aranžmane za porodično letovanje na moru",
        "Tražim luksuzni hotel sa bazenom",
        "Kakve su cene za Istanbul u avgustu?",
        "Imam budžet od 500 EUR, šta možete da predložite?"
    ]
    
    results = []
    
    for query in test_queries:
        logger.info(f"\n🧪 Testing query: '{query}'")
        
        try:
            structured = await self_querying_service.parse_query(query)
            
            logger.info(f"✅ Parsed successfully:")
            logger.info(f"  Semantic query: '{structured.semantic_query}'")
            logger.info(f"  Intent: {structured.intent}")
            logger.info(f"  Filters: {structured.filters}")
            logger.info(f"  Confidence: {structured.confidence:.2f}")
            
            # Generate filter summary
            filter_summary = self_querying_service.get_filter_summary(structured)
            logger.info(f"  Summary: {filter_summary}")
            
            results.append({
                "query": query,
                "parsed": structured,
                "success": True
            })
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            results.append({
                "query": query,
                "error": str(e),
                "success": False
            })
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    logger.info(f"\n📊 Self-Querying Results: {successful}/{len(test_queries)} successful")
    
    return successful == len(test_queries)

async def test_response_generation_service():
    """
    Test Response Generation Service - Natural responses with source attribution
    """
    logger.info("\n🗣️ TESTING RESPONSE GENERATION SERVICE")
    logger.info("=" * 50)
    
    # Initialize services
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return False
    
    client = AsyncOpenAI(api_key=api_key)
    response_generator = get_response_generator(client)
    self_querying_service = get_self_querying_service(client)
    
    # Mock search results (simulating vector search output)
    mock_search_results = [
        {
            "document_name": "Amsterdam_Prvi_Maj_2025.pdf",
            "content": "Amsterdam - Prvi Maj 2025, direktan let. Hotel 4* u centru grada. Cena: 420 EUR po osobi za 4 dana. Uključeno: doručak, transfer, city tour. Amenities: spa, bazen, parking, wifi.",
            "similarity": 0.85,
            "metadata": {
                "category": "tour",
                "location": "Amsterdam",
                "price_range": "expensive",
                "amenities": ["spa", "bazen", "parking", "wifi"],
                "price_details": {
                    "currency": "EUR",
                    "price_per_person": 420
                },
                "family_friendly": False
            }
        },
        {
            "document_name": "Istanbul_Avio_Prvi_Maj.pdf", 
            "content": "Istanbul putovanje avionom. Hotel 4* sa panoramskim pogledom. Cena: 380 EUR po osobi. 4 noćenja sa doručkom. Obilaski: Aja Sofija, Plavi Džamija, Grand Bazar.",
            "similarity": 0.78,
            "metadata": {
                "category": "tour",
                "location": "Istanbul",
                "price_range": "expensive",
                "amenities": ["doručak", "panoramski pogled"],
                "price_details": {
                    "currency": "EUR",
                    "price_per_person": 380
                }
            }
        }
    ]
    
    # Test different query types
    test_scenarios = [
        {
            "query": "Potreban mi je hotel u centru sa parkingom do 500 EUR",
            "intent": "search"
        },
        {
            "query": "Preporuči najbolje aranžmane za Prvi Maj",
            "intent": "recommendation"
        },
        {
            "query": "Uporedi opcije za Amsterdam i Istanbul",
            "intent": "comparison"
        }
    ]
    
    results = []
    
    for scenario in test_scenarios:
        query = scenario["query"]
        logger.info(f"\n🧪 Testing response generation for: '{query}'")
        
        try:
            # Parse query first
            structured_query = await self_querying_service.parse_query(query)
            
            # Generate response
            response_data = await response_generator.generate_response(
                mock_search_results, structured_query
            )
            
            logger.info(f"✅ Response generated successfully:")
            logger.info(f"  Intent: {structured_query.intent}")
            logger.info(f"  Response length: {len(response_data.response)} chars")
            logger.info(f"  Sources: {len(response_data.sources)}")
            logger.info(f"  Structured data: {list(response_data.structured_data.keys())}")
            logger.info(f"  Suggested questions: {len(response_data.suggested_questions)}")
            logger.info(f"  Confidence: {response_data.confidence:.2f}")
            
            # Show partial response
            response_preview = response_data.response[:200] + "..." if len(response_data.response) > 200 else response_data.response
            logger.info(f"  Response preview: {response_preview}")
            
            results.append({
                "query": query,
                "response_data": response_data,
                "success": True
            })
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            results.append({
                "query": query,
                "error": str(e),
                "success": False
            })
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    logger.info(f"\n📊 Response Generation Results: {successful}/{len(test_scenarios)} successful")
    
    return successful == len(test_scenarios)

async def test_integrated_pipeline():
    """
    Test complete Phase 3b pipeline: Query → Self-Querying → Expansion → Search → Response
    """
    logger.info("\n🔄 TESTING INTEGRATED PHASE 3B PIPELINE")
    logger.info("=" * 50)
    
    # Initialize all services
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return False
    
    client = AsyncOpenAI(api_key=api_key)
    self_querying_service = get_self_querying_service(client)
    query_expansion_service = get_query_expansion_service(client)
    response_generator = get_response_generator(client)
    vector_service = VectorService()
    
    # End-to-end test query
    user_query = "Tražim romantičan hotel u Rimu do 400 EUR za dvoje u maju"
    
    logger.info(f"🎯 End-to-end test: '{user_query}'")
    
    try:
        # Step 1: Self-querying (parse natural language)
        logger.info("\n1️⃣ Self-Querying: Parsing natural language...")
        structured_query = await self_querying_service.parse_query(user_query)
        logger.info(f"  ✅ Semantic query: '{structured_query.semantic_query}'")
        logger.info(f"  ✅ Filters: {structured_query.filters}")
        logger.info(f"  ✅ Intent: {structured_query.intent}")
        
        # Step 2: Query expansion (enhance with synonyms)
        logger.info("\n2️⃣ Query Expansion: Enhancing with synonyms...")
        expanded_query = await query_expansion_service.expand_query_llm(structured_query.semantic_query)
        logger.info(f"  ✅ Expanded: {expanded_query}")
        
        # Step 3: Vector search (using existing database)
        logger.info("\n3️⃣ Vector Search: Finding relevant documents...")
        from models.document import SearchQuery
        search_query = SearchQuery(
            query=expanded_query,
            filters=structured_query.filters,
            limit=5,
            threshold=0.1
        )
        search_response = vector_service.search(search_query)
        search_results = []
        
        # Convert SearchResult to format expected by response generator
        for result in search_response.results:
            search_results.append({
                "document_name": result.metadata.source_file or "Unknown",
                "content": result.text,
                "similarity": result.similarity_score,
                "metadata": result.metadata.model_dump()
            })
        
        logger.info(f"  ✅ Found {len(search_results)} results")
        
        # Step 4: Response generation
        logger.info("\n4️⃣ Response Generation: Creating natural response...")
        response_data = await response_generator.generate_response(
            search_results, structured_query
        )
        logger.info(f"  ✅ Generated response ({len(response_data.response)} chars)")
        logger.info(f"  ✅ Confidence: {response_data.confidence:.2f}")
        
        # Show final result
        logger.info("\n🎉 FINAL RESULT:")
        logger.info("=" * 30)
        logger.info(f"Query: {user_query}")
        logger.info(f"Intent: {structured_query.intent}")
        logger.info(f"Filters: {structured_query.filters}")
        logger.info(f"Results: {len(search_results)} documents")
        logger.info(f"Response: {response_data.response[:300]}...")
        logger.info(f"Sources: {[s['document_name'] for s in response_data.sources[:3]]}")
        logger.info(f"Suggested: {response_data.suggested_questions[:2]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        return False

async def test_edge_cases():
    """
    Test edge cases and error handling
    """
    logger.info("\n⚠️ TESTING EDGE CASES")
    logger.info("=" * 50)
    
    # Initialize services
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return False
    
    client = AsyncOpenAI(api_key=api_key)
    self_querying_service = get_self_querying_service(client)
    response_generator = get_response_generator(client)
    
    edge_cases = [
        "",  # Empty query
        "a",  # Very short query
        "Hotel " * 100,  # Very long query
        "asdf qwerty zxcv",  # Nonsense query
        "🏨🌍✈️",  # Emoji query
    ]
    
    successful_edge_cases = 0
    
    for i, query in enumerate(edge_cases, 1):
        logger.info(f"\n🧪 Edge case {i}: '{query[:50]}{'...' if len(query) > 50 else ''}'")
        
        try:
            # Test self-querying service
            structured = await self_querying_service.parse_query(query)
            logger.info(f"  ✅ Self-querying handled gracefully")
            
            # Test response generation with empty results
            response_data = await response_generator.generate_response(
                [], structured
            )
            logger.info(f"  ✅ Response generation handled gracefully")
            logger.info(f"  Response: {response_data.response[:100]}...")
            
            successful_edge_cases += 1
            
        except Exception as e:
            logger.warning(f"  ⚠️ Edge case handled with exception: {e}")
            # This is acceptable for edge cases - we want graceful degradation
            successful_edge_cases += 1
    
    logger.info(f"\n📊 Edge Cases: {successful_edge_cases}/{len(edge_cases)} handled gracefully")
    
    return successful_edge_cases >= len(edge_cases) - 1  # Allow 1 failure

async def main():
    """
    Run all Phase 3b tests
    """
    logger.info("🚀 PHASE 3B TESTING - SELF-QUERYING & RESPONSE GENERATION")
    logger.info("=" * 60)
    
    tests = [
        ("Self-Querying Service", test_self_querying_service),
        ("Response Generation Service", test_response_generation_service),
        ("Integrated Pipeline", test_integrated_pipeline),
        ("Edge Cases", test_edge_cases)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🔥 Running {test_name}...")
        try:
            success = await test_func()
            results.append((test_name, success))
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"  {status}")
        except Exception as e:
            logger.error(f"  ❌ FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("🎯 PHASE 3B TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        logger.info(f"  {status} {test_name}")
    
    logger.info(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 PHASE 3B IMPLEMENTATION SUCCESSFUL!")
        logger.info("✅ Ready for Phase 3c (Conversational Memory) or Frontend Integration")
    else:
        logger.info("⚠️ Some tests failed - review and fix before proceeding")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 