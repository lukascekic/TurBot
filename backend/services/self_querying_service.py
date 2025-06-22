import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from openai import AsyncOpenAI

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class StructuredQuery:
    """Structured query with semantic content and extracted filters"""
    semantic_query: str  # Main search query for vector search
    filters: Dict[str, Any]  # Metadata filters
    intent: str  # Query intent classification
    confidence: float  # Parser confidence (0.0 to 1.0)
    
    def __post_init__(self):
        # Ensure filters is a dict
        if not isinstance(self.filters, dict):
            self.filters = {}
        
        # Ensure confidence is in valid range
        self.confidence = max(0.0, min(1.0, self.confidence))

class SelfQueryingService:
    """
    Advanced self-querying service that parses natural language queries 
    into structured search queries with semantic content and metadata filters.
    """
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.cache = {}  # Simple in-memory cache
        
        # Intent classifications
        self.intents = {
            "search": ["tražim", "potreban", "hoću", "želim", "imam potrebu"],
            "recommendation": ["preporuči", "predloži", "najbolji", "šta predlažete"],
            "comparison": ["uporedi", "razlika", "bolje", "vs", "ili"],
            "information": ["kakav", "koliko", "kada", "gde", "kako", "šta"],
            "booking": ["rezerviši", "bukiraj", "zakaži", "dostupno"]
        }
        
        # Price range mappings (EUR)
        self.price_ranges = {
            "budget": {"min": 0, "max": 100},
            "moderate": {"min": 100, "max": 300}, 
            "expensive": {"min": 300, "max": 600},
            "luxury": {"min": 600, "max": float('inf')}
        }
        
        # Season mappings
        self.seasons = {
            "proleće": "spring", "prolece": "spring", "mart": "spring", "april": "spring", "maj": "spring",
            "leto": "summer", "jun": "summer", "juli": "summer", "avg": "summer", "avgust": "summer",
            "jesen": "autumn", "septembar": "autumn", "oktobar": "autumn", "novembar": "autumn",
            "zima": "winter", "decembar": "winter", "januar": "winter", "februar": "winter"
        }
        
        # Month mappings with ALL Serbian case declensions
        self.months = {
            # Januar - January (all cases)
            "januar": "january", "januara": "january", "januaru": "january", "januarom": "january",
            "u januaru": "january", "tokom januara": "january", "početkom januara": "january",
            
            # Februar - February (all cases) 
            "februar": "february", "februara": "february", "februaru": "february", "februarom": "february",
            "u februaru": "february", "tokom februara": "february", "početkom februara": "february",
            
            # Mart - March (all cases)
            "mart": "march", "marta": "march", "martu": "march", "martom": "march",
            "u martu": "march", "tokom marta": "march", "početkom marta": "march",
            
            # April - April (all cases)
            "april": "april", "aprila": "april", "aprilu": "april", "aprilom": "april", 
            "u aprilu": "april", "tokom aprila": "april", "početkom aprila": "april",
            
            # Maj - May (all cases)
            "maj": "may", "maja": "may", "maju": "may", "majem": "may",
            "u maju": "may", "tokom maja": "may", "početkom maja": "may",
            
            # Jun - June (all cases)
            "jun": "june", "juna": "june", "junu": "june", "junom": "june",
            "u junu": "june", "tokom juna": "june", "početkom juna": "june",
            
            # Juli - July (all cases)
            "juli": "july", "julija": "july", "juliju": "july", "julijem": "july", "julu": "july",
            "u juliju": "july", "u julu": "july", "tokom julija": "july", "početkom julija": "july",
            
            # Avgust - August (all cases) - NAJVAŽNIJI PRIMER
            "avg": "august", "avgust": "august", "avgusta": "august", "avgustu": "august", "avgustom": "august",
            "u avgustu": "august", "tokom avgusta": "august", "početkom avgusta": "august", 
            "sredinom avgusta": "august", "krajem avgusta": "august", "za avgust": "august",
            
            # Septembar - September (all cases)
            "septembar": "september", "septembra": "september", "septembru": "september", "septembrom": "september",
            "u septembru": "september", "tokom septembra": "september", "početkom septembra": "september",
            
            # Oktobar - October (all cases)
            "oktobar": "october", "oktobra": "october", "oktobru": "october", "oktobrom": "october",
            "u oktobru": "october", "tokom oktobra": "october", "početkom oktobra": "october",
            
            # Novembar - November (all cases)
            "novembar": "november", "novembra": "november", "novembru": "november", "novembrom": "november",
            "u novembru": "november", "tokom novembra": "november", "početkom novembra": "november",
            
            # Decembar - December (all cases)
            "decembar": "december", "decembra": "december", "decembru": "december", "decembrom": "december",
            "u decembru": "december", "tokom decembra": "december", "početkom decembra": "december"
        }

    async def parse_query(self, natural_query: str) -> StructuredQuery:
        """
        Parse natural language query into structured format
        """
        try:
            # Check cache first
            cache_key = natural_query.lower().strip()
            if cache_key in self.cache:
                logger.info(f"Cache hit for query: {natural_query}")
                return self.cache[cache_key]
            
            # Classify intent first (fast operation)
            intent = self._classify_intent(natural_query)
            
            # Use LLM for comprehensive parsing
            structured = await self._parse_with_llm(natural_query, intent)
            
            # Enhance with pattern-based parsing
            enhanced = self._enhance_with_patterns(natural_query, structured)
            
            # Validate and normalize
            final_query = self._validate_and_normalize(enhanced)
            
            # Cache the result
            self.cache[cache_key] = final_query
            
            logger.info(f"Parsed query: '{natural_query}' -> Intent: {final_query.intent}, Filters: {len(final_query.filters)}")
            return final_query
            
        except Exception as e:
            logger.error(f"Error parsing query '{natural_query}': {e}")
            # Return fallback structured query
            return StructuredQuery(
                semantic_query=natural_query,
                filters={},
                intent="search",
                confidence=0.3
            )

    async def _parse_with_llm(self, query: str, intent: str) -> StructuredQuery:
        """
        Use LLM to parse the query into structured format
        """
        prompt = f"""
Ti si ekspert za analizu turističkih upita na srpskom jeziku. Analiziraj ovaj upit i izvuci strukturirane informacije.

UPIT: "{query}"
INTENT: {intent}

Izvuci sledeće informacije u JSON formatu:

{{
    "semantic_query": "glavna suština pretrage bez filtera (npr. 'hotel smestaj' umesto 'hotel u Rimu do 200 EUR')",
    "filters": {{
        "location": "grad ili zemlja ako je spomenuto (npr. 'Rim', 'Italija', 'Amsterdam')",
        "category": "hotel|restaurant|attraction|tour ako je jasno",
        "price_range": "budget|moderate|expensive|luxury na osnovu spomenute cene",
        "price_max": number_ili_null_ako_je_spomenuta_maksimalna_cena_u_EUR,
        "group_size": number_ili_null_broj_osoba_ako_je_spomenuto,
        "family_friendly": true_ili_false_ako_je_spomenuto_porodica_deca,
        "amenities": ["lista_amenitija_ako_spomenuto", "spa", "bazen", "parking"],
        "season": "spring|summer|autumn|winter ako je spomenuto vreme",
        "travel_month": "january|february|march|april|may|june|july|august|september|october|november|december - SPECIFIČAN mesec",
        "duration_days": number_ili_null_broj_dana_ako_spomenuto,
        "subcategory": "romantic_getaway|family_vacation|cultural_experience|adventure ako jasno"
    }},
    "confidence": 0.0_do_1.0_koliko_si_siguran_u_parsing
}}

VAŽNO - SRPSKI PADEŽI:
- Prepoznaj sve padežne oblike meseci: "avgust" = "u avgustu" = "tokom avgusta" = "sredinom avgusta" = "avgusta" = "avgustom"
- Meseci po padežima: januar/januara/u januaru, februar/februara/u februaru, mart/marta/u martu, april/aprila/u aprilu, maj/maja/u maju, jun/juna/u junu, juli/julija/u juliju, avgust/avgusta/u avgustu, septembar/septembra/u septembru, oktobar/oktobra/u oktobru, novembar/novembra/u novembru, decembar/decembra/u decembru
- travel_month ima PRIORITET nad season - ako vidiš specifičan mesec koristi travel_month
- Primeri: "u avgustu" -> travel_month: "august", "tokom maja" -> travel_month: "may"

KRITIČNO - UVEK EKSTRAKTUJ AKO JE MOGUĆE:
- category: UVEK pokušaj da odredis category na osnovu konteksta:
  * "letovanje", "more", "plaža", "odmor" -> category: "tour"
  * "hotel", "smestaj", "apartman" -> category: "hotel"  
  * "restoran", "hrana", "jelo" -> category: "restaurant"
  * "muzej", "crkva", "spomenik" -> category: "attraction"
- price_range: UVEK pokušaj da procenis na osnovu konteksta:
  * "jeftino", "budžet", "povoljno" -> price_range: "budget"
  * "skup", "luksuz", "premium" -> price_range: "luxury"
  * "srednji", "normalno" -> price_range: "moderate"

PRAVILA:
- semantic_query treba da bude kratak i fokusiran na suštinu
- Koristi null za nepoznate vrednosti
- location treba da bude u srpskom obliku (Rim, ne Rome) 
- price_range automatski na osnovu price_max: <100=budget, 100-300=moderate, 300-600=expensive, >600=luxury
- travel_month ima prioritet nad season
- confidence visok (>0.8) samo ako si siguran u većinu filtera
- PRIORITET: category i price_range su kritični za queries bez location

ODGOVORI SAMO JSON:
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si ekspert za analizu turističkih upita. Odgovaraj samo validnim JSON-om."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            json_response = response.choices[0].message.content.strip()
            
            # Clean JSON response (remove markdown if present)
            if json_response.startswith("```json"):
                json_response = json_response.replace("```json", "").replace("```", "").strip()
            elif json_response.startswith("```"):
                json_response = json_response.replace("```", "").strip()
            
            # Parse JSON
            parsed_data = json.loads(json_response)
            
            return StructuredQuery(
                semantic_query=parsed_data.get("semantic_query", query),
                filters=parsed_data.get("filters", {}),
                intent=intent,
                confidence=parsed_data.get("confidence", 0.7)
            )
            
        except Exception as e:
            logger.warning(f"LLM parsing failed for '{query}': {e}")
            # Return basic structured query
            return StructuredQuery(
                semantic_query=query,
                filters={},
                intent=intent,
                confidence=0.4
            )

    def _classify_intent(self, query: str) -> str:
        """
        Classify query intent using pattern matching
        """
        query_lower = query.lower()
        
        # Check for each intent category
        for intent, keywords in self.intents.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent
        
        # Default to search if no clear intent
        return "search"

    def _extract_month_from_query(self, query_lower: str) -> Optional[str]:
        """
        Extract month from query handling all Serbian case declensions.
        Returns normalized English month name or None.
        """
        # Use longest match first approach for compound phrases like "u avgustu"
        sorted_months = sorted(self.months.items(), key=lambda x: len(x[0]), reverse=True)
        
        for serbian_form, english_month in sorted_months:
            if serbian_form in query_lower:
                logger.debug(f"Detected month: '{serbian_form}' -> {english_month}")
                return english_month
        
        return None

    def _enhance_with_patterns(self, query: str, structured: StructuredQuery) -> StructuredQuery:
        """
        Enhance LLM parsing with pattern-based extraction
        """
        query_lower = query.lower()
        enhanced_filters = structured.filters.copy()
        
        # Destination extraction (prioritize LLM result, fallback to patterns)
        if not enhanced_filters.get("destination") and not enhanced_filters.get("location"):
            destination = self._extract_destination_patterns(query_lower)
            if destination:
                enhanced_filters["destination"] = destination
                enhanced_filters["location"] = destination  # Backward compatibility
        
        # Duration extraction
        if not enhanced_filters.get("duration_days"):
            duration = self._extract_duration_patterns(query_lower)
            if duration:
                enhanced_filters["duration_days"] = duration
        
        # Transport type extraction
        if not enhanced_filters.get("transport_type"):
            transport = self._extract_transport_patterns(query_lower)
            if transport:
                enhanced_filters["transport_type"] = transport
        
        # Extract price information with regex
        price_patterns = [
            r'do (\d+) eur',  # "do 200 EUR"
            r'(\d+) eur',     # "300 EUR"
            r'budžet (\d+)',  # "budžet 500"
            r'(\d+)€',        # "250€"
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, query_lower)
            if match and not enhanced_filters.get("price_max"):
                price = int(match.group(1))
                enhanced_filters["price_max"] = price
                # Auto-classify price range
                if price < 100:
                    enhanced_filters["price_range"] = "budget"
                elif price < 300:
                    enhanced_filters["price_range"] = "moderate"
                elif price < 600:
                    enhanced_filters["price_range"] = "expensive"
                else:
                    enhanced_filters["price_range"] = "luxury"
                break
        
        # Extract group size
        group_patterns = [
            r'za (\d+) osob',    # "za 4 osobe"
            r'(\d+) osob',       # "4 osobe"
            r'(\d+) član',       # "4 člana"
            r'(\d+) ljudi',      # "4 ljudi"
        ]
        
        for pattern in group_patterns:
            match = re.search(pattern, query_lower)
            if match and not enhanced_filters.get("group_size"):
                enhanced_filters["group_size"] = int(match.group(1))
                break
        
        # Family-friendly detection
        family_keywords = ["porodic", "deca", "porodičn", "familij", "family"]
        if any(keyword in query_lower for keyword in family_keywords):
            enhanced_filters["family_friendly"] = True
        
        # Month detection with case declension handling (specific month takes priority)
        detected_month = self._extract_month_from_query(query_lower)
        if detected_month and not enhanced_filters.get("travel_month"):
            enhanced_filters["travel_month"] = detected_month
        
        # Season detection (fallback if no specific month)
        if not enhanced_filters.get("travel_month"):
            for serbian_season, english_season in self.seasons.items():
                if serbian_season in query_lower and not enhanced_filters.get("season"):
                    enhanced_filters["season"] = english_season
                    break
        
        # Update structured query
        return StructuredQuery(
            semantic_query=structured.semantic_query,
            filters=enhanced_filters,
            intent=structured.intent,
            confidence=min(1.0, structured.confidence + 0.1)  # Small boost for pattern enhancement
        )

    def _validate_and_normalize(self, structured: StructuredQuery) -> StructuredQuery:
        """
        Validate and normalize the structured query
        """
        filters = structured.filters.copy()
        
        # Remove None/null values
        filters = {k: v for k, v in filters.items() if v is not None and v != "null"}
        
        # SMART CATEGORY MAPPING - Map user requests to actual data categories
        if "category" in filters:
            user_category = filters["category"]
            
            # Most tourism documents are actually categorized as 'tour' in our database
            # Map user intentions to actual database categories
            category_mapping = {
                "hotel": "tour",      # Hotel requests -> tour packages (which include hotels)
                "smestaj": "tour",    # Accommodation requests -> tour packages
                "smeštaj": "tour",    # Serbian accommodation -> tour packages
                "apartman": "tour",   # Apartment requests -> tour packages
                "vila": "tour",       # Villa requests -> tour packages
                "resort": "tour",     # Resort requests -> tour packages
                "aranžman": "tour",   # Arrangement requests -> tour packages
                "putovanje": "tour",  # Travel requests -> tour packages
                "tura": "tour",       # Tour requests -> tour packages
                "paket": "tour",      # Package requests -> tour packages
                # Keep original mappings for actual categories
                "tour": "tour",
                "restaurant": "restaurant", 
                "attraction": "attraction"
            }
            
            # Apply mapping if available
            if user_category in category_mapping:
                filters["category"] = category_mapping[user_category]
                logger.debug(f"Mapped category '{user_category}' -> '{filters['category']}'")
        
        # Normalize location names (Serbian variants)
        if "location" in filters:
            location = filters["location"]
            location_mapping = {
                "rome": "Rim",
                "roma": "Rim", 
                "italy": "Rim",
                "italija": "Rim",
                "istanbul": "Istanbul",
                "turkey": "Istanbul",
                "turska": "Istanbul",
                "amsterdam": "Amsterdam",
                "netherlands": "Amsterdam",
                "holandija": "Amsterdam",
                "greece": "Grčka",
                "grcka": "Grčka",
                "grčka": "Grčka",
                "athens": "Atina",
                "atina": "Atina"
            }
            
            # Apply location mapping
            normalized_location = location_mapping.get(location.lower(), location)
            filters["location"] = normalized_location
        
        return StructuredQuery(
            semantic_query=structured.semantic_query,
            filters=filters,
            intent=structured.intent,
            confidence=structured.confidence
        )

    def get_filter_summary(self, structured_query: StructuredQuery) -> str:
        """
        Generate human-readable summary of applied filters
        """
        filters = structured_query.filters
        if not filters:
            return "Bez dodatnih filtera"
        
        summary_parts = []
        
        if "location" in filters:
            summary_parts.append(f"lokacija: {filters['location']}")
        
        if "category" in filters:
            summary_parts.append(f"kategorija: {filters['category']}")
        
        if "price_max" in filters:
            summary_parts.append(f"cena do: {filters['price_max']} EUR")
        elif "price_range" in filters:
            summary_parts.append(f"cenovni rang: {filters['price_range']}")
        
        if "group_size" in filters:
            summary_parts.append(f"grupa: {filters['group_size']} osoba")
        
        if "family_friendly" in filters and filters["family_friendly"]:
            summary_parts.append("porodično")
        
        if "travel_month" in filters:
            summary_parts.append(f"mesec: {filters['travel_month']}")
        elif "season" in filters:
            summary_parts.append(f"sezona: {filters['season']}")
        
        return "Filteri: " + ", ".join(summary_parts)

# Singleton pattern for service
    def _extract_destination_patterns(self, query_lower: str) -> Optional[str]:
        """Extract destination using pattern matching"""
        destinations = {
            'amsterdam': 'Amsterdam',
            'amsterdamu': 'Amsterdam',
            'amsterdama': 'Amsterdam',
            'istanbul': 'Istanbul', 
            'istanbulu': 'Istanbul',
            'istanbula': 'Istanbul',
            'rim': 'Rim',
            'rimu': 'Rim',
            'rima': 'Rim',
            'roma': 'Rim',
            'rome': 'Rim',
            'pariz': 'Pariz',
            'parizu': 'Pariz',
            'pariza': 'Pariz',
            'paris': 'Pariz',
            'madrid': 'Madrid',
            'madridu': 'Madrid',
            'madrida': 'Madrid',
            'barcelona': 'Barcelona',
            'barceloni': 'Barcelona',
            'barcelone': 'Barcelona',
            'maroko': 'Marakeš',
            'maroku': 'Marakeš',
            'maroka': 'Marakeš',
            'malta': 'Malta',
            'malti': 'Malta',
            'malte': 'Malta',
            'bari': 'Bari',
            'bariju': 'Bari',
            'barija': 'Bari',
            'pulja': 'Pulja',
            'pulji': 'Pulja',
            'pulje': 'Pulja'
        }
        
        # Use longest match first
        for dest_variant, dest_name in sorted(destinations.items(), key=len, reverse=True):
            if dest_variant in query_lower:
                return dest_name
        
        return None
    
    def _extract_duration_patterns(self, query_lower: str) -> Optional[int]:
        """Extract duration in days using pattern matching"""
        import re
        
        # Patterns for duration
        duration_patterns = [
            r'(\d+) dan[a]?',  # "3 dana", "5 dan"
            r'(\d+) noć[i]?',  # "4 noći", "3 noć"
            r'(\d+) noc[i]?',  # "4 noci", "3 noc"
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_transport_patterns(self, query_lower: str) -> Optional[str]:
        """Extract transport type using pattern matching"""
        transport_mapping = {
            'avion': 'plane',
            'avionom': 'plane',
            'avio': 'plane',
            'let': 'plane',
            'letom': 'plane',
            'autobus': 'bus',
            'autobusom': 'bus',
            'bus': 'bus',
            'busom': 'bus',
            'voz': 'train',
            'vozom': 'train',
            'železnica': 'train',
            'brod': 'ship',
            'brodom': 'ship',
            'krstarenje': 'ship'
        }
        
        for transport_term, transport_type in transport_mapping.items():
            if transport_term in query_lower:
                return transport_type
        
        return None

# Singleton pattern for service
_self_querying_service = None

def get_self_querying_service(client: AsyncOpenAI) -> SelfQueryingService:
    """Get or create singleton SelfQueryingService instance"""
    global _self_querying_service
    if _self_querying_service is None:
        _self_querying_service = SelfQueryingService(client)
    return _self_querying_service 