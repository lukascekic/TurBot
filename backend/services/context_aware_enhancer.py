import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from openai import AsyncOpenAI

from models.conversation import ContextEnhancementResult, ConversationContext, MessageRole
from services.conversation_memory_service import ConversationMemoryService
from services.named_entity_extractor import NamedEntityExtractor

logger = logging.getLogger(__name__)

class ContextAwareEnhancer:
    """
    Context-aware query enhancement using hybrid conversation memory
    - Resolves pronouns and references 
    - Adds implicit filters from conversation history
    - Detects context switches
    - Enhances queries with historical preferences
    """
    
    def __init__(self, memory_service: ConversationMemoryService, entity_extractor: NamedEntityExtractor, openai_client: AsyncOpenAI):
        self.memory_service = memory_service
        self.entity_extractor = entity_extractor
        self.client = openai_client
        
        # Context enhancement patterns
        self.pronoun_patterns = [
            r'\b(to|taj|ta|ono|on|ona|oni|one)\b',
            r'\b(koliko|kako|zašto|gde)\b',
            r'\b(tu|tamo|ovde)\b'
        ]
        
        self.reference_patterns = [
            r'\b(hotel|mesto|destinacij[ua]|aranžman)\b',
            r'\b(cena|trošak|košta)\b',
            r'\b(ranije|prošli put|spomenuo)\b'
        ]
        
        logger.info("✅ ContextAwareEnhancer initialized")
    
    async def enhance_query_with_context(self, query: str, session_id: str) -> ContextEnhancementResult:
        """
        Main method to enhance user query with conversation context
        
        Args:
            query: Original user query
            session_id: Session identifier for context retrieval
            
        Returns:
            ContextEnhancementResult with enhanced query and metadata
        """
        try:
            start_time = datetime.now()
            
            # Get hybrid conversation context
            context_data = await self.memory_service.build_hybrid_context_for_query(session_id)
            
            # Analyze query for context needs
            context_needs = await self._analyze_query_context_needs(query)
            
            # Enhance query based on context
            if context_needs["needs_context"]:
                enhanced_query = await self._enhance_with_llm_context(query, context_data)
            else:
                # Simple enhancement with active entities
                enhanced_query = await self._enhance_with_active_entities(query, context_data["active_entities"])
            
            # Extract implicit filters from context
            implicit_filters = await self._extract_implicit_filters(query, context_data)
            
            # Detect context switch
            context_switch = await self._detect_context_switch(query, context_data)
            if context_switch:
                # Reset some contextual filters for new topic
                implicit_filters = await self._handle_context_switch(implicit_filters, query)
            
            # Calculate enhancement confidence
            confidence = self._calculate_enhancement_confidence(query, enhanced_query, context_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ContextEnhancementResult(
                original_query=query,
                enhanced_query=enhanced_query,
                implicit_filters=implicit_filters,
                context_used=context_data,
                confidence=confidence,
                enhancement_method="hybrid_context"
            )
            
        except Exception as e:
            logger.error(f"❌ Context enhancement failed: {e}")
            # Return minimal enhancement
            return ContextEnhancementResult(
                original_query=query,
                enhanced_query=query,
                implicit_filters={},
                context_used={},
                confidence=0.1,
                enhancement_method="fallback"
            )
    
    async def _analyze_query_context_needs(self, query: str) -> Dict[str, Any]:
        """Analyze if query needs context enhancement"""
        query_lower = query.lower()
        
        needs_context = False
        context_indicators = []
        
        # Check for pronouns and references
        for pattern in self.pronoun_patterns:
            if re.search(pattern, query_lower):
                needs_context = True
                context_indicators.append("pronouns")
                break
        
        # Check for incomplete references
        incomplete_queries = [
            r'^(koliko|kako|zašto|gde)\b',  # Questions without subject
            r'\b(košta|ima|postoji)\s*\?*$',  # "Koliko košta?" without subject
            r'\b(tu|tamo|isto)\b',  # Location references
            r'^(da|ne)\b'  # Yes/no responses
        ]
        
        for pattern in incomplete_queries:
            if re.search(pattern, query_lower):
                needs_context = True
                context_indicators.append("incomplete_reference")
                break
        
        # Check for follow-up question patterns
        follow_up_patterns = [
            r'\b(isto|takođe|slično)\b',
            r'\b(a što|a šta|a kako)\b',
            r'\b(prošli put|ranije|spomenuo)\b'
        ]
        
        for pattern in follow_up_patterns:
            if re.search(pattern, query_lower):
                needs_context = True
                context_indicators.append("follow_up")
                break
        
        return {
            "needs_context": needs_context,
            "indicators": context_indicators,
            "query_type": self._classify_query_type(query_lower)
        }
    
    async def _enhance_with_llm_context(self, query: str, context_data: Dict[str, Any]) -> str:
        """Use LLM to enhance query with full conversation context"""
        try:
            # Prepare context for LLM
            context_prompt = self._build_context_prompt(query, context_data)
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si ekspert za razumevanje konteksta u turističkim razgovorima. Poboljšaj korisničku poruku dodavanjem konteksta iz prethodne konverzacije."},
                    {"role": "user", "content": context_prompt}
                ],
                max_tokens=300,
                temperature=0.2
            )
            
            enhanced_query = response.choices[0].message.content.strip()
            
            # Validate enhancement
            if len(enhanced_query) > len(query) * 3:  # Too verbose
                enhanced_query = enhanced_query[:len(query) * 2]  # Truncate
            
            logger.info(f"🔄 Enhanced query: '{query}' → '{enhanced_query}'")
            return enhanced_query
            
        except Exception as e:
            logger.error(f"❌ LLM enhancement failed: {e}")
            return await self._enhance_with_active_entities(query, context_data.get("active_entities", {}))
    
    async def _enhance_with_active_entities(self, query: str, active_entities: Dict[str, Any]) -> str:
        """Simple enhancement using active entities"""
        enhanced_query = query
        
        try:
            # Add destination context for incomplete queries
            if "destination" in active_entities and not any(dest in query.lower() for dest in ["rim", "pariz", "grčka", "turska"]):
                if re.search(r'\b(koliko|košta|ima|hotel)\b', query.lower()):
                    enhanced_query = f"{query} u {active_entities['destination']}"
            
            # Add budget context for price queries
            if "price_max" in active_entities and "košta" in query.lower():
                enhanced_query = f"{enhanced_query} (budžet do {active_entities['price_max']} EUR)"
            
            # Add group size context
            if "group_size" in active_entities and "osoba" not in query.lower():
                enhanced_query = f"{enhanced_query} za {active_entities['group_size']} osoba"
            
            return enhanced_query
            
        except Exception as e:
            logger.error(f"❌ Simple enhancement failed: {e}")
            return query
    
    def _build_context_prompt(self, query: str, context_data: Dict[str, Any]) -> str:
        """Build context prompt for LLM enhancement"""
        prompt_parts = []
        
        prompt_parts.append(f"Korisnikova poruka: \"{query}\"")
        
        # Add recent conversation
        if context_data.get("recent_conversation"):
            prompt_parts.append("\nPrethodna konverzacija:")
            for msg in context_data["recent_conversation"][-3:]:
                role = "Korisnik" if msg["role"] == "user" else "AI asistent"
                prompt_parts.append(f"{role}: {msg['content']}")
        
        # Add active entities
        if context_data.get("active_entities"):
            prompt_parts.append(f"\nAktivne informacije: {context_data['active_entities']}")
        
        # Add historical preferences
        if context_data.get("historical_preferences"):
            prompt_parts.append(f"\nRanije pomenute preferencije: {context_data['historical_preferences']}")
        
        prompt_parts.append("""
Zadatak: Poboljšaj korisničku poruku dodavanjem relevantnog konteksta iz konverzacije.

Pravila:
1. Ako poruka ima nejasne reference ("to", "taj hotel", "koliko košta"), zameni ih konkretnim informacijama
2. Dodaj destinaciju ako se pita o cenama/hotelima a destinacija nije spomenuta
3. Zadrži prirodan tok srpskog jezika
4. Ne dodaj previše informacija - budi koncizan
5. Ako je poruka već kompletna, vrati je bez izmena

Poboljšana poruka:""")
        
        return "\n".join(prompt_parts)
    
    async def _extract_implicit_filters(self, query: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract implicit filters from conversation context"""
        implicit_filters = {}
        
        try:
            # From active entities (current session)
            active_entities = context_data.get("active_entities", {})
            for entity_type, entity_value in active_entities.items():
                if entity_type in ["destination", "price_max", "price_min", "travel_month", "group_size", "family_friendly"]:
                    implicit_filters[entity_type] = entity_value
            
            # From historical preferences (persistent across conversation)
            historical_prefs = context_data.get("historical_preferences", {})
            for entity_type, entity_data in historical_prefs.items():
                # Only add if high confidence and frequent mention
                if entity_data.get("confidence", 0) > 0.7 and entity_data.get("frequency", 0) >= 2:
                    if entity_type not in implicit_filters:  # Don't override active entities
                        implicit_filters[entity_type] = entity_data["value"]
            
            # Query-specific implicit filters
            query_lower = query.lower()
            
            # If asking about prices, ensure we have budget context
            if "košta" in query_lower or "cena" in query_lower:
                if "price_max" not in implicit_filters and "price_min" not in implicit_filters:
                    # Look for any price mentions in recent conversation
                    for msg in context_data.get("recent_conversation", []):
                        if any(word in msg["content"].lower() for word in ["eur", "€", "budžet", "košta"]):
                            # Extract price from message (simple pattern)
                            price_match = re.search(r'(\d+)\s*eur', msg["content"].lower())
                            if price_match:
                                implicit_filters["price_max"] = int(price_match.group(1))
                                break
            
            logger.info(f"🎯 Extracted implicit filters: {implicit_filters}")
            return implicit_filters
            
        except Exception as e:
            logger.error(f"❌ Failed to extract implicit filters: {e}")
            return {}
    
    async def _detect_context_switch(self, query: str, context_data: Dict[str, Any]) -> bool:
        """Detect if user is switching conversation context"""
        try:
            query_lower = query.lower()
            
            # Explicit context switch indicators
            switch_indicators = [
                r'\b(a što|a šta)\b',
                r'\b(drugo|drugačij)\b',
                r'\b(umesto|ne to)\b',
                r'\b(promen[ai])\b'
            ]
            
            for pattern in switch_indicators:
                if re.search(pattern, query_lower):
                    logger.info("🔄 Context switch detected: explicit indicator")
                    return True
            
            # Destination switch detection
            current_destination = context_data.get("active_entities", {}).get("destination")
            if current_destination:
                # Check if query mentions different destination
                destinations = ["rim", "pariz", "grčka", "turska", "amsterdam", "madrid", "maroko"]
                for dest in destinations:
                    if dest in query_lower and dest.lower() != current_destination.lower():
                        logger.info(f"🔄 Context switch detected: destination change {current_destination} → {dest}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Context switch detection failed: {e}")
            return False
    
    async def _handle_context_switch(self, implicit_filters: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Handle context switch by resetting some filters"""
        # Keep persistent preferences (budget, group_size) but reset destination-specific ones
        persistent_filters = {}
        
        for filter_type, filter_value in implicit_filters.items():
            if filter_type in ["price_max", "price_min", "group_size", "family_friendly", "travel_month"]:
                persistent_filters[filter_type] = filter_value
        
        # Extract new destination from query if present
        query_lower = query.lower()
        destinations = ["rim", "pariz", "grčka", "turska", "amsterdam", "madrid", "maroko"]
        for dest in destinations:
            if dest in query_lower:
                persistent_filters["destination"] = dest.title()
                break
        
        logger.info(f"🔄 Context switch handled: kept {list(persistent_filters.keys())}")
        return persistent_filters
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of user query"""
        if re.search(r'\b(koliko|cena|košta|troška)\b', query):
            return "price_inquiry"
        elif re.search(r'\b(hotel|smeštaj|apartman)\b', query):
            return "accommodation_search"
        elif re.search(r'\b(ima|postoji|dostupn)\b', query):
            return "availability_check"
        elif re.search(r'\b(preporuč|savet|najbolj)\b', query):
            return "recommendation_request"
        elif re.search(r'\b(da|ne|možda)\b', query):
            return "confirmation"
        else:
            return "general_inquiry"
    
    def _calculate_enhancement_confidence(self, original: str, enhanced: str, context_data: Dict[str, Any]) -> float:
        """Calculate confidence in the enhancement"""
        base_confidence = 0.5
        
        # Boost confidence if context was available
        if context_data.get("recent_conversation"):
            base_confidence += 0.2
        
        if context_data.get("active_entities"):
            base_confidence += 0.2
        
        # Boost if enhancement significantly improved query
        if len(enhanced) > len(original) * 1.2:
            base_confidence += 0.1
        
        # Reduce if no enhancement happened
        if enhanced == original:
            base_confidence -= 0.2
        
        return max(0.1, min(1.0, base_confidence)) 