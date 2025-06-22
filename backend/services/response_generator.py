import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import AsyncOpenAI

from .self_querying_service import StructuredQuery

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ResponseData:
    """Response data with structured information"""
    response: str  # Natural language response
    sources: List[Dict[str, Any]]  # Source documents with metadata
    structured_data: Dict[str, Any]  # Structured information (prices, amenities, etc.)
    suggested_questions: List[str]  # Follow-up questions
    confidence: float  # Response confidence (0.0 to 1.0)
    
    def __post_init__(self):
        # Ensure lists are initialized
        if not isinstance(self.sources, list):
            self.sources = []
        if not isinstance(self.suggested_questions, list):
            self.suggested_questions = []
        if not isinstance(self.structured_data, dict):
            self.structured_data = {}
        
        # Ensure confidence is in valid range
        self.confidence = max(0.0, min(1.0, self.confidence))

class ResponseGenerator:
    """
    Advanced response generator that creates natural Serbian responses
    with source attribution and structured information presentation.
    """
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.cache = {}  # Simple in-memory cache
        
        # Response templates for different intents
        self.response_templates = {
            "search": "Na osnovu vaše pretrage pronašao sam sledeće opcije:",
            "recommendation": "Evo mojih preporuka za vas:",
            "comparison": "Evo poređenja opcija koje ste tražili:",
            "information": "Evo informacija koje ste tražili:",
            "booking": "Evo dostupnih opcija za rezervaciju:"
        }
        
        # Suggested questions templates
        self.suggested_questions_templates = {
            "hotel": [
                "Kakve su dodatne usluge u hotelu?",
                "Da li hotel ima spa ili wellness centar?",
                "Kakve su mogućnosti ishrane?",
                "Da li je hotel pogodan za porodice sa decom?"
            ],
            "tour": [
                "Šta je uključeno u cenu aranžmana?",
                "Kakav je prevoz predviđen?",
                "Da li postoje dodatni izleti?",
                "Koliko dana traje putovanje?"
            ],
            "restaurant": [
                "Kakva je kuhinja u restoranu?",
                "Da li je potrebna rezervacija?",
                "Kakve su cene jela?",
                "Da li imaju vegetarijanske opcije?"
            ]
        }

    async def generate_response(
        self, 
        search_results: List[Dict[str, Any]], 
        structured_query: StructuredQuery,
        context: Optional[Dict[str, Any]] = None
    ) -> ResponseData:
        """
        Generate comprehensive response with natural language and structured data
        """
        try:
            # Extract structured information from results
            structured_data = self._extract_structured_data(search_results)
            
            # Generate natural language response
            natural_response = await self._generate_natural_response(
                search_results, structured_query, structured_data, context
            )
            
            # Prepare sources with proper attribution
            sources = self._prepare_sources(search_results)
            
            # Generate suggested follow-up questions
            suggested_questions = self._generate_suggested_questions(
                structured_query, search_results
            )
            
            # Calculate response confidence
            confidence = self._calculate_confidence(search_results, structured_query)
            
            response_data = ResponseData(
                response=natural_response,
                sources=sources,
                structured_data=structured_data,
                suggested_questions=suggested_questions,
                confidence=confidence
            )
            
            logger.info(f"Generated response for intent '{structured_query.intent}' with {len(sources)} sources")
            return response_data
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Return basic fallback response
            return ResponseData(
                response="Izvinjavam se, došlo je do greške pri generisanju odgovora. Molimo pokušajte ponovo.",
                sources=[],
                structured_data={},
                suggested_questions=["Možete li precizirati svoju pretragu?"],
                confidence=0.1
            )

    async def _generate_natural_response(
        self, 
        search_results: List[Dict[str, Any]], 
        structured_query: StructuredQuery,
        structured_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate natural Serbian response using LLM
        """
        # Prepare context for LLM
        results_summary = self._prepare_results_summary(search_results)
        filters_summary = self._prepare_filters_summary(structured_query.filters)
        
        prompt = f"""
Ti si TurBot, profesionalni turistički agent. Odgovaraj ljubazno i korisno na srpskom jeziku.

KORISNIKOV UPIT: "{structured_query.semantic_query}"
TRAŽI: {filters_summary}

PRONAĐENI REZULTATI:
{results_summary}

KRITIČNO - UVEK PRIKAŽI PRONAĐENE REZULTATE:
- Ako ima rezultata - OBAVEZNO ih pomeni čak i ako se ne poklapaju svi kriterijumi
- Objasni šta se poklapa a šta ne (lokacija ✓, datum ✗, cena ✓)
- Daj konkretne opcije sa detaljima (naziv, cena, datum)

PRISTUP:
- Budi TRANSPARENTAN o poklapanju kriterijuma
- Uvek prikaži dostupne opcije pa tek onda alternative
- Koristi profesionalan ali prijatan ton
- Fokus na KONKRETNE INFORMACIJE i OPCIJE

STRUKTURA ODGOVORA:

1. **POZDRAV**: "Zdravo! [kratka procena]"

2. **DOSTUPNE OPCIJE** (ako ima rezultata):
   - Navedi 2-3 konkretne opcije sa detaljima
   - Objasni šta se poklapa a šta ne sa zahtevima
   
3. **ALTERNATIVE** (ako se ne poklapaju svi kriterijumi):
   - Predloži slične opcije ili datume
   - Objasni zašto su relevantne

4. **POZIV NA AKCIJU**:
   - "Da li vas neka od ovih opcija zanima?"

STIL:
- Profesionalan ali prijatan srpski
- Direktan i informativan
- Fokus na KONKRETNE OPCIJE i DETALJE
- Bez previše casual izraza

ODGOVOR:
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si TurBot, stručni turistički agent. Odgovaraj na srpskom jeziku, prirodno i korisničko."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7  # Slightly higher for more natural responses
            )
            
            natural_response = response.choices[0].message.content.strip()
            
            # Add source attribution if not already present
            if not any(word in natural_response.lower() for word in ["prema", "iz", "dokument", "aranžman"]):
                natural_response += f"\n\n📋 Informacije su pronađene u {len(search_results)} dokumenata naše baze."
            
            return natural_response
            
        except Exception as e:
            logger.warning(f"LLM response generation failed: {e}")
            # Return template-based response
            return self._generate_template_response(search_results, structured_query)

    def _generate_template_response(
        self, 
        search_results: List[Dict[str, Any]], 
        structured_query: StructuredQuery
    ) -> str:
        """
        Generate template-based response as fallback
        """
        if not search_results:
            # Generate helpful response even with no results
            filters = structured_query.filters or {}
            location = filters.get('location') or filters.get('destination')
            travel_month = filters.get('travel_month')
            category = filters.get('category')
            price_range = filters.get('price_range')
            
            response_parts = []
            
            # Acknowledge what they're looking for
            if location and travel_month:
                response_parts.append(f"Zdravo! Nažalost nemam aranžmane za {location} u {travel_month}-u u našoj trenutnoj bazi.")
            elif location:
                response_parts.append(f"Zdravo! Nažalost, trenutno nemam opcije za {location} koje odgovaraju vašim kriterijumima.")
            elif travel_month:
                response_parts.append(f"Zdravo! Nemam dostupne aranžmane za {travel_month} koji odgovaraju vašoj pretrazi.")
            elif category:
                response_parts.append(f"Zdravo! Trenutno nemam {category} opcije koje odgovaraju vašim zahtevima.")
            else:
                response_parts.append("Zdravo! Nažalost, nisu pronađeni rezultati za vašu pretragu.")
            
            # Suggest alternatives based on what was requested
            response_parts.append("\nAli evo šta mogu da predložim:")
            
            # Generate smart alternatives based on filters
            alternatives = self._generate_smart_alternatives(filters)
            for alternative in alternatives:
                response_parts.append(f"• {alternative}")
            
            response_parts.append("• Javite mi specifičnije zahteve pa da istražimo zajedno!")
            
            response_parts.append("\nDa li vas neka od ovih opcija zanima?")
            
            return "\n".join(response_parts)
        
        # Handle case with results
        template = self.response_templates.get(structured_query.intent, 
                                               "Evo rezultata vaše pretrage:")
        response_parts = [template]
        
        for i, result in enumerate(search_results[:3], 1):  # Limit to top 3 results
            document_name = result.get('document_name', 'Nepoznat dokument')
            content_preview = result.get('content', '')[:200] + "..."
            similarity = result.get('similarity', 0)
            
            response_parts.append(f"{i}. {document_name}")
            response_parts.append(f"   Relevantnost: {similarity:.1%}")
            response_parts.append(f"   {content_preview}")
            response_parts.append("")
        
        return "\n".join(response_parts)

    def _generate_smart_alternatives(self, filters: Dict[str, Any]) -> List[str]:
        """
        Generate smart alternative suggestions based on filters
        """
        alternatives = []
        
        location = filters.get('location') or filters.get('destination')
        travel_month = filters.get('travel_month')
        category = filters.get('category')
        price_range = filters.get('price_range')
        
        # Month-based alternatives
        if travel_month:
            month_alternatives = self._get_month_alternatives(travel_month)
            if month_alternatives:
                alternatives.extend(month_alternatives)
        
        # Location-based alternatives
        if location:
            location_alternatives = self._get_location_alternatives(location)
            if location_alternatives:
                alternatives.extend(location_alternatives)
        
        # Category-based alternatives
        if category:
            category_alternatives = self._get_category_alternatives(category)
            if category_alternatives:
                alternatives.extend(category_alternatives)
        
        # Price-based alternatives
        if price_range:
            price_alternatives = self._get_price_alternatives(price_range)
            if price_alternatives:
                alternatives.extend(price_alternatives)
        
        # Generic alternatives if nothing specific found
        if not alternatives:
            alternatives = [
                "Proverite slične destinacije u regionu",
                "Razmislite o alternativnim datumima putovanja",
                "Istražite različite tipove aranžmana"
            ]
        
        return alternatives[:4]  # Limit to 4 alternatives

    def _get_month_alternatives(self, travel_month: str) -> List[str]:
        """
        Get alternative months based on requested month
        """
        month_mapping = {
            'january': {'adjacent': ['december', 'february'], 'season': 'zimski'},
            'february': {'adjacent': ['january', 'march'], 'season': 'zimski'},
            'march': {'adjacent': ['february', 'april'], 'season': 'prolećni'},
            'april': {'adjacent': ['march', 'may'], 'season': 'prolećni'},
            'may': {'adjacent': ['april', 'june'], 'season': 'prolećni'},
            'june': {'adjacent': ['may', 'july'], 'season': 'letnji'},
            'july': {'adjacent': ['june', 'august'], 'season': 'letnji'},
            'august': {'adjacent': ['july', 'september'], 'season': 'letnji'},
            'september': {'adjacent': ['august', 'october'], 'season': 'jesenji'},
            'october': {'adjacent': ['september', 'november'], 'season': 'jesenji'},
            'november': {'adjacent': ['october', 'december'], 'season': 'jesenji'},
            'december': {'adjacent': ['november', 'january'], 'season': 'zimski'}
        }
        
        # Serbian month names
        serbian_months = {
            'january': 'januar', 'february': 'februar', 'march': 'mart',
            'april': 'april', 'may': 'maj', 'june': 'jun',
            'july': 'jul', 'august': 'avgust', 'september': 'septembar',
            'october': 'oktobar', 'november': 'novembar', 'december': 'decembar'
        }
        
        alternatives = []
        
        if travel_month in month_mapping:
            month_info = month_mapping[travel_month]
            adjacent_months = month_info['adjacent']
            season = month_info['season']
            
            # Adjacent months
            serbian_adjacent = [serbian_months.get(m, m) for m in adjacent_months]
            alternatives.append(f"Proverite aranžmane za {' ili '.join(serbian_adjacent)} - često su slični")
            
            # Seasonal suggestions
            if season == 'letnji':
                alternatives.append("Razmislite o destinacijama popularnima leti: Grčka, Turska, Hrvatska, Crna Gora")
            elif season == 'zimski':
                alternatives.append("Razmislite o zimskim destinacijama: Austrija, Švajcarska, Francuska (skijanje)")
            elif season == 'prolećni':
                alternatives.append("Prolećne destinacije: Italija, Španija, Portugalija su prelepe u to vreme")
            elif season == 'jesenji':
                alternatives.append("Jesenje destinacije: Turska, Egipat, Maroko imaju prijatne temperature")
        
        return alternatives

    def _get_location_alternatives(self, location: str) -> List[str]:
        """
        Get alternative locations based on requested location
        """
        location_groups = {
            'Rim': ['Firenca', 'Venecija', 'Milano', 'Napulj'],
            'Pariz': ['London', 'Amsterdam', 'Brisel', 'Madrid'],
            'Amsterdam': ['Brisel', 'Pariz', 'Berlin', 'Prag'],
            'Istanbul': ['Antalija', 'Kapadokija', 'Izmir', 'Bodrum'],
            'Madrid': ['Barselona', 'Sevilla', 'Lisabon', 'Porto'],
            'Atina': ['Solun', 'Santorini', 'Mikonos', 'Krit'],
            'Budva': ['Kotor', 'Herceg Novi', 'Tivat', 'Bar'],
            'Split': ['Dubrovnik', 'Zadar', 'Pula', 'Rijeka']
        }
        
        alternatives = []
        
        if location in location_groups:
            similar_cities = location_groups[location][:3]  # Top 3 alternatives
            alternatives.append(f"Slične destinacije: {', '.join(similar_cities)}")
            alternatives.append(f"{location} u drugim mesecima kada možda imamo više opcija")
        else:
            alternatives.append(f"Slične destinacije u istom regionu kao {location}")
            alternatives.append(f"{location} u drugim mesecima kada možda imamo više opcija")
        
        return alternatives

    def _get_category_alternatives(self, category: str) -> List[str]:
        """
        Get alternative categories based on requested category
        """
        category_alternatives = {
            'hotel': ['apartman', 'villa', 'resort', 'pansion'],
            'tour': ['izlet', 'tura', 'aranžman', 'paket'],
            'restaurant': ['kafić', 'bar', 'restoran', 'lokalna gastronomija'],
            'attraction': ['muzej', 'spomenik', 'park', 'kulturna baština']
        }
        
        alternatives = []
        
        if category in category_alternatives:
            alt_categories = category_alternatives[category][:2]
            alternatives.append(f"Razmislite o alternativama: {', '.join(alt_categories)}")
        
        return alternatives

    def _get_price_alternatives(self, price_range: str) -> List[str]:
        """
        Get alternative price ranges based on requested price range
        """
        price_alternatives = {
            'budget': ['moderate - možda nešto skuplje ali sa boljim sadržajem'],
            'moderate': ['budget - ekonomičnije opcije', 'expensive - luksuznije opcije'],
            'expensive': ['moderate - nešto povoljnije opcije'],
            'luxury': ['expensive - i dalje kvalitetno ali pristupačnije']
        }
        
        alternatives = []
        
        if price_range in price_alternatives:
            for alt in price_alternatives[price_range]:
                alternatives.append(f"Proverite {alt}")
        
        return alternatives

    def _extract_structured_data(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract structured data from search results
        """
        structured_data = {
            "total_results": len(search_results),
            "price_range": {"min": None, "max": None, "currency": "EUR"},
            "locations": [],
            "categories": [],
            "amenities": [],
            "average_similarity": 0.0
        }
        
        if not search_results:
            return structured_data
        
        # Aggregate data from results
        prices = []
        similarities = []
        
        for result in search_results:
            # Extract similarity
            similarity = result.get('similarity', 0)
            similarities.append(similarity)
            
            # Extract metadata
            if 'metadata' in result:
                metadata = result['metadata']
                
                # Locations
                location = metadata.get('location')
                if location and location not in structured_data["locations"]:
                    structured_data["locations"].append(location)
                
                # Categories
                category = metadata.get('category')
                if category and category not in structured_data["categories"]:
                    structured_data["categories"].append(category)
                
                # Amenities (if available in enhanced metadata)
                amenities = metadata.get('amenities', [])
                if isinstance(amenities, list):
                    for amenity in amenities:
                        if amenity and amenity not in structured_data["amenities"]:
                            structured_data["amenities"].append(amenity)
                
                # Prices (if available in enhanced metadata)
                price_details = metadata.get('price_details', {})
                if isinstance(price_details, dict):
                    price_per_person = price_details.get('price_per_person')
                    if price_per_person:
                        prices.append(price_per_person)
        
        # Calculate aggregated values
        if similarities:
            structured_data["average_similarity"] = sum(similarities) / len(similarities)
        
        if prices:
            structured_data["price_range"]["min"] = min(prices)
            structured_data["price_range"]["max"] = max(prices)
        
        return structured_data

    def _prepare_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare source information with proper attribution
        """
        sources = []
        
        for result in search_results:
            source = {
                "document_name": result.get('document_name', 'Nepoznat dokument'),
                "similarity": result.get('similarity', 0.0),
                "content_preview": result.get('content', '')[:300] + "...",
                "metadata": result.get('metadata', {})
            }
            
            # Add page number if available
            if 'page_number' in result and result['page_number']:
                source["page"] = result['page_number']
            
            sources.append(source)
        
        return sources

    def _prepare_results_summary(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Prepare concise summary of search results for LLM
        """
        if not search_results:
            return "Nema pronađenih rezultata."
        
        summary_parts = []
        
        for i, result in enumerate(search_results[:5], 1):  # Top 5 results
            document_name = result.get('document_name', f'Dokument {i}')
            content = result.get('content', '')[:400]  # Limit content length
            similarity = result.get('similarity', 0)
            
            summary_parts.append(f"REZULTAT {i}: {document_name} (relevantnost: {similarity:.1%})")
            summary_parts.append(content)
            summary_parts.append("---")
        
        return "\n".join(summary_parts)

    def _prepare_filters_summary(self, filters: Dict[str, Any]) -> str:
        """
        Prepare human-readable summary of applied filters
        """
        if not filters:
            return "Bez specifičnih filtera"
        
        filter_parts = []
        
        for key, value in filters.items():
            if value is not None:
                filter_parts.append(f"{key}: {value}")
        
        return ", ".join(filter_parts) if filter_parts else "Bez specifičnih filtera"

    def _generate_suggested_questions(
        self, 
        structured_query: StructuredQuery, 
        search_results: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate contextual follow-up questions
        """
        suggestions = []
        
        # Get base suggestions for detected categories
        for result in search_results[:3]:  # Check top 3 results
            metadata = result.get('metadata', {})
            category = metadata.get('category')
            
            if category in self.suggested_questions_templates:
                category_suggestions = self.suggested_questions_templates[category]
                for suggestion in category_suggestions:
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
        
        # Add generic suggestions if not enough specific ones
        if len(suggestions) < 3:
            generic_suggestions = [
                "Možete li mi dati više detalja o cenama?",
                "Da li postoje alternativne opcije?",
                "Kako mogu da rezervišem?",
                "Da li imate preporuke za dodatne aktivnosti?"
            ]
            
            for suggestion in generic_suggestions:
                if suggestion not in suggestions and len(suggestions) < 4:
                    suggestions.append(suggestion)
        
        return suggestions[:4]  # Limit to 4 suggestions

    def _calculate_confidence(
        self, 
        search_results: List[Dict[str, Any]], 
        structured_query: StructuredQuery
    ) -> float:
        """
        Calculate response confidence based on various factors
        """
        if not search_results:
            return 0.1
        
        # Base confidence from query parsing
        confidence = structured_query.confidence * 0.4
        
        # Add confidence from search results quality
        if search_results:
            avg_similarity = sum(r.get('similarity', 0) for r in search_results) / len(search_results)
            confidence += avg_similarity * 0.4
        
        # Add confidence from number of results
        result_count_factor = min(len(search_results) / 3, 1.0) * 0.2
        confidence += result_count_factor
        
        return min(1.0, confidence)

# Singleton pattern for service
_response_generator = None

def get_response_generator(client: AsyncOpenAI) -> ResponseGenerator:
    """Get or create singleton ResponseGenerator instance"""
    global _response_generator
    if _response_generator is None:
        _response_generator = ResponseGenerator(client)
    return _response_generator 