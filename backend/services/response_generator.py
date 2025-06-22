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
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> ResponseData:
        """Generate response using RAG results with conversation context"""
        try:
            print(f"\n🤖 RESPONSE GENERATOR:")
            print(f"   Number of search results: {len(search_results)}")
            print(f"   Structured query: {structured_query.semantic_query if hasattr(structured_query, 'semantic_query') else 'N/A'}")
            print(f"   Query intent: {structured_query.intent if hasattr(structured_query, 'intent') else 'N/A'}")
            
            # Check if conversation context is provided
            if conversation_context:
                print(f"   🧠 CONVERSATION CONTEXT RECEIVED:")
                print(f"      Session ID: {conversation_context.get('session_id', 'N/A')}")
                print(f"      Total messages: {conversation_context.get('total_messages', 0)}")
                print(f"      Recent conversation: {len(conversation_context.get('recent_conversation', []))} messages")
                print(f"      Active entities: {conversation_context.get('active_entities', {})}")
                print(f"      Historical preferences: {len(conversation_context.get('historical_preferences', {}))} entities")
                
                # Log recent conversation details
                recent_conv = conversation_context.get('recent_conversation', [])
                if recent_conv:
                    print(f"   Recent conversation to be included in prompt:")
                    for i, msg in enumerate(recent_conv):
                        print(f"      {i+1}. {msg['role']}: {msg['content'][:60]}...")
                else:
                    print(f"   ⚠️  No recent conversation in context!")
            else:
                print(f"   ⚠️  NO CONVERSATION CONTEXT PROVIDED!")
            
            # Check if we need detailed content for this query
            needs_detailed = self._needs_detailed_content(structured_query.semantic_query)
            print(f"   Needs detailed content: {needs_detailed}")
            
            if needs_detailed:
                print(f"   🔍 GENERATING DETAILED RESPONSE...")
                return await self._generate_detailed_response(search_results, structured_query, conversation_context)
            
            # Standard response generation
            print(f"   📝 GENERATING STANDARD RESPONSE...")
            
            if not search_results:
                return self._generate_no_results_response(structured_query, conversation_context)
            
            # Prepare context for LLM prompt
            context_text = ""
            sources = []
            
            for i, result in enumerate(search_results[:5]):  # Use top 5 results
                content = result.get('content', '')[:400]  # Limit content length for standard response
                metadata = result.get('metadata', {})
                source_file = result.get('document_name', metadata.get('source_file', f'Document {i+1}'))
                similarity = result.get('similarity', 0)
                
                context_text += f"\n--- Document {i+1}: {source_file} (Relevance: {similarity:.2f}) ---\n{content}\n"
                
                sources.append({
                    "document_name": source_file,
                    "relevance": f"{similarity:.0%}",
                    "snippet": content[:150] + "..." if len(content) > 150 else content
                })
            
            print(f"   Context prepared: {len(context_text)} characters from {len(sources)} sources")
            
            # Build conversation-aware prompt
            conversation_prompt = ""
            if conversation_context and conversation_context.get('recent_conversation'):
                print(f"   🧠 BUILDING CONVERSATION-AWARE PROMPT...")
                conversation_prompt = "\n--- RECENT CONVERSATION HISTORY ---\n"
                for msg in conversation_context['recent_conversation']:
                    role = "Korisnik" if msg['role'] == 'user' else "TurBot"
                    conversation_prompt += f"{role}: {msg['content']}\n"
                conversation_prompt += "--- END CONVERSATION HISTORY ---\n\n"
                
                # Add active entities context
                if conversation_context.get('active_entities'):
                    conversation_prompt += "--- ACTIVE CONTEXT ---\n"
                    for entity_type, value in conversation_context['active_entities'].items():
                        conversation_prompt += f"{entity_type}: {value}\n"
                    conversation_prompt += "--- END ACTIVE CONTEXT ---\n\n"
                
                print(f"   Conversation prompt built: {len(conversation_prompt)} characters")
            else:
                print(f"   No conversation context to include in prompt")
            
            # Create comprehensive system prompt with conversation awareness
            system_prompt = f"""Ti si TurBot, napredni AI asistent za turističke agencije u Srbiji. Tvoja uloga je da pomazeš korisnicima sa informacijama o putovanjima i turističkim aranžmanima.

KONTEKST RAZGOVORA:
{conversation_prompt if conversation_prompt else "Ovo je početak razgovora."}

DOSTUPNI TURISTIČKI SADRŽAJ:
{context_text}

INSTRUKCIJE:
1. **Kontekst razgovora**: {"Koristi gornji kontekst razgovora da razumeš kontinuitet komunikacije." if conversation_prompt else "Ovo je početak novog razgovora."}
2. **Personalizovane preporuke**: Odgovori na srpskom jeziku sa konkretnim preporukama na osnovu dostupnih aranžmana
3. **Source attribution**: Uvek navedi izvore informacija (nazive PDF dokumenata)
4. **Praktične informacije**: Uključi cene, datume, destinacije i specifičnosti aranžmana
5. **Profesionalan ton**: Koristi prijateljski ali profesionalan ton turističkog agenta
6. **Format odgovora**: Struktuiran, jasan i informativan odgovor

TRENUTNI UPIT: {structured_query.semantic_query}

Generiši sveobuhvatan odgovor koji pomaže korisniku da donese informisanu odluku o putovanju."""

            print(f"   System prompt prepared: {len(system_prompt)} characters")
            
            # Calculate estimated token usage
            estimated_input_tokens = len(system_prompt) // 4  # Rough estimate: 4 chars = 1 token
            print(f"   💰 Estimated input tokens: ~{estimated_input_tokens}")
            print(f"   💰 Estimated cost: ~${estimated_input_tokens * 0.000150:.6f}")
            print(f"   Sending to OpenAI GPT-4o-mini...")
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": structured_query.semantic_query}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            # Log actual token usage if available
            if hasattr(response, 'usage') and response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                total_cost = (input_tokens * 0.000150) + (output_tokens * 0.000600)  # GPT-4o-mini pricing
                
                print(f"   ✅ OpenAI response received: {len(generated_response)} characters")
                print(f"   💰 ACTUAL TOKEN USAGE:")
                print(f"      Input tokens: {input_tokens}")
                print(f"      Output tokens: {output_tokens}")
                print(f"      Total tokens: {total_tokens}")
                print(f"      Total cost: ${total_cost:.6f}")
            else:
                print(f"   ✅ OpenAI response received: {len(generated_response)} characters")
                print(f"   ⚠️  Token usage info not available")
            
            # Generate suggested questions based on context and search results
            suggested_questions = self._generate_suggested_questions(search_results, structured_query, conversation_context)
            
            # Calculate confidence based on search results and conversation context
            confidence = self._calculate_confidence(search_results, conversation_context)
            
            print(f"   Generated {len(suggested_questions)} suggested questions")
            print(f"   Calculated confidence: {confidence:.2f}")
            
            return ResponseData(
                response=generated_response,
                sources=sources,
                structured_data={
                    "intent": structured_query.intent if hasattr(structured_query, 'intent') else None,
                    "filters_used": structured_query.filters if hasattr(structured_query, 'filters') else {},
                    "results_count": len(search_results),
                    "conversation_aware": bool(conversation_context and conversation_context.get('recent_conversation'))
                },
                suggested_questions=suggested_questions,
                confidence=confidence
            )
            
        except Exception as e:
            print(f"   ❌ ERROR in response generation: {e}")
            logger.error(f"❌ Response generation failed: {e}")
            return ResponseData(
                response="Izvinjavam se, došlo je do greške pri generisanju odgovora. Molim pokušajte ponovo.",
                sources=[],
                structured_data={},
                suggested_questions=["Možete li ponoviti pitanje?"],
                confidence=0.1
            )

    def _needs_detailed_content(self, query: str) -> bool:
        """Check if query requires detailed document content"""
        detail_keywords = [
            'datumi', 'datum', 'kada', 'koji dani', 'polazak', 'povratak',
            'program', 'itinerar', 'šta je uključeno', 'detaljno',
            'više informacija', 'specifično', 'dodatno', 'extra',
            'cene', 'cenovnik', 'košta', 'price', 'koliko'
        ]
        
        return any(keyword in query.lower() for keyword in detail_keywords)

    def _generate_no_results_response(self, structured_query, conversation_context: Optional[Dict[str, Any]] = None) -> ResponseData:
        """Generate response when no search results are found"""
        # Build context-aware message
        context_info = ""
        if conversation_context and conversation_context.get('active_entities'):
            active_entities = conversation_context['active_entities']
            if 'destination' in active_entities:
                context_info = f" za {active_entities['destination']}"
        
        response = f"Izvinjavam se, trenutno nemamo dostupne aranžmane{context_info} koji odgovaraju vašem upitu. Možete li precizirati vašu pretragu ili probati sa drugačijim kriterijumima?"
        
        # Generate alternative suggestions
        suggested_questions = [
            "Možete li proširiti kriterijume pretrage?",
            "Da li vas zanima druga destinacija?",
            "Možete li promeniti datume putovanja?",
            "Da li imate fleksibilan budžet?"
        ]
        
        return ResponseData(
            response=response,
            sources=[],
            structured_data={"no_results": True, "query": structured_query.semantic_query},
            suggested_questions=suggested_questions,
            confidence=0.3
        )

    async def _generate_detailed_response(
        self, 
        detailed_docs: List[Dict[str, Any]], 
        structured_query: StructuredQuery,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> ResponseData:
        """
        Generate response using detailed document content
        """
        try:
            # Prepare comprehensive content for AI
            detailed_content_summary = self._prepare_detailed_content_summary(detailed_docs)
            
            # Add conversation context if available
            conversation_info = ""
            if conversation_context:
                recent_messages = conversation_context.get("recent_conversation", [])
                active_entities = conversation_context.get("active_entities", {})
                
                if recent_messages:
                    conversation_info += "\nPREDHODNA KONVERZACIJA:\n"
                    for msg in recent_messages[-2:]:
                        role = "Korisnik" if msg["role"] == "user" else "TurBot"
                        conversation_info += f"{role}: {msg['content']}\n"
                
                if active_entities:
                    conversation_info += f"\nAKTIVNE PREFERENCIJE: {active_entities}\n"

            prompt = f"""
Ti si TurBot, profesionalni turistički agent. Imaš pristup detaljnim informacijama o aranžmanima.

KORISNIKOV UPIT: "{structured_query.semantic_query}"
{conversation_info}

DETALJNE INFORMACIJE O ARANŽMANIMA:
{detailed_content_summary}

VAŽNO: Sada imaš kompletne informacije - koristi ih za precizne odgovore!

ZADATAK:
- Odgovori DETALJNO sa konkretnim informacijama (datumi, cene, program)
- Koristi sve dostupne podatke iz dokumenata
- Budi SPECIFIČAN sa datumima, cenama, uslugama
- Strukturiraj odgovor jasno (bullets, sekcije)

STRUKTURA ODGOVORA:

1. **DIREKTAN ODGOVOR**: Konkretne informacije na pitanje

2. **DETALJNI PODACI**:
   - Datumi polaska: [konkretni datumi]
   - Cene: [specifične cene sa valutom]
   - Program: [ključne aktivnosti]
   - Uključeno: [šta je u ceni]

3. **DODATNE INFORMACIJE**: Relevantni detalji

4. **SLEDEĆI KORACI**: Konkretne preporuke

STIL: Profesionalan, informativan, sa svim potrebnim detaljima

ODGOVOR:
"""

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ti si ekspert turistički agent sa pristupom detaljnim informacijama."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )

            ai_response = response.choices[0].message.content.strip()

            # Prepare sources from detailed documents
            sources = []
            for doc in detailed_docs:
                sources.append({
                    "document_name": doc["document_name"],
                    "similarity": 1.0,  # High relevance since we specifically fetched this
                    "content_preview": doc["full_content"][:300] + "...",
                    "metadata": doc["metadata"],
                    "detailed_content_available": True
                })

            # Generate enhanced suggested questions based on detailed content
            suggested_questions = self._generate_detailed_suggested_questions(detailed_docs, structured_query)

            # Extract structured data from detailed content
            structured_data = self._extract_detailed_structured_data(detailed_docs)

            return ResponseData(
                response=ai_response,
                sources=sources,
                structured_data=structured_data,
                suggested_questions=suggested_questions,
                confidence=0.9  # High confidence with detailed content
            )

        except Exception as e:
            logger.error(f"Error generating detailed response: {e}")
            # Fallback to standard response
            return ResponseData(
                response="Izvinjavam se, došlo je do greške pri pristupu detaljnim informacijama.",
                sources=[],
                structured_data={},
                suggested_questions=["Molim pokušajte ponovo sa konkretnim pitanjem"],
                confidence=0.1
            )

    def _prepare_detailed_content_summary(self, detailed_docs: List[Dict[str, Any]]) -> str:
        """Prepare comprehensive summary from detailed documents"""
        summary_parts = []
        
        for i, doc in enumerate(detailed_docs, 1):
            doc_name = doc["document_name"]
            full_content = doc["full_content"]
            structured = doc.get("structured_content", {})
            
            summary_parts.append(f"DOKUMENT {i}: {doc_name}")
            summary_parts.append("=" * 50)
            
            # Add full content (not limited to 400 chars like before)
            summary_parts.append("KOMPLETNI SADRŽAJ:")
            summary_parts.append(full_content)
            
            # Add structured information if available
            if structured:
                if structured.get("prices"):
                    summary_parts.append(f"CENE: {', '.join(structured['prices'])}")
                if structured.get("dates"):
                    summary_parts.append(f"DATUMI: {', '.join(structured['dates'])}")
                if structured.get("amenities"):
                    summary_parts.append(f"SADRŽAJI: {', '.join(structured['amenities'])}")
            
            summary_parts.append("\n" + "-" * 50 + "\n")
        
        return "\n".join(summary_parts)

    def _generate_detailed_suggested_questions(
        self, 
        detailed_docs: List[Dict[str, Any]], 
        structured_query: StructuredQuery
    ) -> List[str]:
        """Generate specific follow-up questions based on detailed content"""
        suggestions = []
        
        # Analyze detailed content to generate specific questions
        for doc in detailed_docs:
            structured = doc.get("structured_content", {})
            
            # Date-based questions
            if structured.get("dates"):
                suggestions.append("Koji su tačni datumi polaska i povratka?")
                suggestions.append("Da li postoje alternativni termini?")
            
            # Price-based questions
            if structured.get("prices"):
                suggestions.append("Šta je tačno uključeno u cenu?")
                suggestions.append("Da li postoje dodatni troškovi?")
            
            # Program-based questions
            if "program" in structured.get("sections", {}):
                suggestions.append("Možete li mi objasniti detaljan program po danima?")
                suggestions.append("Koliko slobodnog vremena imamo?")
            
            # Transport-based questions
            if "transport" in structured.get("sections", {}):
                suggestions.append("Kakav je prevoz i odakle se kreće?")
                suggestions.append("Da li je potrebna rezervacija?")
        
        # Remove duplicates and limit to 4
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:4]

    def _extract_detailed_structured_data(self, detailed_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract comprehensive structured data from detailed documents"""
        structured_data = {
            "total_documents": len(detailed_docs),
            "detailed_content_used": True,
            "comprehensive_info": {},
            "all_prices": [],
            "all_dates": [],
            "all_amenities": [],
            "document_summaries": []
        }
        
        for doc in detailed_docs:
            doc_name = doc["document_name"]
            structured = doc.get("structured_content", {})
            
            doc_summary = {
                "name": doc_name,
                "content_length": doc.get("content_length", 0),
                "sections": list(structured.get("sections", {}).keys())
            }
            
            # Aggregate data
            if structured.get("prices"):
                structured_data["all_prices"].extend(structured["prices"])
            if structured.get("dates"):
                structured_data["all_dates"].extend(structured["dates"])
            if structured.get("amenities"):
                structured_data["all_amenities"].extend(structured["amenities"])
            
            structured_data["document_summaries"].append(doc_summary)
        
        return structured_data

    async def _generate_natural_response(
        self, 
        search_results: List[Dict[str, Any]], 
        structured_query: StructuredQuery,
        structured_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate natural Serbian response using LLM
        """
        # Prepare context for LLM
        results_summary = self._prepare_results_summary(search_results)
        filters_summary = self._prepare_filters_summary(structured_query.filters)
        
        # Add conversation context if available
        conversation_info = ""
        if conversation_context:
            recent_messages = conversation_context.get("recent_conversation", [])
            active_entities = conversation_context.get("active_entities", {})
            
            if recent_messages:
                conversation_info += "\nPREDHODNA KONVERZACIJA:\n"
                for msg in recent_messages[-2:]:  # Last 2 messages for context
                    role = "Korisnik" if msg["role"] == "user" else "TurBot"
                    conversation_info += f"{role}: {msg['content']}\n"
            
            if active_entities:
                conversation_info += f"\nAKTIVNE PREFERENCIJE: {active_entities}\n"
        
        prompt = f"""
Ti si TurBot, profesionalni turistički agent. Odgovaraj ljubazno i korisno na srpskom jeziku.

KORISNIKOV UPIT: "{structured_query.semantic_query}"
TRAŽI: {filters_summary}
{conversation_info}
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

VAZNO: Ne pisi eksplicitno delove izmedju ** (npr ** POZDRAV **)

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
        search_results: List[Dict[str, Any]], 
        structured_query: StructuredQuery,
        conversation_context: Optional[Dict[str, Any]] = None
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
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate response confidence based on various factors
        """
        if not search_results:
            return 0.1
        
        # Base confidence from query parsing
        confidence = 0.4
        
        # Add confidence from search results quality
        if search_results:
            avg_similarity = sum(r.get('similarity', 0) for r in search_results) / len(search_results)
            confidence += avg_similarity * 0.4
        
        # Add confidence from number of results
        result_count_factor = min(len(search_results) / 3, 1.0) * 0.2
        confidence += result_count_factor
        
        # Add conversation context confidence
        if conversation_context:
            recent_messages = conversation_context.get('recent_conversation', [])
            active_entities = conversation_context.get('active_entities', {})
            
            if recent_messages:
                confidence += 0.1  # Small boost for recent conversation
            
            if active_entities:
                confidence += 0.1  # Small boost for active entities
        
        return min(1.0, confidence)

# Singleton pattern for service
_response_generator = None

def get_response_generator(client: AsyncOpenAI) -> ResponseGenerator:
    """Get or create singleton ResponseGenerator instance"""
    global _response_generator
    if _response_generator is None:
        _response_generator = ResponseGenerator(client)
    return _response_generator 