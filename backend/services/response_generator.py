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
Ti si TurBot, ekspertni turistički agent koji pomaže klijentima da pronađu najbolje turističke aranžmane. 
Odgovaraj na srpskom jeziku, prirodno i profesionalno.

KORISNIKOV UPIT: "{structured_query.semantic_query}"
INTENT: {structured_query.intent}
FILTTERI: {filters_summary}

PRONAĐENI REZULTATI:
{results_summary}

STRUKTURIRANI PODACI:
{json.dumps(structured_data, ensure_ascii=False, indent=2)}

ZADATAK:
Generiši prirodan, korisničan odgovor na srpskom jeziku koji:

1. ODGOVARA DIREKTNO na korisnikov upit
2. PREDSTAVLJA pronađene opcije jasno i organizovano
3. IZDVAJA ključne informacije (cene, lokacije, amenitije)
4. OBJAŠNJAVA zašto rezultati možda ne odgovaraju savršeno korisnikovim kriterijumima
5. PREDLAŽE ALTERNATIVE kada rezultati nisu idealni
6. KORISTI PRIRODAN, KONVERZACIJSKI ton
7. REFERENCIŠE izvore ("Prema aranžmanu XYZ...")
8. PREDLAŽE sledeće korake ili pitanja

POSEBNO VAŽNO:
- Ako nema rezultata za tačnu destinaciju, predloži slične destinacije
- Ako cene ne odgovaraju budžetu, objasni razliku i predloži alternative
- Ako datum ne odgovara, predloži slične datume
- Budi transparentan o ograničenjima pronađenih rezultata

STIL:
- Prirodan srpski jezik
- Profesionalan ali prijateljski ton
- Jasne i konkretne informacije
- Izbegavaj previše tehničke detalje
- Fokus na korisnu vrednost za klijenta

STRUKTURA ODGOVORA:
1. Kratko uvodno obraćanje
2. Glavni sadržaj sa opcijama
3. Izdvajanje najbitnijih detalja
4. Poziv na akciju ili sledeći korak

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
        template = self.response_templates.get(structured_query.intent, 
                                               "Evo rezultata vaše pretrage:")
        
        if not search_results:
            return "Nažalost, nije pronađen nijedan rezultat koji odgovara vašim kriterijumima. Molimo pokušajte sa drugačijim pretragom."
        
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