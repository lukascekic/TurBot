import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from openai import AsyncOpenAI

from models.conversation import TourismEntity, EntityExtractionResult

logger = logging.getLogger(__name__)

class NamedEntityExtractor:
    """
    Tourism-specific named entity extraction for Serbian language
    Optimized for conversation memory and hybrid context approach
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        
        # Tourism entity categories with Serbian language keywords
        self.tourism_entities = {
            "destination": {
                "keywords": ["grad", "mesto", "zemlja", "destinacija", "lokacija", "u", "za"],
                "locations": ["Rim", "Roma", "Pariz", "Paris", "Amsterdam", "Grčka", "Greece", "Turska", "Turkey", 
                             "Istanbul", "Maroko", "Morocco", "Egipat", "Egypt", "Španija", "Spain", "Madrid",
                             "Portugalia", "Portugal", "Lisabon", "Porto", "Italija", "Italy", "Milano", "Venecija",
                             "Beograd", "Novi Sad", "Niš", "Kragujevac", "Split", "Zagreb", "Ljubljana"]
            },
            "accommodation": {
                "keywords": ["hotel", "smeštaj", "apartman", "vila", "resort", "hostel", "pensiona", "smestaj"],
                "types": ["3*", "4*", "5*", "luxury", "budget", "boutique", "spa hotel", "city hotel"]
            },
            "budget": {
                "keywords": ["cena", "troškovi", "budžet", "košta", "EUR", "€", "din", "dinar", "jeftino", "skupo"],
                "price_indicators": ["do", "od", "oko", "maksimalno", "minimum", "budžet", "per", "po"]
            },
            "travel_dates": {
                "keywords": ["datum", "period", "vreme", "kada", "mesec", "sezona", "dana", "noćenja"],
                "months": ["januar", "februar", "mart", "april", "maj", "jun", "jul", "avgust", 
                          "septembar", "oktobar", "novembar", "decembar"],
                "seasons": ["leto", "zima", "proleće", "jesen", "letovanje", "zimovanje"]
            },
            "group_composition": {
                "keywords": ["osoba", "osobe", "deca", "dete", "odrasli", "porodica", "grupa", "ljudi"],
                "numbers": ["dva", "tri", "četiri", "pet", "šest", "sedam", "osam", "2", "3", "4", "5", "6", "7", "8"]
            },
            "preferences": {
                "keywords": ["familijno", "deca", "spa", "bazen", "plaza", "centar", "wifi", "parking", "doručak"],
                "amenities": ["spa", "wellness", "fitness", "pool", "beach", "restaurant", "bar", "wifi", "parking"]
            },
            "transport": {
                "keywords": ["avion", "avio", "autobus", "bus", "voz", "auto", "prevoz", "transport"],
                "types": ["flight", "plane", "bus", "train", "car", "transfer"]
            },
            "activities": {
                "keywords": ["obilazak", "izlet", "kultura", "muzej", "plaža", "kupovina", "shopping", "spa"],
                "types": ["sightseeing", "cultural", "beach", "adventure", "wellness", "shopping", "nightlife"]
            }
        }
        
        logger.info("✅ NamedEntityExtractor initialized with Serbian tourism vocabulary")
    
    async def extract_entities_from_message(self, message: str, conversation_history: Optional[List[str]] = None) -> EntityExtractionResult:
        """
        Extract tourism entities from a single message
        
        Args:
            message: User message content
            conversation_history: Previous messages for context (optional)
            
        Returns:
            EntityExtractionResult with extracted entities
        """
        try:
            start_time = datetime.now()
            
            # First try rule-based extraction (fast)
            rule_based_entities = await self._extract_entities_rule_based(message)
            
            # Then enhance with LLM extraction (comprehensive)
            llm_entities = await self._extract_entities_with_llm(message, conversation_history)
            
            # Merge results intelligently
            merged_entities = await self._merge_entity_results(rule_based_entities, llm_entities)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Determine confidence based on extraction methods
            confidence = self._calculate_extraction_confidence(rule_based_entities, llm_entities, merged_entities)
            
            return EntityExtractionResult(
                entities=merged_entities,
                confidence=confidence,
                extraction_method="hybrid",
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"❌ Entity extraction failed for message: {e}")
            return EntityExtractionResult(
                entities={},
                confidence=0.1,
                extraction_method="failed",
                processing_time=0.0
            )
    
    async def _extract_entities_rule_based(self, message: str) -> Dict[str, TourismEntity]:
        """Rule-based entity extraction using keywords and patterns"""
        entities = {}
        message_lower = message.lower()
        timestamp = datetime.now()
        
        try:
            # Extract destination
            destination = self._extract_destination(message_lower)
            if destination:
                entities["destination"] = TourismEntity(
                    entity_type="destination",
                    entity_value=destination,
                    confidence=0.8,
                    first_mentioned=timestamp,
                    last_mentioned=timestamp,
                    frequency=1
                )
            
            # Extract budget/price information
            budget_info = self._extract_budget(message_lower)
            if budget_info:
                entities.update(budget_info)
            
            # Extract travel dates
            date_info = self._extract_dates(message_lower)
            if date_info:
                entities.update(date_info)
            
            # Extract group composition
            group_info = self._extract_group_composition(message_lower)
            if group_info:
                entities.update(group_info)
            
            # Extract accommodation preferences
            accommodation_info = self._extract_accommodation(message_lower)
            if accommodation_info:
                entities.update(accommodation_info)
            
            # Extract transport preferences
            transport_info = self._extract_transport(message_lower)
            if transport_info:
                entities.update(transport_info)
            
            logger.info(f"🔍 Rule-based extraction found {len(entities)} entities")
            return entities
            
        except Exception as e:
            logger.error(f"❌ Rule-based extraction failed: {e}")
            return {}
    
    async def _extract_entities_with_llm(self, message: str, conversation_history: Optional[List[str]] = None) -> Dict[str, TourismEntity]:
        """LLM-based entity extraction for comprehensive understanding"""
        try:
            # Prepare context for LLM
            context_text = ""
            if conversation_history:
                context_text = f"Prethodna konverzacija:\n" + "\n".join(conversation_history[-3:]) + f"\n\nTrenutna poruka: {message}"
            else:
                context_text = f"Poruka: {message}"
            
            # Create extraction prompt
            prompt = self._create_llm_extraction_prompt(context_text)
            
            # Call LLM
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si ekspert za analizu turističkih upita na srpskom jeziku. Izvuci strukturirane informacije iz korisničkih poruka."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.1
            )
            
            # Parse LLM response
            llm_response = response.choices[0].message.content.strip()
            entities = await self._parse_llm_entity_response(llm_response)
            
            logger.info(f"🤖 LLM extraction found {len(entities)} entities")
            return entities
            
        except Exception as e:
            logger.error(f"❌ LLM extraction failed: {e}")
            return {}
    
    def _extract_destination(self, message: str) -> Optional[str]:
        """Extract destination from message using keyword matching"""
        # Check for explicit location mentions
        for location in self.tourism_entities["destination"]["locations"]:
            if location.lower() in message:
                return location
        
        # Check for location patterns (u + city, za + country)
        location_patterns = [
            r'u\s+([A-ZŠĐČĆŽ][a-zšđčćž]+)',
            r'za\s+([A-ZŠĐČĆŽ][a-zšđčćž]+)',
            r'do\s+([A-ZŠĐČĆŽ][a-zšđčćž]+)',
            r'destinacij[ai]\s+([A-ZŠĐČĆŽ][a-zšđčćž]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, message)
            if match:
                potential_location = match.group(1)
                # Validate against known locations
                for known_location in self.tourism_entities["destination"]["locations"]:
                    if potential_location.lower() == known_location.lower():
                        return known_location
        
        return None
    
    def _extract_budget(self, message: str) -> Dict[str, TourismEntity]:
        """Extract budget/price information"""
        entities = {}
        timestamp = datetime.now()
        
        # Price patterns
        price_patterns = [
            r'(\d+)\s*eur[oa]?',
            r'(\d+)\s*€',
            r'do\s+(\d+)\s*eur',
            r'oko\s+(\d+)\s*eur',
            r'budž[eé]t\s+(\d+)',
            r'košta\s+(\d+)',
            r'(\d+)\s*din'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, message)
            if match:
                amount = int(match.group(1))
                
                # Determine price type based on context
                if "do" in match.group(0) or "maksimal" in message:
                    entities["price_max"] = TourismEntity(
                        entity_type="price_max",
                        entity_value=amount,
                        confidence=0.9,
                        first_mentioned=timestamp,
                        last_mentioned=timestamp
                    )
                elif "od" in match.group(0) or "minimum" in message:
                    entities["price_min"] = TourismEntity(
                        entity_type="price_min", 
                        entity_value=amount,
                        confidence=0.9,
                        first_mentioned=timestamp,
                        last_mentioned=timestamp
                    )
                else:
                    entities["price_target"] = TourismEntity(
                        entity_type="price_target",
                        entity_value=amount,
                        confidence=0.8,
                        first_mentioned=timestamp,
                        last_mentioned=timestamp
                    )
                break
        
        # Price range indicators
        if any(word in message for word in ["jeftin", "budget", "ekonom"]):
            entities["price_range"] = TourismEntity(
                entity_type="price_range",
                entity_value="budget",
                confidence=0.7,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        elif any(word in message for word in ["luksuz", "skup", "premium"]):
            entities["price_range"] = TourismEntity(
                entity_type="price_range",
                entity_value="luxury",
                confidence=0.7,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        
        return entities
    
    def _extract_dates(self, message: str) -> Dict[str, TourismEntity]:
        """Extract travel date information"""
        entities = {}
        timestamp = datetime.now()
        
        # Month detection
        for month in self.tourism_entities["travel_dates"]["months"]:
            if month in message:
                entities["travel_month"] = TourismEntity(
                    entity_type="travel_month",
                    entity_value=month,
                    confidence=0.8,
                    first_mentioned=timestamp,
                    last_mentioned=timestamp
                )
                break
        
        # Season detection
        for season in self.tourism_entities["travel_dates"]["seasons"]:
            if season in message:
                entities["travel_season"] = TourismEntity(
                    entity_type="travel_season",
                    entity_value=season,
                    confidence=0.8,
                    first_mentioned=timestamp,
                    last_mentioned=timestamp
                )
                break
        
        # Duration extraction
        duration_patterns = [
            r'(\d+)\s*dan[a]?',
            r'(\d+)\s*noć[i]?',
            r'(\d+)\s*noc[i]?'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, message)
            if match:
                duration = int(match.group(1))
                if "dan" in match.group(0):
                    entities["duration_days"] = TourismEntity(
                        entity_type="duration_days",
                        entity_value=duration,
                        confidence=0.9,
                        first_mentioned=timestamp,
                        last_mentioned=timestamp
                    )
                elif "noć" in match.group(0):
                    entities["duration_nights"] = TourismEntity(
                        entity_type="duration_nights",
                        entity_value=duration,
                        confidence=0.9,
                        first_mentioned=timestamp,
                        last_mentioned=timestamp
                    )
                break
        
        return entities
    
    def _extract_group_composition(self, message: str) -> Dict[str, TourismEntity]:
        """Extract group composition information"""
        entities = {}
        timestamp = datetime.now()
        
        # Number of people
        people_patterns = [
            r'(\d+)\s*osob[ae]',
            r'za\s+(\d+)',
            r'(\d+)\s*ljudi',
            r'(\d+)\s*član'
        ]
        
        for pattern in people_patterns:
            match = re.search(pattern, message)
            if match:
                count = int(match.group(1))
                entities["group_size"] = TourismEntity(
                    entity_type="group_size",
                    entity_value=count,
                    confidence=0.9,
                    first_mentioned=timestamp,
                    last_mentioned=timestamp
                )
                break
        
        # Family indicators
        if any(word in message for word in ["porodica", "deca", "dete", "familij"]):
            entities["family_friendly"] = TourismEntity(
                entity_type="family_friendly",
                entity_value=True,
                confidence=0.8,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        
        return entities
    
    def _extract_accommodation(self, message: str) -> Dict[str, TourismEntity]:
        """Extract accommodation preferences"""
        entities = {}
        timestamp = datetime.now()
        
        # Hotel category
        if "hotel" in message:
            entities["category"] = TourismEntity(
                entity_type="category",
                entity_value="hotel",
                confidence=0.9,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        elif "apartman" in message:
            entities["category"] = TourismEntity(
                entity_type="category",
                entity_value="apartment",
                confidence=0.9,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        elif "smeštaj" in message or "smestaj" in message:
            entities["category"] = TourismEntity(
                entity_type="category",
                entity_value="accommodation",
                confidence=0.8,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        
        # Amenities
        amenities = []
        for amenity in self.tourism_entities["preferences"]["amenities"]:
            if amenity.lower() in message:
                amenities.append(amenity)
        
        if amenities:
            entities["amenities"] = TourismEntity(
                entity_type="amenities",
                entity_value=amenities,
                confidence=0.7,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        
        return entities
    
    def _extract_transport(self, message: str) -> Dict[str, TourismEntity]:
        """Extract transport preferences"""
        entities = {}
        timestamp = datetime.now()
        
        if any(word in message for word in ["avion", "avio", "let"]):
            entities["transport_type"] = TourismEntity(
                entity_type="transport_type",
                entity_value="plane",
                confidence=0.9,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        elif any(word in message for word in ["autobus", "bus"]):
            entities["transport_type"] = TourismEntity(
                entity_type="transport_type",
                entity_value="bus",
                confidence=0.9,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        elif any(word in message for word in ["voz", "železnic"]):
            entities["transport_type"] = TourismEntity(
                entity_type="transport_type",
                entity_value="train",
                confidence=0.9,
                first_mentioned=timestamp,
                last_mentioned=timestamp
            )
        
        return entities
    
    def _create_llm_extraction_prompt(self, context_text: str) -> str:
        """Create prompt for LLM entity extraction"""
        return f"""
Analiziraj sledeći turistički upit na srpskom jeziku i izvuci strukturirane informacije.

{context_text}

Izvuci sledeće informacije (ako postoje):
1. DESTINACIJA: grad, zemlja ili region
2. BUDŽET: cena, troškovi (sa valutom)
3. DATUMI: mesec, sezona, period
4. GRUPA: broj osoba, tip grupe (porodica, prijatelji)
5. SMEŠTAJ: tip hotela, kategorija, amenities
6. TRANSPORT: avion, autobus, voz
7. AKTIVNOSTI: šta želi da radi

Odgovori u JSON formatu:
{{
  "destination": "naziv_mesta",
  "price_max": broj_ili_null,
  "travel_month": "mesec_ili_null",
  "group_size": broj_ili_null,
  "family_friendly": true_ili_false_ili_null,
  "category": "hotel/apartment/tour",
  "transport_type": "plane/bus/train/null",
  "amenities": ["spa", "pool", ...]
}}

Ako informacija ne postoji, stavi null. Budi precizan i koristi standardne nazive.
"""
    
    async def _parse_llm_entity_response(self, llm_response: str) -> Dict[str, TourismEntity]:
        """Parse LLM JSON response into TourismEntity objects"""
        entities = {}
        timestamp = datetime.now()
        
        try:
            # Clean and parse JSON
            json_text = llm_response.strip()
            if json_text.startswith("```json"):
                json_text = json_text.replace("```json", "").replace("```", "").strip()
            
            parsed_data = json.loads(json_text)
            
            # Convert to TourismEntity objects
            for entity_type, entity_value in parsed_data.items():
                if entity_value is not None and entity_value != "":
                    entities[entity_type] = TourismEntity(
                        entity_type=entity_type,
                        entity_value=entity_value,
                        confidence=0.8,  # LLM extraction confidence
                        first_mentioned=timestamp,
                        last_mentioned=timestamp,
                        frequency=1
                    )
            
            return entities
            
        except Exception as e:
            logger.error(f"❌ Failed to parse LLM entity response: {e}")
            return {}
    
    async def _merge_entity_results(self, rule_based: Dict[str, TourismEntity], 
                                   llm_based: Dict[str, TourismEntity]) -> Dict[str, TourismEntity]:
        """Intelligently merge rule-based and LLM-based entity extraction results"""
        merged = {}
        
        # Start with rule-based entities (higher precision)
        for entity_type, entity in rule_based.items():
            merged[entity_type] = entity
        
        # Add LLM entities that don't conflict or have higher confidence
        for entity_type, llm_entity in llm_based.items():
            if entity_type not in merged:
                # Add new entity from LLM
                merged[entity_type] = llm_entity
            else:
                # Choose entity with higher confidence
                existing_entity = merged[entity_type]
                if llm_entity.confidence > existing_entity.confidence:
                    merged[entity_type] = llm_entity
        
        return merged
    
    def _calculate_extraction_confidence(self, rule_based: Dict, llm_based: Dict, merged: Dict) -> float:
        """Calculate overall extraction confidence"""
        if not merged:
            return 0.1
        
        total_confidence = 0.0
        entity_count = len(merged)
        
        for entity in merged.values():
            total_confidence += entity.confidence
        
        average_confidence = total_confidence / entity_count
        
        # Boost confidence if both methods agree
        agreement_bonus = 0.0
        for entity_type in rule_based:
            if entity_type in llm_based:
                agreement_bonus += 0.1
        
        return min(1.0, average_confidence + agreement_bonus) 