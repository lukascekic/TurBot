import sys
import os
# Add parent directory to path to import services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import pytest
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Import the services
from services.query_expansion_service import QueryExpansionService, get_query_expansion_service
from services.metadata_enhancement_service import MetadataEnhancementService, get_metadata_enhancement_service, EnhancedMetadata

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPhase3a:
    """
    Comprehensive test suite for Phase 3a: Query Expansion & Metadata Enhancement
    """
    
    @pytest.fixture
    def openai_client(self):
        """Create OpenAI client for testing"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")
        
        return AsyncOpenAI(api_key=api_key)
    
    @pytest.fixture
    def query_expansion_service(self, openai_client):
        """Create query expansion service"""
        return QueryExpansionService(openai_client)
    
    @pytest.fixture
    def metadata_enhancement_service(self, openai_client):
        """Create metadata enhancement service"""
        return MetadataEnhancementService(openai_client)

    # Query Expansion Tests
    
    @pytest.mark.asyncio
    async def test_query_expansion_basic_serbian(self, query_expansion_service):
        """Test basic Serbian query expansion"""
        query = "hotel u Rimu"
        
        expanded = await query_expansion_service.expand_query_llm(query)
        
        # Basic validations
        assert expanded is not None
        assert len(expanded) > len(query)
        assert "OR" in expanded
        assert "hotel" in expanded.lower()
        assert any(term in expanded.lower() for term in ["rim", "roma", "rome"])
        
        logger.info(f"✅ Basic expansion test passed: '{query}' -> '{expanded}'")
    
    @pytest.mark.asyncio
    async def test_query_expansion_semantic_serbian(self, query_expansion_service):
        """Test semantic expansion for Serbian tourism queries"""
        test_cases = [
            ("romantican smestaj", ["romantic", "spa", "za parove", "luksuzno", "intimno"]),
            ("porodicno letovanje", ["family", "deca", "kids", "plaža", "more"]),
            ("kulturna tura", ["cultural", "muzej", "historical", "heritage", "galerija"]),
            ("luksuzni hotel", ["luxury", "premium", "spa", "vrhunski", "boutique"])
        ]
        
        for query, expected_terms in test_cases:
            expanded = await query_expansion_service.expand_query_llm(query)
            
            # Check that at least some expected semantic terms are present
            found_terms = [term for term in expected_terms if term.lower() in expanded.lower()]
            
            assert len(found_terms) >= 2, f"Expected semantic terms not found in expansion of '{query}': {expanded}"
            
            logger.info(f"✅ Semantic expansion test passed: '{query}' -> found terms: {found_terms}")
    
    @pytest.mark.asyncio
    async def test_query_expansion_geographic_variants(self, query_expansion_service):
        """Test geographic variant expansion"""
        geographic_test_cases = [
            ("hotel u Rimu", ["rim", "roma", "rome", "italy", "italija"]),
            ("tura u Istanbul", ["istanbul", "turkey", "turska", "constantinople"]),
            ("putovanje u Amsterdam", ["amsterdam", "netherlands", "holandija", "holland"]),
            ("smestaj u Beogradu", ["beograd", "belgrade", "serbia", "srbija"])
        ]
        
        for query, expected_locations in geographic_test_cases:
            expanded = await query_expansion_service.expand_query_llm(query)
            
            found_locations = [loc for loc in expected_locations if loc.lower() in expanded.lower()]
            
            assert len(found_locations) >= 2, f"Geographic variants not found for '{query}': {expanded}"
            
            logger.info(f"✅ Geographic expansion test passed: '{query}' -> found: {found_locations}")
    
    @pytest.mark.asyncio
    async def test_query_expansion_caching(self, query_expansion_service):
        """Test that query expansion caching works correctly"""
        query = "test hotel cache"
        
        # First call
        start_time = asyncio.get_event_loop().time()
        result1 = await query_expansion_service.expand_query_llm(query)
        first_duration = asyncio.get_event_loop().time() - start_time
        
        # Second call (should be cached)
        start_time = asyncio.get_event_loop().time()
        result2 = await query_expansion_service.expand_query_llm(query)
        second_duration = asyncio.get_event_loop().time() - start_time
        
        # Results should be identical
        assert result1 == result2
        
        # Second call should be significantly faster (cached)
        assert second_duration < first_duration * 0.5
        
        logger.info(f"✅ Caching test passed: First: {first_duration:.2f}s, Second: {second_duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_query_expansion_fallback(self, query_expansion_service):
        """Test fallback mechanism when LLM fails"""
        # Simulate LLM failure by using invalid client
        query_expansion_service.client = None
        
        query = "hotel restoran"
        expanded = await query_expansion_service.expand_query_llm(query)
        
        # Should still return expansion using fallback
        assert expanded is not None
        assert len(expanded) > len(query)
        assert "OR" in expanded
        
        logger.info(f"✅ Fallback test passed: '{query}' -> '{expanded}'")

    # Metadata Enhancement Tests
    
    @pytest.mark.asyncio
    async def test_metadata_enhancement_comprehensive(self, metadata_enhancement_service):
        """Test comprehensive metadata extraction"""
        sample_content = """
        Amsterdam - PRVI MAJ 2025 - Direktan let
        
        Cena: 450 EUR po osobi
        Trajanje: 5 dana / 4 noći
        Transport: Direktan let iz Beograda
        
        Program uključuje:
        - Smeštaj u hotelu 4* u centru
        - Doručak svaki dan
        - Transfer aerodrom-hotel-aerodrom
        - Panoramski obilazak grada
        
        Hotel sadržaji:
        - Bazen i spa centar
        - Besplatan WiFi
        - Parking
        - Fitnes centar
        
        Pogodno za porodice sa decom.
        """
        
        filename = "Amsterdam_PRVI_MAJ_2025_cenovnik.pdf"
        
        enhanced_metadata = await metadata_enhancement_service.enhance_document_metadata_comprehensive(
            sample_content, filename
        )
        
        # Validate extracted metadata
        assert enhanced_metadata is not None
        assert enhanced_metadata.category in ["tour", "hotel", "restaurant", "attraction"]
        assert "Amsterdam" in enhanced_metadata.location or "Amsterdam" in enhanced_metadata.destinations
        assert enhanced_metadata.price_details is not None
        assert enhanced_metadata.price_details.get("currency") in ["EUR", "USD", "RSD"]
        assert enhanced_metadata.duration_days == 5
        assert len(enhanced_metadata.amenities) > 0
        assert "bazen" in enhanced_metadata.amenities or "spa" in enhanced_metadata.amenities
        assert enhanced_metadata.family_friendly == True
        assert enhanced_metadata.confidence_score > 0.5
        
        logger.info(f"✅ Comprehensive metadata test passed:")
        logger.info(f"  Category: {enhanced_metadata.category}")
        logger.info(f"  Location: {enhanced_metadata.location}")
        logger.info(f"  Destinations: {enhanced_metadata.destinations}")
        logger.info(f"  Price details: {enhanced_metadata.price_details}")
        logger.info(f"  Amenities: {enhanced_metadata.amenities}")
        logger.info(f"  Duration: {enhanced_metadata.duration_days} days")
        logger.info(f"  Confidence: {enhanced_metadata.confidence_score}")
    
    @pytest.mark.asyncio
    async def test_metadata_enhancement_filename_intelligence(self, metadata_enhancement_service):
        """Test filename-based metadata enhancement"""
        test_cases = [
            ("Istanbul_avio_uskrs_2025.pdf", "Istanbul"),
            ("Rim_Prvi_maj_hotel_cenovnik.pdf", "Rim"),
            ("Maroko_putovanje_luxury.pdf", "Maroko"), 
            ("Portugal_Lisabon_Porto_tura.pdf", "Portugalska")
        ]
        
        sample_content = "Turistička tura sa hotelskim smeštajem. Cena 300 EUR."
        
        for filename, expected_location in test_cases:
            enhanced_metadata = await metadata_enhancement_service.enhance_document_metadata_comprehensive(
                sample_content, filename
            )
            
            # Check that location is correctly extracted from filename
            assert (expected_location in enhanced_metadata.location or 
                    expected_location in enhanced_metadata.destinations), \
                f"Location '{expected_location}' not found for filename '{filename}'"
            
            logger.info(f"✅ Filename intelligence test passed: {filename} -> {enhanced_metadata.location}")
    
    @pytest.mark.asyncio
    async def test_metadata_enhancement_price_extraction(self, metadata_enhancement_service):
        """Test price extraction from various formats"""
        price_test_cases = [
            ("Cena: 450 EUR po osobi", {"currency": "EUR", "price_per_person": 450}),
            ("Price: $300 per person", {"currency": "USD", "price_per_person": 300}),
            ("od 200 do 500 EUR", {"currency": "EUR", "price_range_min": 200, "price_range_max": 500}),
            ("Cena hotela 120€ za noć", {"currency": "EUR", "price_per_night": 120})
        ]
        
        for content, expected_price_info in price_test_cases:
            enhanced_metadata = await metadata_enhancement_service.enhance_document_metadata_comprehensive(
                content, "test.pdf"
            )
            
            # Check that some price information was extracted
            assert enhanced_metadata.price_details is not None
            
            if "currency" in expected_price_info:
                assert enhanced_metadata.price_details.get("currency") == expected_price_info["currency"]
            
            logger.info(f"✅ Price extraction test: '{content}' -> {enhanced_metadata.price_details}")
    
    @pytest.mark.asyncio
    async def test_metadata_enhancement_amenities_detection(self, metadata_enhancement_service):
        """Test amenities detection"""
        content_with_amenities = """
        Hotel 5* sa luksuznim sadržajima:
        - Bazen sa pogledom na more
        - Spa i wellness centar  
        - Besplatan WiFi u celom hotelu
        - Privatni parking
        - Klimatizovane sobe
        - Balkon sa pogledom
        - Restoran sa internacionalnom kuhinjom
        - Fitness centar
        - Room service 24h
        """
        
        enhanced_metadata = await metadata_enhancement_service.enhance_document_metadata_comprehensive(
            content_with_amenities, "luxury_hotel.pdf"
        )
        
        expected_amenities = ["bazen", "spa", "wifi", "parking", "klima", "balkon", "restoran", "fitness"]
        found_amenities = [amenity for amenity in expected_amenities if amenity in enhanced_metadata.amenities]
        
        assert len(found_amenities) >= 5, f"Expected more amenities, found: {enhanced_metadata.amenities}"
        
        logger.info(f"✅ Amenities detection test passed: Found {len(found_amenities)} amenities: {enhanced_metadata.amenities}")
    
    @pytest.mark.asyncio
    async def test_metadata_enhancement_fallback(self, metadata_enhancement_service):
        """Test fallback mechanism for metadata enhancement"""
        # Simulate LLM failure
        metadata_enhancement_service.client = None
        
        content = "Hotel u Rimu. Cena 300 EUR. 5 dana."
        filename = "test_fallback.pdf"
        
        enhanced_metadata = await metadata_enhancement_service.enhance_document_metadata_comprehensive(
            content, filename
        )
        
        # Should still return metadata using pattern matching fallback
        assert enhanced_metadata is not None
        assert enhanced_metadata.extraction_method == "pattern_matching"
        assert enhanced_metadata.confidence_score > 0
        
        logger.info(f"✅ Metadata fallback test passed: {enhanced_metadata.extraction_method}")

    # Integration Tests
    
    @pytest.mark.asyncio 
    async def test_phase3a_integration(self, query_expansion_service, metadata_enhancement_service):
        """Test integration between query expansion and metadata enhancement"""
        
        # Sample document
        document_content = """
        Romantičan vikend u Rimu
        Luksuzni hotel 5* u centru grada
        Cena: 650 EUR po paru
        Uključuje: spa tretmane, privatni transfer
        """
        filename = "romantic_rome_weekend.pdf"
        
        # Step 1: Extract enhanced metadata
        enhanced_metadata = await metadata_enhancement_service.enhance_document_metadata_comprehensive(
            document_content, filename
        )
        
        # Step 2: Test query expansion for related queries
        related_queries = [
            "romantican hotel rim",
            "luksuzni smestaj roma", 
            "spa hotel italy"
        ]
        
        for query in related_queries:
            expanded_query = await query_expansion_service.expand_query_llm(query)
            
            # Check that expansion would help find this document
            metadata_terms = [enhanced_metadata.location.lower()] + [d.lower() for d in enhanced_metadata.destinations]
            amenity_terms = [a.lower() for a in enhanced_metadata.amenities]
            
            overlap_found = any(term in expanded_query.lower() for term in metadata_terms + amenity_terms)
            
            assert overlap_found, f"Query '{query}' expansion doesn't overlap with document metadata"
            
            logger.info(f"✅ Integration test passed: Query '{query}' would match document")
        
        logger.info("✅ Phase 3a integration test completed successfully!")

# Demo Scenarios for Testing

@pytest.mark.asyncio
async def test_demo_scenarios():
    """Test real demo scenarios"""
    
    # Initialize services
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    
    client = AsyncOpenAI(api_key=api_key)
    query_service = get_query_expansion_service(client)
    metadata_service = get_metadata_enhancement_service(client)
    
    # Demo queries that will be used in presentation
    demo_queries = [
        "potreban mi je hotel u centru amsterdama",
        "romantican smestaj za dvoje u rimu",
        "porodicno letovanje na moru",
        "kulturna tura kroz italiju",
        "luksuzni spa hotel"
    ]
    
    logger.info("🎯 Running DEMO SCENARIOS for Phase 3a")
    
    for query in demo_queries:
        expanded = await query_service.expand_query_llm(query)
        logger.info(f"📝 Demo Query: '{query}'")
        logger.info(f"🔍 Expanded: '{expanded}'")
        logger.info("---")
    
    # Sample document metadata extraction
    sample_doc = """
    Amsterdam - Prvi Maj 2025
    Hotel 4* u centru grada
    Cena: 420 EUR po osobi
    5 dana / 4 noći
    Uključuje: doručak, transfer, city tour
    Hotel amenities: spa, bazen, parking, wifi
    """
    
    metadata = await metadata_service.enhance_document_metadata_comprehensive(
        sample_doc, "Amsterdam_Prvi_Maj_2025.pdf"
    )
    
    logger.info("📊 Sample Document Metadata:")
    logger.info(f"  Category: {metadata.category}")
    logger.info(f"  Location: {metadata.location}")
    logger.info(f"  Price Details: {metadata.price_details}")
    logger.info(f"  Amenities: {metadata.amenities}")
    logger.info(f"  Confidence: {metadata.confidence_score}")
    
    logger.info("🎉 DEMO SCENARIOS completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_demo_scenarios()) 