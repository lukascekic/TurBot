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
    
    def __init__(self, client: AsyncOpenAI, context_enhancer=None):
        self.client = client
        self.context_enhancer = context_enhancer
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

    async def parse_query_with_context(self, query: str, session_id: str) -> StructuredQuery:
        """Parse query with conversation context awareness"""
        try:
            print(f"\n🔍 SELF-QUERYING WITH CONTEXT:")
            print(f"   Original query: '{query}'")
            print(f"   Session ID: {session_id}")
            
            # Get conversation context
            conversation_context = await self.conversation_memory_service.build_hybrid_context_for_query(session_id)
            
            print(f"   Context received:")
            print(f"      Recent conversation: {len(conversation_context.get('recent_conversation', []))} messages")
            print(f"      Active entities: {conversation_context.get('active_entities', {})}")
            print(f"      Historical preferences: {len(conversation_context.get('historical_preferences', {}))} entities")
            
            # Enhance query with conversation context if available
            enhanced_query = query
            if conversation_context.get('recent_conversation') or conversation_context.get('active_entities'):
                print(f"   🔧 ENHANCING QUERY WITH CONTEXT...")
                enhanced_query = await self._enhance_query_with_context(query, conversation_context)
                print(f"   Enhanced query: '{enhanced_query}'")
            else:
                print(f"   No context available for query enhancement")
            
            # Parse the enhanced query
            structured_query = await self.parse_query(enhanced_query)
            
            # Merge context-derived filters
            context_filters = self._extract_filters_from_context(conversation_context)
            if context_filters:
                print(f"   🔗 MERGING CONTEXT FILTERS:")
                print(f"      Query filters: {structured_query.filters}")
                print(f"      Context filters: {context_filters}")
                
                # Merge filters (query filters take precedence)
                merged_filters = {**context_filters, **structured_query.filters}
                structured_query.filters = merged_filters
                
                print(f"      Merged filters: {merged_filters}")
            
            print(f"   ✅ Context-aware structured query:")
            print(f"      Semantic query: '{structured_query.semantic_query}'")
            print(f"      Intent: {structured_query.intent}")
            print(f"      Filters: {structured_query.filters}")
            print(f"      Confidence: {structured_query.confidence:.2f}")
            
            return structured_query
            
        except Exception as e:
            print(f"   ❌ ERROR in parse_query_with_context: {e}")
            logger.error(f"❌ Error in parse_query_with_context: {e}")
            # Fallback to basic parsing
            return await self.parse_query(query)

    async def _enhance_query_with_context(self, query: str, conversation_context: Dict[str, Any]) -> str:
        """Enhance query using conversation context"""
        try:
            print(f"      Building context-enhanced query...")
            
            # Build context prompt for query enhancement
            context_prompt = ""
            
            # Add recent conversation
            recent_conv = conversation_context.get('recent_conversation', [])
            if recent_conv:
                context_prompt += "NEDAVNI RAZGOVOR:\n"
                for msg in recent_conv:
                    role = "Korisnik" if msg['role'] == 'user' else "TurBot"
                    context_prompt += f"{role}: {msg['content']}\n"
                context_prompt += "\n"
            
            # Add active entities
            active_entities = conversation_context.get('active_entities', {})
            if active_entities:
                context_prompt += "AKTIVNI KONTEKST:\n"
                for entity_type, value in active_entities.items():
                    context_prompt += f"- {entity_type}: {value}\n"
                context_prompt += "\n"
            
            # Query enhancement prompt
            enhancement_prompt = f"""Analiziraj sledeći upit u kontekstu prethodnog razgovora i aktivnih entiteta.

{context_prompt}

TRENUTNI UPIT: "{query}"

Pojasni i proširi upit tako da bude jasniji i konkretniji na osnovu konteksta razgovora. 
- Ako se koriste zamenice (to, ono, tako), zameni ih konkretnim rečima
- Ako se pominje "detalji" ili "više informacija", specificiraj o čemu se radi
- Ako je upit nejasan, dodaj kontekst iz prethodnog razgovora
- Zadrži originalni jezik i stil upita

POBOLJŠANI UPIT:"""

            print(f"      Enhancement prompt prepared: {len(enhancement_prompt)} characters")
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si asistent koji pomaže u razumevanju korisničkih upita u kontekstu razgovora."},
                    {"role": "user", "content": enhancement_prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            enhanced_query = response.choices[0].message.content.strip()
            
            # Remove any quotes or extra formatting
            if enhanced_query.startswith('"') and enhanced_query.endswith('"'):
                enhanced_query = enhanced_query[1:-1]
            
            print(f"      Enhanced query generated: '{enhanced_query}'")
            return enhanced_query
            
        except Exception as e:
            print(f"      ❌ Query enhancement failed: {e}")
            logger.error(f"Query enhancement failed: {e}")
            return query  # Return original query on failure

    def _extract_filters_from_context(self, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract filters from conversation context"""
        try:
            print(f"      Extracting filters from context...")
            
            filters = {}
            
            # Extract from active entities
            active_entities = conversation_context.get('active_entities', {})
            if active_entities:
                print(f"         Active entities: {active_entities}")
                
                # Map entity types to filter names
                entity_filter_mapping = {
                    'destination': 'location',
                    'location': 'location',
                    'budget': 'price_range',
                    'price_range': 'price_range',
                    'category': 'category',
                    'travel_dates': 'travel_month',
                    'group_size': 'family_friendly'
                }
                
                for entity_type, value in active_entities.items():
                    if entity_type in entity_filter_mapping:
                        filter_name = entity_filter_mapping[entity_type]
                        filters[filter_name] = value
                        print(f"         Mapped {entity_type} -> {filter_name}: {value}")
            
            # Extract from historical preferences (lower priority)
            historical_prefs = conversation_context.get('historical_preferences', {})
            for entity_type, entity_data in historical_prefs.items():
                if isinstance(entity_data, dict) and 'value' in entity_data:
                    # Only use if not already set by active entities
                    filter_name = entity_type.replace('destination', 'location')
                    if filter_name not in filters:
                        filters[filter_name] = entity_data['value']
                        print(f"         Historical: {entity_type} -> {filter_name}: {entity_data['value']}")
            
            print(f"         Context filters extracted: {filters}")
            return filters
            
        except Exception as e:
            print(f"         ❌ Error extracting filters from context: {e}")
            logger.error(f"Error extracting filters from context: {e}")
            return {}

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