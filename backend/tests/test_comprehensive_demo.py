import sys
import os
# Add parent directory to path to import services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

from services.query_expansion_service import get_query_expansion_service
from services.metadata_enhancement_service import get_metadata_enhancement_service

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def comprehensive_demo():
    """
    Comprehensive demo showing query expansion + metadata for multiple scenarios
    """
    
    # Initialize services
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return
    
    client = AsyncOpenAI(api_key=api_key)
    query_service = get_query_expansion_service(client)
    metadata_service = get_metadata_enhancement_service(client)
    
    logger.info("🎯 COMPREHENSIVE DEMO - Query Expansion + Metadata Enhancement")
    logger.info("=" * 80)
    
    # Demo scenarios with both query and sample document
    demo_scenarios = [
        {
            "user_query": "romantican hotel u rimu", 
            "sample_document": """
            Romantičan vikend u Rimu - Hotel 5*
            Luksuzni boutique hotel u srcu Rima
            Cena: 580 EUR po paru (2 noći)
            Uključuje: spa tretmane, privatni balkon, šampanjac
            Amenities: spa, jacuzzi, room service, fine dining
            """,
            "filename": "romantic_rome_hotel.pdf"
        },
        {
            "user_query": "porodicno letovanje na moru",
            "sample_document": """
            Porodično letovanje - Grčka 2025
            Hotel 4* directly na plaži
            Cena: 350 EUR po osobi (7 dana)
            Za porodice sa decom - animacija, bazen, playground
            Amenities: bazen, kids club, plaža, parking, wifi
            """,
            "filename": "family_greece_vacation.pdf"
        },
        {
            "user_query": "luksuzni spa hotel",
            "sample_document": """
            Premium Spa Resort - Zlatibor
            5* luksuzni resort sa wellness centrom
            Cena: 450 EUR po osobi (3 dana)
            Premium spa tretmani, gourmet restorani
            Amenities: spa, wellness, indoor pool, golf, fine dining
            """,
            "filename": "luxury_spa_zlatibor.pdf"
        }
    ]
    
    for i, scenario in enumerate(demo_scenarios, 1):
        logger.info(f"\n🎪 SCENARIO {i}: {scenario['user_query'].upper()}")
        logger.info("-" * 60)
        
        # Step 1: Query Expansion
        logger.info("🔍 Query Expansion:")
        expanded = await query_service.expand_query_llm(scenario['user_query'])
        logger.info(f"  Original: '{scenario['user_query']}'")
        logger.info(f"  Expanded: '{expanded}'")
        
        # Step 2: Document Metadata Enhancement
        logger.info("\n📊 Document Metadata:")
        metadata = await metadata_service.enhance_document_metadata_comprehensive(
            scenario['sample_document'], 
            scenario['filename']
        )
        
        logger.info(f"  📁 Category: {metadata.category} ({metadata.subcategory})")
        logger.info(f"  📍 Location: {metadata.location}")
        logger.info(f"  💰 Price: {metadata.price_details}")
        logger.info(f"  🏨 Amenities: {metadata.amenities}")
        logger.info(f"  👨‍👩‍👧‍👦 Family Friendly: {metadata.family_friendly}")
        logger.info(f"  🎯 Confidence: {metadata.confidence_score}")
        
        # Step 3: Query-Document Matching Analysis
        logger.info("\n🎯 Query-Document Matching:")
        
        # Check if expanded query would match document metadata
        expanded_lower = expanded.lower()
        metadata_terms = [metadata.location.lower()] + [d.lower() for d in metadata.destinations]
        amenity_terms = [a.lower() for a in metadata.amenities]
        category_terms = [metadata.category, metadata.subcategory]
        
        all_metadata_terms = metadata_terms + amenity_terms + [t for t in category_terms if t]
        
        matches = [term for term in all_metadata_terms if term and term in expanded_lower]
        
        if matches:
            logger.info(f"  ✅ MATCH FOUND: {matches}")
            logger.info(f"  🎉 This document would be retrieved for the query!")
        else:
            logger.info(f"  ❌ NO DIRECT MATCH: Query expansion might need improvement")
        
        logger.info("=" * 60)
    
    logger.info("\n🎉 COMPREHENSIVE DEMO COMPLETED!")
    logger.info("💡 Analysis: Query expansion creates broader search terms that help find relevant documents")
    logger.info("📈 Metadata enhancement provides structured information for better user experience")

if __name__ == "__main__":
    asyncio.run(comprehensive_demo()) 