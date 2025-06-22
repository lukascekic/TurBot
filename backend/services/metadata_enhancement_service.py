import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from openai import AsyncOpenAI
import hashlib
from models.document import DocumentMetadata

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
    """AI-powered metadata enhancement using GPT-4o-mini for maximum precision"""
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        
    async def enhance_document_metadata(self, content: str, filename: str) -> DocumentMetadata:
        """
        Extract comprehensive metadata from document content using GPT-4o-mini
        
        Args:
            content: Document text content
            filename: Original filename for context
            
        Returns:
            Enhanced DocumentMetadata with AI-extracted fields
        """
        try:
            # Prepare content for analysis (truncate if too long)
            analysis_content = self._prepare_content_for_analysis(content)
            
            # Create comprehensive extraction prompt
            extraction_prompt = self._create_extraction_prompt(analysis_content, filename)
            
            # Call GPT-4o-mini for metadata extraction
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=500
            )
            
            # Parse AI response
            ai_response = response.choices[0].message.content
            metadata_dict = self._parse_ai_response(ai_response)
            
            # Add filename-based fallbacks
            metadata_dict = self._add_filename_based_metadata(metadata_dict, filename)
            
            # Ensure source_file is set
            metadata_dict['source_file'] = filename
            
            # Create DocumentMetadata object
            enhanced_metadata = DocumentMetadata(**metadata_dict)
            
            logger.info(f"Enhanced metadata for {filename}: destination={enhanced_metadata.destination}, category={enhanced_metadata.category}")
            return enhanced_metadata
            
        except Exception as e:
            logger.error(f"Error enhancing metadata for {filename}: {e}")
            # Return basic metadata as fallback
            return self._create_fallback_metadata(filename)
    
    def _get_system_prompt(self) -> str:
        """System prompt for metadata extraction"""
        return """Ti si ekspert za analizu turističkih dokumenata. Tvoj zadatak je da iz sadržaja dokumenta izvučeš precizne metadata.

VAŽNO: Odgovori SAMO u JSON formatu bez dodatnog teksta.

Analiziraj dokument i izvuci sledeće informacije:
- destination: Glavna destinacija (grad/zemlja) - OBAVEZNO
- category: tour/hotel/restaurant/attraction
- price_range: budget/moderate/expensive/luxury (na osnovu cena)
- duration_days: Broj dana putovanja (broj)
- transport_type: bus/plane/train/ship
- family_friendly: true/false (na osnovu sadržaja)
- seasonal: year_round/summer/winter/spring/autumn
- travel_month: konkretni mesec ako je spomenut
- price_details: JSON sa cenama (single, double, currency)
- confidence_score: Tvoja sigurnost u izvučene podatke (0.0-1.0)

Primer odgovora:
{
  "destination": "Rim",
  "category": "tour", 
  "price_range": "moderate",
  "duration_days": 4,
  "transport_type": "plane",
  "family_friendly": true,
  "seasonal": "year_round",
  "travel_month": "maj",
  "price_details": "{\"single\": 450, \"double\": 320, \"currency\": \"EUR\"}",
  "confidence_score": 0.9
}"""

    def _create_extraction_prompt(self, content: str, filename: str) -> str:
        """Create extraction prompt with content and filename context"""
        return f"""Analiziraj ovaj turistički dokument i izvuci metadata:

FILENAME: {filename}

SADRŽAJ DOKUMENTA:
{content}

Izvuci metadata u JSON formatu:"""

    def _prepare_content_for_analysis(self, content: str) -> str:
        """Prepare content for AI analysis (truncate if needed)"""
        # Limit to ~2000 characters to stay within token limits
        if len(content) > 2000:
            # Take first 1000 and last 1000 chars to capture both intro and pricing
            content = content[:1000] + "\n...\n" + content[-1000:]
        return content

    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into metadata dictionary"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                metadata_dict = json.loads(json_str)
                
                # Validate and clean the response
                return self._validate_and_clean_metadata(metadata_dict)
            else:
                logger.warning("No JSON found in AI response")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {}

    def _validate_and_clean_metadata(self, metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean AI-extracted metadata"""
        cleaned = {}
        
        # Destination (most important)
        if 'destination' in metadata_dict and metadata_dict['destination']:
            cleaned['destination'] = str(metadata_dict['destination']).strip()
            # Also set location for backward compatibility
            cleaned['location'] = cleaned['destination']
        
        # Category validation
        valid_categories = ['tour', 'hotel', 'restaurant', 'attraction']
        if metadata_dict.get('category') in valid_categories:
            cleaned['category'] = metadata_dict['category']
        
        # Price range validation
        valid_price_ranges = ['budget', 'moderate', 'expensive', 'luxury']
        if metadata_dict.get('price_range') in valid_price_ranges:
            cleaned['price_range'] = metadata_dict['price_range']
        
        # Duration (validate as integer)
        if 'duration_days' in metadata_dict:
            try:
                duration = int(metadata_dict['duration_days'])
                if 1 <= duration <= 30:  # Reasonable range
                    cleaned['duration_days'] = duration
            except (ValueError, TypeError):
                pass
        
        # Transport type validation
        valid_transport = ['bus', 'plane', 'train', 'ship']
        if metadata_dict.get('transport_type') in valid_transport:
            cleaned['transport_type'] = metadata_dict['transport_type']
        
        # Boolean fields
        if isinstance(metadata_dict.get('family_friendly'), bool):
            cleaned['family_friendly'] = metadata_dict['family_friendly']
        
        # Seasonal validation
        valid_seasonal = ['year_round', 'summer', 'winter', 'spring', 'autumn']
        if metadata_dict.get('seasonal') in valid_seasonal:
            cleaned['seasonal'] = metadata_dict['seasonal']
        
        # Travel month
        if 'travel_month' in metadata_dict and metadata_dict['travel_month']:
            cleaned['travel_month'] = str(metadata_dict['travel_month']).lower().strip()
        
        # Price details (keep as JSON string)
        if 'price_details' in metadata_dict:
            cleaned['price_details'] = str(metadata_dict['price_details'])
        
        # Confidence score validation
        if 'confidence_score' in metadata_dict:
            try:
                confidence = float(metadata_dict['confidence_score'])
                if 0.0 <= confidence <= 1.0:
                    cleaned['confidence_score'] = confidence
            except (ValueError, TypeError):
                pass
        
        return cleaned

    def _add_filename_based_metadata(self, metadata_dict: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Add filename-based metadata as fallback/enhancement"""
        filename_lower = filename.lower()
        
        # Destination detection from filename (high priority)
        filename_destinations = {
            'amsterdam': 'Amsterdam',
            'istanbul': 'Istanbul', 
            'rim': 'Rim',
            'roma': 'Rim',
            'rome': 'Rim',
            'pariz': 'Pariz',
            'paris': 'Pariz',
            'romanticna_francuska': 'Pariz',
            'portugalska': 'Lisabon',
            'portugal': 'Lisabon',
            'madrid': 'Madrid',
            'barcelona': 'Barcelona',
            'maroko': 'Marakeš',
            'morocco': 'Marakeš',
            'malta': 'Malta',
            'bari': 'Bari',
            'pulja': 'Pulja'
        }
        
        # If destination not found by AI, try filename
        if not metadata_dict.get('destination'):
            for keyword, destination in filename_destinations.items():
                if keyword in filename_lower:
                    metadata_dict['destination'] = destination
                    metadata_dict['location'] = destination  # Backward compatibility
                    break
        
        # Transport type from filename
        if not metadata_dict.get('transport_type'):
            if 'avio' in filename_lower or 'avion' in filename_lower:
                metadata_dict['transport_type'] = 'plane'
            elif 'bus' in filename_lower:
                metadata_dict['transport_type'] = 'bus'
        
        # Category from filename patterns
        if not metadata_dict.get('category'):
            if any(word in filename_lower for word in ['cenovnik', 'program', 'putovanja']):
                metadata_dict['category'] = 'tour'
        
        return metadata_dict

    def _create_fallback_metadata(self, filename: str) -> DocumentMetadata:
        """Create basic fallback metadata when AI extraction fails"""
        fallback_dict = {
            'source_file': filename,
            'confidence_score': 0.1  # Low confidence for fallback
        }
        
        # Add filename-based metadata
        fallback_dict = self._add_filename_based_metadata(fallback_dict, filename)
        
        return DocumentMetadata(**fallback_dict)

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