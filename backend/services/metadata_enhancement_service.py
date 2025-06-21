import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from openai import AsyncOpenAI
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class EnhancedMetadata:
    """Enhanced metadata structure for tourism documents"""
    # Basic fields (existing)
    category: str
    location: str
    price_range: str
    family_friendly: bool
    seasonal: str
    
    # New rich metadata fields
    subcategory: Optional[str] = None
    destinations: List[str] = None
    price_details: Dict[str, Any] = None
    amenities: List[str] = None
    duration_days: Optional[int] = None
    travel_dates: Dict[str, str] = None
    group_size: Dict[str, int] = None
    difficulty_level: Optional[str] = None
    transport_type: Optional[str] = None
    
    # Metadata quality tracking
    confidence_score: float = 0.0
    extraction_method: str = "llm"
    extracted_at: datetime = None
    
    def __post_init__(self):
        if self.destinations is None:
            self.destinations = []
        if self.price_details is None:
            self.price_details = {}
        if self.amenities is None:
            self.amenities = []
        if self.travel_dates is None:
            self.travel_dates = {}
        if self.group_size is None:
            self.group_size = {}
        if self.extracted_at is None:
            self.extracted_at = datetime.now()

class MetadataEnhancementService:
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self.cache: Dict[str, EnhancedMetadata] = {}
        
    async def enhance_document_metadata_comprehensive(
        self, 
        content: str, 
        filename: str, 
        existing_metadata: Dict[str, Any] = None
    ) -> EnhancedMetadata:
        """
        Comprehensive metadata extraction optimized for demo quality
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(content, filename)
            if cache_key in self.cache:
                logger.info(f"Cache hit for metadata: {filename}")
                return self.cache[cache_key]
            
            # Extract comprehensive metadata using LLM
            enhanced_metadata = await self._extract_comprehensive_metadata(
                content, filename, existing_metadata
            )
            
            # Cache the result
            self.cache[cache_key] = enhanced_metadata
            
            logger.info(f"Enhanced metadata for {filename}: {enhanced_metadata.category} - {enhanced_metadata.subcategory}")
            return enhanced_metadata
            
        except Exception as e:
            logger.error(f"Error enhancing metadata for '{filename}': {e}")
            # Fallback to existing metadata + basic enhancement
            return self._fallback_metadata_enhancement(content, filename, existing_metadata)
    
    async def _extract_comprehensive_metadata(
        self, 
        content: str, 
        filename: str, 
        existing_metadata: Dict[str, Any] = None
    ) -> EnhancedMetadata:
        """
        Use LLM to extract comprehensive metadata from document content
        """
        
        # Truncate content if too long (to save tokens)
        truncated_content = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""
Analiziraj ovaj dokument turističke agencije i izvuci detaljne metapodatke.

DOKUMENT: {filename}
SADRŽAJ:
{truncated_content}

IZVUCI SLEDEĆE METAPODATKE u JSON formatu:

{{
    "category": "tour|hotel|restaurant|attraction",
    "subcategory": "city_tour|beach_resort|cultural_experience|adventure|romantic_getaway|family_vacation",
    "destinations": ["lista lokacija - gradovi, zemlje, regioni"],
    "price_details": {{
        "currency": "EUR|USD|RSD",
        "price_per_person": number_or_null,
        "price_range_min": number_or_null,
        "price_range_max": number_or_null,
        "includes": ["lista šta je uključeno u cenu"]
    }},
    "amenities": ["lista sadržaja - bazen, spa, wifi, parking, klima, balkon, itd"],
    "duration_days": number_or_null,
    "travel_dates": {{
        "start_date": "YYYY-MM-DD format ili null",
        "end_date": "YYYY-MM-DD format ili null", 
        "flexible_dates": true_or_false,
        "season": "spring|summer|autumn|winter|year_round"
    }},
    "group_size": {{
        "min_size": number_or_null,
        "max_size": number_or_null,
        "optimal_size": number_or_null,
        "family_friendly": true_or_false
    }},
    "difficulty_level": "easy|moderate|challenging|null",
    "transport_type": "bus|plane|train|ship|car|mixed|null",
    "location": "glavna destinacija",
    "price_range": "budget|moderate|expensive|luxury",
    "seasonal": "year_round|spring|summer|autumn|winter",
    "family_friendly": true_or_false,
    "confidence_score": 0.0_to_1.0
}}

PRAVILA:
- Budi precizna i konzistentna
- Koristi null za nepoznate vrednosti
- Confidence score na osnovu jasnoće informacija u dokumentu
- Destinations lista treba da bude sveobuhvatna
- Amenities lista treba da bude detaljn

ODGOVORI SAMO SA JSON-om:
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si ekspert za analizu turističkih dokumenata. Odgovaraj samo validnim JSON-om."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.1
            )
            
            json_response = response.choices[0].message.content.strip()
            
            # Debug logging for JSON parsing issues
            if not json_response:
                logger.error(f"Empty LLM response for {filename}")
                return self._fallback_metadata_enhancement(content, filename, existing_metadata)
            
            logger.debug(f"LLM response for {filename}: {json_response[:200]}...")
            
            # Clean JSON response (remove markdown formatting if present)
            if json_response.startswith("```json"):
                json_response = json_response.replace("```json", "").replace("```", "").strip()
            elif json_response.startswith("```"):
                json_response = json_response.replace("```", "").strip()
            
            # Parse JSON response
            metadata_dict = json.loads(json_response)
            
            # Create EnhancedMetadata object
            enhanced_metadata = EnhancedMetadata(
                category=metadata_dict.get("category", "tour"),
                subcategory=metadata_dict.get("subcategory"),
                location=metadata_dict.get("location", ""),
                destinations=metadata_dict.get("destinations", []),
                price_details=metadata_dict.get("price_details", {}),
                amenities=metadata_dict.get("amenities", []),
                duration_days=metadata_dict.get("duration_days"),
                travel_dates=metadata_dict.get("travel_dates", {}),
                group_size=metadata_dict.get("group_size", {}),
                difficulty_level=metadata_dict.get("difficulty_level"),
                transport_type=metadata_dict.get("transport_type"),
                price_range=metadata_dict.get("price_range", "moderate"),
                seasonal=metadata_dict.get("seasonal", "year_round"),
                family_friendly=metadata_dict.get("family_friendly", False),
                confidence_score=metadata_dict.get("confidence_score", 0.7),
                extraction_method="llm_comprehensive"
            )
            
            # Validate and post-process
            enhanced_metadata = self._validate_and_enhance_metadata(enhanced_metadata, filename)
            
            return enhanced_metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {filename}: {e}")
            return self._fallback_metadata_enhancement(content, filename, existing_metadata)
        except Exception as e:
            logger.error(f"LLM metadata extraction failed for {filename}: {e}")
            return self._fallback_metadata_enhancement(content, filename, existing_metadata)
    
    def _validate_and_enhance_metadata(self, metadata: EnhancedMetadata, filename: str) -> EnhancedMetadata:
        """
        Validate and enhance metadata with filename-based insights
        """
        # Filename-based location enhancement
        filename_lower = filename.lower()
        
        # Geographic location enhancement from filename
        location_mappings = {
            "amsterdam": "Amsterdam",
            "istanbul": "Istanbul", 
            "rim": "Rim",
            "roma": "Rim",
            "rome": "Rim",
            "beograd": "Beograd",
            "belgrade": "Beograd",
            "pariz": "Pariz",
            "paris": "Pariz",
            "maroko": "Maroko",
            "morocco": "Maroko",
            "malta": "Malta",
            "bari": "Bari",
            "pulja": "Pulja",
            "portugal": "Portugalska",
            "portugals": "Portugalska",
            "lisabon": "Lisabon",
            "porto": "Porto",
            "andaluz": "Andaluzija",
            "espana": "Španija",
            "madrid": "Madrid",
            "toskana": "Toskana",
            "italy": "Italija",
            "italija": "Italija"
        }
        
        for key, location in location_mappings.items():
            if key in filename_lower:
                if not metadata.location or metadata.location == "":
                    metadata.location = location
                if location not in metadata.destinations:
                    metadata.destinations.append(location)
                break
        
        # Price range adjustment based on filename patterns
        if any(term in filename_lower for term in ["lux", "luxury", "premium", "vip"]):
            metadata.price_range = "luxury"
        elif any(term in filename_lower for term in ["budget", "economic", "jeftin"]):
            metadata.price_range = "budget"
        
        # Category enhancement based on filename
        if any(term in filename_lower for term in ["hotel", "resort", "vila", "apartman"]):
            if metadata.category == "tour":
                metadata.subcategory = "accommodation_focused_tour"
        
        # Ensure minimum confidence score
        if metadata.confidence_score < 0.3:
            metadata.confidence_score = 0.5  # Reasonable default
        
        return metadata
    
    def _fallback_metadata_enhancement(
        self, 
        content: str, 
        filename: str, 
        existing_metadata: Dict[str, Any] = None
    ) -> EnhancedMetadata:
        """
        Fallback metadata enhancement using pattern matching
        """
        logger.info(f"Using fallback metadata enhancement for {filename}")
        
        # Start with existing metadata if available
        base_metadata = existing_metadata or {}
        
        # Basic pattern matching for key information
        price_info = self._extract_price_info(content)
        duration_info = self._extract_duration_info(content)
        amenities_info = self._extract_amenities_info(content)
        
        enhanced_metadata = EnhancedMetadata(
            category=base_metadata.get("category", "tour"),
            location=base_metadata.get("location", ""),
            price_range=base_metadata.get("price_range", "moderate"),
            family_friendly=base_metadata.get("family_friendly", False),
            seasonal=base_metadata.get("seasonal", "year_round"),
            price_details=price_info,
            duration_days=duration_info,
            amenities=amenities_info,
            confidence_score=0.4,
            extraction_method="pattern_matching"
        )
        
        # Apply filename-based enhancements
        enhanced_metadata = self._validate_and_enhance_metadata(enhanced_metadata, filename)
        
        return enhanced_metadata
    
    def _extract_price_info(self, content: str) -> Dict[str, Any]:
        """Extract price information using regex patterns"""
        price_patterns = [
            r'(\d+)\s*(?:EUR|€|eur)',
            r'(\d+)\s*(?:USD|\$|usd)',
            r'(\d+)\s*(?:RSD|din|rsd)',
            r'cena.*?(\d+)',
            r'price.*?(\d+)',
            r'(\d+)\s*po\s*osobi'
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            prices.extend([int(match) for match in matches])
        
        if prices:
            return {
                "currency": "EUR",  # Default assumption
                "price_range_min": min(prices),
                "price_range_max": max(prices),
                "includes": ["basic_package"]
            }
        
        return {}
    
    def _extract_duration_info(self, content: str) -> Optional[int]:
        """Extract trip duration using regex patterns"""
        duration_patterns = [
            r'(\d+)\s*(?:dana|day|days)',
            r'(\d+)\s*(?:noći|night|nights)',
            r'(\d+)\s*(?:dan|day)'
        ]
        
        for pattern in duration_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                return int(matches[0])
        
        return None
    
    def _extract_amenities_info(self, content: str) -> List[str]:
        """Extract amenities using keyword matching"""
        amenity_keywords = {
            "bazen": ["pool", "swimming pool", "bazen"],
            "spa": ["spa", "wellness", "masaža"],
            "wifi": ["wifi", "wi-fi", "internet"],
            "parking": ["parking", "parkiranje"],
            "klima": ["air conditioning", "klima", "ac"],
            "balkon": ["balkon", "balcony", "terasa"],
            "restoran": ["restoran", "restaurant", "dining"],
            "bar": ["bar", "lounge", "kafić"],
            "fitness": ["fitness", "gym", "teretana"],
            "room_service": ["room service", "sobni servis"]
        }
        
        found_amenities = []
        content_lower = content.lower()
        
        for amenity, keywords in amenity_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                found_amenities.append(amenity)
        
        return found_amenities
    
    def _get_cache_key(self, content: str, filename: str) -> str:
        """Generate cache key for content and filename"""
        content_hash = hashlib.md5(content[:1000].encode()).hexdigest()
        filename_hash = hashlib.md5(filename.encode()).hexdigest()
        return f"{filename_hash}_{content_hash}"
    
    async def batch_enhance_metadata(
        self, 
        documents: List[Tuple[str, str, Dict[str, Any]]]  # (content, filename, existing_metadata)
    ) -> List[EnhancedMetadata]:
        """
        Batch process multiple documents for metadata enhancement
        """
        logger.info(f"Starting batch metadata enhancement for {len(documents)} documents")
        
        # Process in smaller batches to avoid overwhelming the LLM
        batch_size = 5
        results = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [
                self.enhance_document_metadata_comprehensive(content, filename, existing_metadata)
                for content, filename, existing_metadata in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
                    # Add fallback metadata
                    results.append(EnhancedMetadata(
                        category="tour",
                        location="",
                        price_range="moderate",
                        family_friendly=False,
                        seasonal="year_round",
                        confidence_score=0.1,
                        extraction_method="error_fallback"
                    ))
                else:
                    results.append(result)
            
            # Small delay between batches to be nice to the API
            await asyncio.sleep(0.5)
        
        logger.info(f"Completed batch metadata enhancement. Success rate: {len([r for r in results if r.confidence_score > 0.3])/len(results)*100:.1f}%")
        return results

# Singleton instance
_metadata_enhancement_service = None

def get_metadata_enhancement_service(openai_client: AsyncOpenAI) -> MetadataEnhancementService:
    """
    Get singleton instance of MetadataEnhancementService
    """
    global _metadata_enhancement_service
    if _metadata_enhancement_service is None:
        _metadata_enhancement_service = MetadataEnhancementService(openai_client)
    return _metadata_enhancement_service 