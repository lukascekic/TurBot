import asyncio
import json
import logging
from typing import Dict, List, Optional
from openai import AsyncOpenAI
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)

class QueryExpansionService:
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self.cache: Dict[str, str] = {}
        
    async def expand_query_llm(self, query: str) -> str:
        """
        LLM-powered semantic expansion optimized for Serbian tourism queries
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(query)
            if cache_key in self.cache:
                logger.info(f"Cache hit for query: {query}")
                return self.cache[cache_key]
            
            # Generate expansion using LLM
            expanded = await self._generate_expansion(query)
            
            # Cache the result
            self.cache[cache_key] = expanded
            
            logger.info(f"Expanded query: '{query}' -> '{expanded}'")
            return expanded
            
        except Exception as e:
            logger.error(f"Error expanding query '{query}': {e}")
            # Fallback to basic expansion
            return await self._fallback_expansion(query)
    
    async def _generate_expansion(self, query: str) -> str:
        """
        Generate semantic expansion using LLM
        """
        prompt = f"""
Ti si ekspert za srpski jezik i turizam. Tvoj zadatak je da proširiš turistički upit sa sinonimima i srodnim terminima.

Originalni upit: "{query}"

Generiši proširenu pretragu koja uključuje:
1. Sinonime na srpskom (hotel → smeštaj, apartman, vila, pansion, boutique)
2. Regionalne termine (Rim → Roma, Rome, Italija, Italy)
3. Semantičke varijante RELEVANTNE za originalni upit:
   - romantičan → za parove, medeni mesec, spa, luksuzno, intimno
   - porodičan → family, deca, animacija, playground, kids
   - luksuzno → premium, spa, wellness, vrhunski
4. Morfološke oblike (najbolji → top, odličan, prvoklasan, vrhunski)
5. Tourism specifične termine (letovanje → odmor, more, plaža, beach, vacation)

Pravila:
- Koristi OR operator između termina
- Zadrži logičku strukturu originalnog upita (grupisi related termine)
- Maksimalno 12-15 termina (fokus na relevantnost)
- VAŽNO: Semantičke varijante moraju biti RELEVANTNE za originalni upit
- NE dodavaj "romantičan" termine ako je upit "porodičan"
- NE dodavaj "porodičan" termine ako je upit "romantičan"
- Fokus na specifične tourism termine povezane sa originalnim zahtevom

Format odgovora: samo prošireni query bez objašnjenja.

Primer:
Input: "hotel u Rimu"
Output: "hotel OR smeštaj OR apartman OR vila OR pansion u Rimu OR Roma OR Rome OR Italija OR Italy OR centar"

Tvoj odgovor:
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si ekspert za srpski jezik i turizam. Odgovaraj kratko i precizno."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            expanded_query = response.choices[0].message.content.strip()
            
            # Validate expansion
            if self._is_valid_expansion(expanded_query, query):
                return expanded_query
            else:
                logger.warning(f"Invalid LLM expansion for '{query}': {expanded_query}")
                return await self._fallback_expansion(query)
                
        except Exception as e:
            logger.error(f"LLM expansion failed for '{query}': {e}")
            return await self._fallback_expansion(query)
    
    async def _fallback_expansion(self, query: str) -> str:
        """
        Fallback to basic synonym expansion if LLM fails
        """
        # Basic Serbian tourism synonyms
        synonyms = {
            "hotel": ["smeštaj", "apartman", "vila", "pansion", "boutique"],
            "restoran": ["kafana", "gostionica", "lokantić", "restaurant"],
            "plaža": ["more", "beach", "kupanje", "sunčanje"],
            "tura": ["izlet", "putovanje", "aranžman", "tour"],
            "centar": ["city center", "centro", "središte"],
            "letovanje": ["odmor", "vacation", "holiday", "more"],
            "romantičan": ["za parove", "intimno", "romantic"],
            "luksuzno": ["lux", "luxury", "premium", "vrhunsko"],
            "porodična": ["family", "sa decom", "kids friendly"],
            
            # Geographic variants
            "rim": ["roma", "rome", "italija", "italy"],
            "beograd": ["belgrade", "srbija", "serbia"],
            "istanbul": ["turkey", "turska", "constantinople"],
            "amsterdam": ["netherlands", "holandija", "holland"],
            "pariz": ["paris", "francuska", "france"]
        }
        
        expanded_terms = []
        original_words = query.lower().split()
        
        for word in original_words:
            expanded_terms.append(word)
            # Add synonyms if found
            for key, syn_list in synonyms.items():
                if key in word:
                    expanded_terms.extend(syn_list[:3])  # Limit to 3 synonyms
        
        # Remove duplicates and join
        unique_terms = list(dict.fromkeys(expanded_terms))
        return " OR ".join(unique_terms)
    
    def _is_valid_expansion(self, expanded: str, original: str) -> bool:
        """
        Validate that expansion is reasonable
        """
        if not expanded or len(expanded) < len(original):
            return False
        
        # Check for OR operators
        if " OR " not in expanded:
            return False
        
        # Count number of OR terms
        terms_count = len(expanded.split(" OR "))
        if terms_count > 15:  # Too many terms
            logger.warning(f"Too many expansion terms ({terms_count}) for '{original}'")
            return False
            
        # Check expansion ratio (not too long)
        expansion_ratio = len(expanded) / len(original)
        if expansion_ratio > 12:  # Reasonable expansion limit (relaxed for better UX)
            logger.warning(f"Expansion too long (ratio: {expansion_ratio:.1f}) for '{original}'")
            return False
            
        return True
    
    def _get_cache_key(self, query: str) -> str:
        """
        Generate cache key for query
        """
        return hashlib.md5(query.lower().encode()).hexdigest()
    
    @lru_cache(maxsize=100)
    def get_tourism_keywords(self) -> List[str]:
        """
        Get comprehensive list of tourism-related keywords
        """
        return [
            # Accommodation
            "hotel", "smeštaj", "apartman", "vila", "pansion", "boutique", "resort",
            "hostel", "garni", "motel", "pension", "guesthouse",
            
            # Food & Dining  
            "restoran", "kafana", "gostionica", "lokantić", "restaurant", "bar",
            "pizzeria", "fast food", "fine dining", "buffet",
            
            # Activities
            "tura", "izlet", "putovanje", "aranžman", "tour", "excursion",
            "sightseeing", "obilazak", "poseta", "visit",
            
            # Locations
            "centar", "city center", "centro", "središte", "downtown",
            "plaža", "more", "beach", "obala", "coast",
            
            # Amenities
            "bazen", "pool", "spa", "wellness", "fitness", "parking",
            "wifi", "klima", "balkon", "terasa", "pogled",
            
            # Price ranges
            "jeftino", "budget", "economical", "luksuzno", "luxury", "premium",
            "povoljno", "affordable", "skupo", "expensive"
        ]

# Singleton instance
_query_expansion_service = None

def get_query_expansion_service(openai_client: AsyncOpenAI) -> QueryExpansionService:
    """
    Get singleton instance of QueryExpansionService
    """
    global _query_expansion_service
    if _query_expansion_service is None:
        _query_expansion_service = QueryExpansionService(openai_client)
    return _query_expansion_service 