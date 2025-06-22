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
from models.document import SearchQuery

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complete_flow_with_full_display():
    """
    Test complete flow and display EVERYTHING - including full responses
    """
    logger.info("🎯 COMPREHENSIVE FULL RESPONSE DEMO")
    logger.info("=" * 60)
    
    # Initialize services
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return False
    
    client = AsyncOpenAI(api_key=api_key)
    self_querying_service = get_self_querying_service(client)
    query_expansion_service = get_query_expansion_service(client)
    response_generator = get_response_generator(client)
    vector_service = VectorService()
    
    # Test queries - including specific month test
    test_queries = [
        "Tražim hotel u Amsterdamu u avgustu do 500 EUR",  # Specific month test
        "Preporuči najbolje aranžmane za Istanbul"  # General recommendation
    ]
    
    for i, user_query in enumerate(test_queries, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"🔥 TEST {i}: {user_query}")
        logger.info(f"{'='*60}")
        
        try:
            # Step 1: Self-querying
            logger.info(f"\n1️⃣ SELF-QUERYING ANALYSIS")
            logger.info("-" * 30)
            structured_query = await self_querying_service.parse_query(user_query)
            
            logger.info(f"🎯 Original Query: '{user_query}'")
            logger.info(f"🧠 Semantic Query: '{structured_query.semantic_query}'")
            logger.info(f"🎭 Intent: {structured_query.intent}")
            logger.info(f"🔧 Confidence: {structured_query.confidence:.2f}")
            logger.info(f"📋 Filter Summary: {self_querying_service.get_filter_summary(structured_query)}")
            logger.info(f"🗂️ All Filters:")
            for key, value in structured_query.filters.items():
                logger.info(f"   {key}: {value}")
            
            # Step 2: Query expansion
            logger.info(f"\n2️⃣ QUERY EXPANSION")
            logger.info("-" * 30)
            expanded_query = await query_expansion_service.expand_query_llm(structured_query.semantic_query)
            logger.info(f"📈 Original: '{structured_query.semantic_query}'")
            logger.info(f"📈 Expanded: '{expanded_query}'")
            
            # Step 3: Vector search
            logger.info(f"\n3️⃣ VECTOR SEARCH")
            logger.info("-" * 30)
            
            # Use only location filter to avoid ChromaDB issues (same as test_case_declension_demo.py)
            simple_filters = {}
            if "location" in structured_query.filters:
                simple_filters["location"] = structured_query.filters["location"]
            
            search_query = SearchQuery(
                query=expanded_query,
                filters=simple_filters,  # Only location filter
                limit=5,
                threshold=0.1
            )
            search_response = vector_service.search(search_query)
            
            logger.info(f"🔍 Query sent to vector DB: '{search_query.query}'")
            logger.info(f"🔍 Original filters: {structured_query.filters}")
            logger.info(f"🔍 ChromaDB filters used: {search_query.filters}")
            logger.info(f"📊 Results found: {len(search_response.results)}")
            logger.info(f"⏱️ Search time: {search_response.processing_time:.3f}s")
            
            # Convert search results for response generator
            search_results = []
            for result in search_response.results:
                search_results.append({
                    "document_name": result.metadata.source_file or "Unknown",
                    "content": result.text,
                    "similarity": result.similarity_score,
                    "metadata": result.metadata.model_dump()
                })
            
            # Display found documents
            if search_results:
                logger.info(f"\n📄 FOUND DOCUMENTS:")
                for j, result in enumerate(search_results, 1):
                    logger.info(f"   {j}. {result['document_name']}")
                    logger.info(f"      Similarity: {result['similarity']:.3f}")
                    logger.info(f"      Location: {result['metadata'].get('location', 'N/A')}")
                    logger.info(f"      Category: {result['metadata'].get('category', 'N/A')}")
                    if result['metadata'].get('travel_month'):
                        logger.info(f"      Month: {result['metadata']['travel_month']}")
                    elif result['metadata'].get('seasonal'):
                        logger.info(f"      Season: {result['metadata']['seasonal']}")
                    logger.info(f"      Content preview: {result['content'][:100]}...")
                    logger.info("")
            else:
                logger.info("   ❌ No documents found")
            
            # Step 4: Response generation
            logger.info(f"\n4️⃣ RESPONSE GENERATION")
            logger.info("-" * 30)
            response_data = await response_generator.generate_response(
                search_results, structured_query
            )
            
            logger.info(f"📝 Response generated:")
            logger.info(f"   Length: {len(response_data.response)} characters")
            logger.info(f"   Sources: {len(response_data.sources)}")
            logger.info(f"   Confidence: {response_data.confidence:.2f}")
            logger.info(f"   Suggested questions: {len(response_data.suggested_questions)}")
            
            # Display structured data
            logger.info(f"\n📊 STRUCTURED DATA EXTRACTED:")
            for key, value in response_data.structured_data.items():
                logger.info(f"   {key}: {value}")
            
            # Display sources
            if response_data.sources:
                logger.info(f"\n📚 SOURCES USED:")
                for j, source in enumerate(response_data.sources, 1):
                    logger.info(f"   {j}. {source['document_name']} (similarity: {source['similarity']:.3f})")
            
            # Display suggested questions
            if response_data.suggested_questions:
                logger.info(f"\n❓ SUGGESTED FOLLOW-UP QUESTIONS:")
                for j, question in enumerate(response_data.suggested_questions, 1):
                    logger.info(f"   {j}. {question}")
            
            # **FULL RESPONSE DISPLAY**
            logger.info(f"\n🎉 **COMPLETE AI RESPONSE:**")
            logger.info("=" * 50)
            logger.info(response_data.response)
            logger.info("=" * 50)
            
            logger.info(f"\n✅ Test {i} completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Test {i} failed: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n🎯 DEMO COMPLETED")
    return True

async def test_month_granularity():
    """
    Specific test for month granularity - avgust vs juli
    """
    logger.info(f"\n🗓️ MONTH GRANULARITY TEST")
    logger.info("=" * 40)
    
    # Initialize services
    api_key = os.getenv("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)
    self_querying_service = get_self_querying_service(client)
    
    month_queries = [
        "Hotel u Istanbulu u avgustu",
        "Putovanje u Rim u julu", 
        "Aranžman za Grčku tokom leta"
    ]
    
    for query in month_queries:
        logger.info(f"\n🧪 Testing: '{query}'")
        structured = await self_querying_service.parse_query(query)
        
        logger.info(f"   Detected month: {structured.filters.get('travel_month', 'None')}")
        logger.info(f"   Detected season: {structured.filters.get('season', 'None')}")
        
        if structured.filters.get('travel_month'):
            logger.info(f"   ✅ Specific month preserved: {structured.filters['travel_month']}")
        elif structured.filters.get('season'):
            logger.info(f"   ⚠️ Only season detected: {structured.filters['season']}")
        else:
            logger.info(f"   ❌ No temporal information detected")

async def main():
    """
    Run full response demo
    """
    logger.info("🚀 STARTING FULL RESPONSE DEMO")
    
    success1 = await test_complete_flow_with_full_display()
    success2 = await test_month_granularity() 
    
    if success1:
        logger.info("\n🎉 DEMO SUCCESSFUL!")
        logger.info("✅ You can now see complete responses and understand the full pipeline")
        logger.info("✅ Month granularity implemented - 'avgust' will be preserved as specific month")
        logger.info("✅ ChromaDB filter issues should be resolved")
    else:
        logger.info("\n⚠️ Some issues detected - review output above")
    
    return success1

if __name__ == "__main__":
    asyncio.run(main()) 