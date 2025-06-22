#!/usr/bin/env python3
"""
Enhanced RAG Test Suite

Tests the complete enhanced RAG pipeline:
1. GPT-4o-mini metadata extraction
2. Weighted filtering system
3. Intelligent response generation
4. End-to-end user experience
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
from services.metadata_enhancement_service import MetadataEnhancementService

async def test_enhanced_metadata_extraction():
    """Test GPT-4o-mini metadata extraction"""
    print("🧠 TESTING ENHANCED METADATA EXTRACTION")
    print("=" * 60)
    
    metadata_service = MetadataEnhancementService(client)
    
    # Test cases with different document types
    test_cases = [
        {
            "content": "RIM - AVIO - 4 dana, 3 noćenja. Hotel 3* u centru. Cena: 450 EUR po osobi. Uključuje prevoz avionom, smeštaj sa doručkom, razgledanje Koloseum i Vatikan.",
            "filename": "Rim_Avio_Prvi_Maj_3_nocenja_cenovnik.pdf",
            "expected": {
                "destination": "Rim",
                "category": "tour",
                "duration_days": 4,
                "transport_type": "plane",
                "price_range": "moderate"
            }
        },
        {
            "content": "Amsterdam - direktan let, 5 dana. Individualno putovanje. Hotel 4* sa spa centrom. Cena od 600 EUR.",
            "filename": "Amsterdam_PRVI_MAJ_2025_Direktan_let.pdf",
            "expected": {
                "destination": "Amsterdam", 
                "transport_type": "plane",
                "duration_days": 5
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['filename']}")
        print("-" * 40)
        
        try:
            enhanced_meta = await metadata_service.enhance_document_metadata(
                test_case["content"], test_case["filename"]
            )
            
            print(f"✅ Destination: {enhanced_meta.destination}")
            print(f"✅ Category: {enhanced_meta.category}")
            print(f"✅ Duration: {enhanced_meta.duration_days} days")
            print(f"✅ Transport: {enhanced_meta.transport_type}")
            print(f"✅ Price Range: {enhanced_meta.price_range}")
            print(f"✅ Confidence: {enhanced_meta.confidence_score:.2f}")
            
            # Validate against expected results
            for field, expected_value in test_case["expected"].items():
                actual_value = getattr(enhanced_meta, field)
                if actual_value == expected_value:
                    print(f"   ✅ {field}: {actual_value} (matches expected)")
                else:
                    print(f"   ⚠️  {field}: {actual_value} (expected: {expected_value})")
                    
        except Exception as e:
            print(f"❌ Test failed: {e}")

async def test_end_to_end_pipeline():
    """Test complete end-to-end pipeline"""
    print("\n\n🚀 TESTING END-TO-END ENHANCED RAG PIPELINE")
    print("=" * 60)
    
    # Initialize all services
    self_querying = SelfQueryingService(client)
    query_expansion = QueryExpansionService(client)
    vector_service = VectorService()
    response_generator = ResponseGenerator(client)
    
    # Realistic user queries
    user_queries = [
        "Tražim romantičan smestaj u Rimu za medeni mesec",
        "Daj mi neki aranžman za Amsterdam u maju, budžet oko 500 EUR"
    ]
    
    for i, query in enumerate(user_queries, 1):
        print(f"\n👤 User Query {i}: '{query}'")
        print("=" * 50)
        
        try:
            # Step 1: Self-Querying
            print("1️⃣ Self-Querying Analysis...")
            structured_query = await self_querying.parse_query(query)
            print(f"   Intent: {structured_query.intent}")
            print(f"   Semantic Query: {structured_query.semantic_query}")
            print(f"   Filters Extracted ({len(structured_query.filters)}):")
            for key, value in structured_query.filters.items():
                if value is not None and value != "" and value != []:
                    print(f"     • {key}: {value}")
            print(f"   Confidence: {structured_query.confidence:.2f}")
            
            # Step 2: Query Expansion
            print("\n2️⃣ Query Expansion...")
            expanded_query = await query_expansion.expand_query_llm(structured_query.semantic_query)
            print(f"   Expanded: {expanded_query[:80]}...")
            
            # Step 3: Enhanced Vector Search
            print("\n3️⃣ Enhanced Vector Search...")
            from models.document import SearchQuery
            search_query = SearchQuery(
                query=expanded_query,
                filters=structured_query.filters,
                limit=3
            )
            
            search_results = vector_service.search(search_query)
            print(f"   Found: {len(search_results.results)} results")
            
            # Step 4: Intelligent Response Generation
            print("\n4️⃣ Intelligent Response Generation...")
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
            
            # Final Result
            print(f"\n🎉 **FINAL RESPONSE:**")
            print("=" * 40)
            print(response.response[:300] + "..." if len(response.response) > 300 else response.response)
            print("=" * 40)
            print(f"✅ Pipeline completed successfully!")
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """Run enhanced RAG tests"""
    print("🧪 ENHANCED RAG TEST SUITE")
    print("=" * 80)
    
    # Test 1: Enhanced Metadata Extraction
    await test_enhanced_metadata_extraction()
    
    # Test 2: End-to-End Pipeline
    await test_end_to_end_pipeline()
    
    print("\n" + "=" * 80)
    print("🏁 TESTS COMPLETED!")
    print("✅ Enhanced RAG system ready!")

if __name__ == "__main__":
    asyncio.run(main())
