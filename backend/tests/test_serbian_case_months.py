#!/usr/bin/env python3

import asyncio
import logging
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from services.self_querying_service import SelfQueryingService

async def test_serbian_case_declensions():
    """Test Serbian case declensions for months"""
    
    # Initialize service
    service = SelfQueryingService(client)
    
    # Test cases with different Serbian case declensions
    test_queries = [
        # Nominativ (osnovni oblik)
        "Tražim hotel u Rimu u avgust",
        "Putovanje u Grčku u maj",
        "Aranžman za Španiju u jun",
        
        # Lokativ (u + lokativ)
        "Hotel u Amsterdamu u avgustu",
        "Smestaj u Rimu u maju",
        "Aranžman u junu za Grčku",
        
        # Genitiv (tokom + genitiv)
        "Putovanje tokom avgusta",
        "Hotel tokom maja u Rimu",
        "Aranžman tokom jula",
        
        # Genitiv (početkom + genitiv)
        "Putovanje početkom avgusta",
        "Hotel početkom maja",
        "Aranžman početkom juna",
        
        # Genitiv (krajem + genitiv)
        "Putovanje krajem avgusta",
        "Hotel krajem maja",
        "Aranžman krajem jula",
        
        # Genitiv (sredinom + genitiv)
        "Hotel sredinom avgusta u Rimu",
        "Putovanje sredinom maja",
        "Aranžman sredinom juna",
        
        # Akuzativ (za + akuzativ)
        "Rezervacija za august",
        "Booking za maj",
        "Putovanje za jun",
        
        # Compound phrases
        "Romantičan hotel u Rimu u avgustu do 400 EUR",
        "Porodični aranžman tokom maja za četiri osobe",
        "Letovanje početkom juna u Grčkoj"
    ]
    
    print("🧪 TESTING SERBIAN CASE DECLENSIONS FOR MONTHS")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n🔍 Testing: '{query}'")
        
        try:
            # Parse query
            result = await service.parse_query(query)
            
            # Extract month information
            travel_month = result.filters.get("travel_month")
            season = result.filters.get("season")
            
            print(f"   ✅ travel_month: {travel_month}")
            print(f"   ✅ season: {season}")
            print(f"   ✅ semantic_query: {result.semantic_query}")
            print(f"   ✅ confidence: {result.confidence}")
            
            # Validate month detection
            if travel_month:
                print(f"   🎯 MONTH DETECTED: {travel_month}")
            elif season:
                print(f"   🎯 SEASON DETECTED: {season}")
            else:
                print(f"   ❌ NO TEMPORAL INFO DETECTED")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 TESTING COMPLETE")

async def test_month_extraction_direct():
    """Test direct month extraction function"""
    
    service = SelfQueryingService(client)
    
    test_cases = [
        "u avgustu",
        "tokom avgusta", 
        "sredinom avgusta",
        "početkom avgusta",
        "krajem avgusta",
        "za avgust",
        "avgusta",
        "avgustom",
        "u maju",
        "tokom maja",
        "početkom maja",
        "u junu",
        "tokom juna",
        "u juliju",
        "u julu",
        "tokom julija"
    ]
    
    print("\n🧪 TESTING DIRECT MONTH EXTRACTION")
    print("=" * 50)
    
    for test_case in test_cases:
        result = service._extract_month_from_query(test_case.lower())
        print(f"'{test_case}' -> {result}")
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_serbian_case_declensions())
    asyncio.run(test_month_extraction_direct()) 