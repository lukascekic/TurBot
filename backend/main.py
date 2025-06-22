from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import os
from dotenv import load_dotenv
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from datetime import datetime
import json
import asyncio

# Load environment variables FIRST!
load_dotenv()

from routers.documents import router as documents_router
from routers.sessions import router as sessions_router

# Import Enhanced RAG services
from services.self_querying_service import SelfQueryingService
from services.query_expansion_service import QueryExpansionService
from services.vector_service import VectorService
from services.response_generator import ResponseGenerator, get_response_generator
from models.document import SearchQuery

# Import Conversation Memory services
from services.conversation_memory_service import ConversationMemoryService
from services.named_entity_extractor import NamedEntityExtractor
from services.context_aware_enhancer import ContextAwareEnhancer
from models.conversation import MessageRole

# Configure logging
logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Conversation Memory services
conversation_memory_service = ConversationMemoryService()
named_entity_extractor = NamedEntityExtractor(client)
context_aware_enhancer = ContextAwareEnhancer(conversation_memory_service, named_entity_extractor, client)

# Initialize Enhanced RAG services with conversation context
self_querying_service = SelfQueryingService(client, context_enhancer=context_aware_enhancer)
# Add conversation memory service for context-aware parsing
self_querying_service.conversation_memory_service = conversation_memory_service
query_expansion_service = QueryExpansionService(client)
vector_service = VectorService()
response_generator = get_response_generator(client)

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=2)

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_type: Optional[str] = "client"  # "client" or "agent"

class ChatResponse(BaseModel):
    response: str
    sources: list
    suggested_questions: list
    session_id: Optional[str] = None
    confidence: float
    structured_data: Dict[str, Any]
    conversation_context: Optional[Dict[str, Any]] = None
    active_entities: Optional[Dict[str, Any]] = None

# Create FastAPI app
app = FastAPI(
    title="TurBot API",
    description="AI Agent za turističke agencije - Enhanced RAG Implementation",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
allowed_origins = eval(os.getenv("ALLOWED_ORIGINS", '["http://localhost:3000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents_router)
app.include_router(sessions_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "TurBot API"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "TurBot API - Dobrodošli u turistički AI asistent!"}

# Enhanced chat endpoint with conversation memory and full RAG pipeline
@app.post("/chat", response_model=ChatResponse)
async def enhanced_chat(chat_message: ChatMessage):
    """Enhanced chat endpoint with conversation memory and complete RAG pipeline"""
    try:
        user_message = chat_message.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        session_id = chat_message.session_id or f"session_{int(datetime.now().timestamp())}"
        
        
        logger.info(f"🎯 Processing chat message: '{user_message}' [Session: {session_id[:8]}]")
        
        async def enhanced_rag_with_memory_pipeline():
            """Complete Enhanced RAG pipeline with conversation memory"""
            try:
                
            
                await conversation_memory_service.save_message(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=user_message
                )
                
                # Step 1: Context-Aware Self-Querying - Parse with conversation context
                
                structured_query = await self_querying_service.parse_query_with_context(
                    user_message, session_id
                )
                
                
                # Extract entities from current message for context updating
                
                entity_extraction_result = await named_entity_extractor.extract_entities_from_message(user_message)
                if entity_extraction_result.entities:
                    # Convert TourismEntity objects to simple dict for active entities
                    extracted_entities = {}
                    for entity_type, entity_obj in entity_extraction_result.entities.items():
                        extracted_entities[entity_type] = entity_obj.entity_value
                    
                    
                    
                    # Update active entities in conversation memory
                    await conversation_memory_service.update_active_entities(session_id, extracted_entities)

                # Step 2: Query expansion
                expanded_query = await query_expansion_service.expand_query_llm(
                    structured_query.semantic_query
                )
                
                
                # Step 4: Enhanced Vector Search with context-aware filters
                
                search_query = SearchQuery(
                    query=expanded_query,
                    filters=structured_query.filters,
                    limit=5  # Get top 5 results for better context
                )
                
                search_results = vector_service.search(search_query)
                
                
                # Convert search results to format expected by response generator
                search_results_dict = []
                for i, result in enumerate(search_results.results):
                    search_results_dict.append({
                        'content': result.text,
                        'metadata': result.metadata.model_dump(),
                        'similarity': result.similarity_score,
                        'document_name': result.metadata.source_file or 'Unknown'
                    })
                    
                
                # Get conversation context for response generation
                conversation_context = await conversation_memory_service.build_hybrid_context_for_query(session_id)
                
                
                
                # Log conversation context details
                recent_conv = conversation_context.get('recent_conversation', [])
                if recent_conv:
                    print(f"   Recent conversation details:")
                    for i, msg in enumerate(recent_conv):
                        print(f"      {i+1}. {msg['role']}: {msg['content'][:80]}...")
                else:
                    print(f"   ⚠️  NO RECENT CONVERSATION FOUND!")
                
                response_data = await response_generator.generate_response(
                    search_results=search_results_dict,
                    structured_query=structured_query,
                    conversation_context=conversation_context  # Add conversation context
                )
                
                
                await conversation_memory_service.save_message(
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=response_data.response,
                    entities=entity_extraction_result.entities if entity_extraction_result.entities else None,
                    sources=[source.get('document_name', '') for source in response_data.sources],
                    confidence=response_data.confidence
                )
                
                return response_data, conversation_context
                
            except Exception as e:
                print(f"❌ ENHANCED RAG PIPELINE FAILED: {e}")
                logger.error(f"❌ Enhanced RAG with Memory pipeline failed: {e}")
                # Return fallback response
                from services.response_generator import ResponseData
                return ResponseData(
                    response=f"Izvinjavam se, došlo je do greške pri obradi vašeg upita. Molim pokušajte ponovo ili reformulišite pitanje.",
                    sources=[],
                    structured_data={},
                    suggested_questions=[
                        "Možete li precizirati vašu pretragu?",
                        "Da li tražite specifičnu destinaciju?", 
                        "Kakav je vaš budžet za putovanje?"
                    ],
                    confidence=0.1
                ), {}
        
        # Execute Enhanced RAG pipeline with memory
        response_data, conversation_context = await enhanced_rag_with_memory_pipeline()
        
        # Get current active entities for frontend display
        print("\n📊 GATHERING SESSION STATISTICS...")
        session_stats = await conversation_memory_service.get_session_stats(session_id)
        current_context = await conversation_memory_service.get_conversation_context(session_id)
        
        print(f"   Session stats: {session_stats}")
        print(f"   Current active entities: {current_context.active_entities if current_context else {}}")
        
        # Format response for frontend
        chat_response = ChatResponse(
            response=response_data.response,
            sources=response_data.sources,
            suggested_questions=response_data.suggested_questions,
            session_id=session_id,
            confidence=response_data.confidence,
            structured_data=response_data.structured_data,
            conversation_context={
                "total_messages": session_stats.get("total_messages", 0),
                "recent_messages": session_stats.get("recent_messages", 0),
                "historical_entities": session_stats.get("historical_entities", 0)
            },
            active_entities=dict(current_context.active_entities) if current_context else {}
        )
        
        print(f"\n🎉 CHAT RESPONSE GENERATED:")
        print(f"   Response length: {len(chat_response.response)} characters")
        print(f"   Sources: {len(chat_response.sources)}")
        print(f"   Suggested questions: {len(chat_response.suggested_questions)}")
        print(f"   Session ID: {chat_response.session_id}")
        print(f"   Confidence: {chat_response.confidence:.2f}")
        
        logger.info(f"🎉 Chat response with memory generated successfully (confidence: {response_data.confidence:.2f})")
        return chat_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        # Return user-friendly error response
        return ChatResponse(
            response="Izvinjavam se, trenutno nije moguće da odgovorim na vaše pitanje. Molim pokušajte kasnije.",
            sources=[],
            suggested_questions=["Molim pokušajte ponovo za nekoliko trenutaka"],
            session_id=chat_message.session_id,
            confidence=0.0,
            structured_data={},
            conversation_context={},
            active_entities={}
        )

# Enhanced RAG with Streaming - Best of both worlds!
@app.post("/chat/stream")
async def enhanced_chat_stream(chat_message: ChatMessage):
    """Enhanced RAG endpoint with real-time streaming for optimal UX"""
    try:
        user_message = chat_message.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        session_id = chat_message.session_id or f"session_{int(datetime.now().timestamp())}"
        
        logger.info(f"🎬 Enhanced RAG streaming: '{user_message}' [Session: {session_id[:8]}]")

        async def enhanced_rag_stream_generator():
            """Enhanced RAG pipeline with streaming response and conversation memory"""
            try:
                start_time = datetime.now()
                
                # Helper function to check if query needs detailed content analysis
                def check_needs_detailed_content(query: str) -> bool:
                    """Check if query requires detailed document content"""
                    detail_keywords = [
                        'datumi', 'datum', 'kada', 'koji dani', 'polazak', 'povratak',
                        'program', 'itinerar', 'šta je uključeno', 'detaljno',
                        'više informacija', 'specifično', 'dodatno', 'extra',
                        'cene', 'cenovnik', 'košta', 'price', 'koliko',
                        'cena', 'cenu', 'cene', 'troškovi', 'troškove',
                        'plaćanje', 'plaćanja', 'novac', 'budget', 'budžet',
                        'koliko košta', 'koliko je', 'koliko je cena',
                        'detaljnije', 'precizno', 'tačno', 'konkretno',
                        'više detalja', 'više informacija', 'šta sve',
                        'koja je cena', 'koja cena', 'koje su cene'
                    ]
                    
                    query_lower = query.lower()
                    found_keywords = [keyword for keyword in detail_keywords if keyword in query_lower]
                    needs_detailed = len(found_keywords) > 0
                    
                    return needs_detailed

                # Step 0: Save user message to conversation memory
                await conversation_memory_service.save_message(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=user_message
                )

                # Step 1: Context-aware self-querying
                structured_query = await self_querying_service.parse_query_with_context(
                    user_message, session_id
                )

                # Step 1.5: Extract entities from the message
                entity_extraction_result = await named_entity_extractor.extract_entities_from_message(user_message)
                if entity_extraction_result.entities:
                    extracted_entities = {}
                    for entity_type, entity_obj in entity_extraction_result.entities.items():
                        extracted_entities[entity_type] = entity_obj.entity_value
                    await conversation_memory_service.update_active_entities(session_id, extracted_entities)

                # Step 2: Query expansion
                expanded_query = await query_expansion_service.expand_query_llm(
                    structured_query.semantic_query
                )

                # Step 3: Vector search with filters
                search_query = SearchQuery(
                    query=expanded_query,
                    filters=structured_query.filters,
                    limit=5
                )
                search_results = vector_service.search(search_query)
                
                # Handle no results with fallback strategies
                if len(search_results.results) == 0:
                    # Fallback 1: Try without filters
                    fallback_search_query = SearchQuery(
                        query=expanded_query,
                        filters={},
                        limit=5
                    )
                    fallback_results = vector_service.search(fallback_search_query)
                    
                    if len(fallback_results.results) > 0:
                        search_results = fallback_results
                    else:
                        # Fallback 2: Try with original query
                        basic_search_query = SearchQuery(
                            query=structured_query.semantic_query,
                            filters={},
                            limit=5
                        )
                        basic_results = vector_service.search(basic_search_query)
                        
                        if len(basic_results.results) > 0:
                            search_results = basic_results

                # Step 4: Prepare context content for AI
                context_content = ""
                sources = []
                
                for i, result in enumerate(search_results.results[:3]):
                    context_content += f"\n## Source: {result.metadata.source_file}\n{result.text[:400]}...\n"
                    sources.append(result.metadata.source_file)

                # Step 4.5: Get conversation context for AI prompt
                conversation_context = await conversation_memory_service.build_hybrid_context_for_query(session_id)
                recent_conv = conversation_context.get('recent_conversation', [])
                active_entities = conversation_context.get('active_entities', {})

                # Step 5: Create enhanced system prompt
                needs_detailed = check_needs_detailed_content(user_message)
                has_context = len(context_content.strip()) > 0
                
                if needs_detailed and has_context:
                    # Detailed mode with full document content
                    detailed_context = ""
                    for i, result in enumerate(search_results.results[:3], 1):
                        content = result.text
                        metadata = result.metadata.model_dump()
                        source_file = metadata.get('source_file', f'Document {i}')
                        similarity = result.similarity_score
                        
                        detailed_context += f"\n--- DOKUMENT {i}: {source_file} (Relevantnost: {similarity:.1%}) ---\n"
                        detailed_context += f"KOMPLETNI SADRŽAJ:\n{content}\n"
                        detailed_context += f"METADATA: {metadata}\n"
                        detailed_context += "-" * 80 + "\n"
                    
                    system_prompt = f"""Ti si TurBot, profesionalni turistički agent sa pristupom KOMPLETNIM informacijama o aranžmanima.

KOMPLETNE INFORMACIJE O ARANŽMANIMA:
{detailed_context}

KRITIČNO - IMAŠ PRISTUP KOMPLETNIM PODACIMA:
- Koristi SVE dostupne informacije iz dokumenata iznad
- Ekstraktuj cene, datume, detalje programa iz KOMPLETNOG sadržaja
- Ne ograničavaj se samo na metadata - čitaj i analiziraj pun tekst dokumenata
- Ako vidiš cene ili detalje u tekstu, koristi ih u odgovoru

INSTRUKCIJE:
- Odgovori DETALJNO sa konkretnim informacijama (datumi, cene, program)
- Analiziraj KOMPLETNI sadržaj dokumenata da pronađeš sve relevantne informacije
- Budi SPECIFIČAN sa datumima, cenama, uslugama koje pronađeš u tekstovima
- Ako pronađeš cene u dokumentima, OBAVEZNO ih navedi
- Navedi odakle su informacije (nazivi dokumenata)

STIL: Profesionalan, informativan, sa svim detaljima iz dokumenata"""
                    
                elif has_context:
                    # Standard mode
                    system_prompt = f"""Ti si TurBot, AI asistent za turističke agencije. Odgovori na srpskom jeziku koristeći dostupne informacije.

DOSTUPNI SADRŽAJ:
{context_content}

INSTRUKCIJE:
- Odgovori prirodno i prijateljski na srpskom jeziku
- Koristi SAMO informacije iz dostupnih dokumenata iznad
- Ako nemaš tačne informacije u dostupnim dokumentima, jasno reci da nemaš podatke
- Fokusiraj se na korisne detalje (cene, datumi, lokacije)
- Budi kratak i precizan (maksimalno 3-4 pasusa)

KRITIČNO - PROTIV HALUCINACIJE:
- NIKAD ne izmišljaj destinacije, cene, datume ili hotele
- Ako informacija nije u dostupnim dokumentima, reci "Nemam tu informaciju"
- Uvek navedi odakle su informacije (nazivi dokumenata)"""
                else:
                    # No context mode
                    system_prompt = f"""Ti si TurBot, AI asistent za turističke agencije. 

SITUACIJA: Trenutno nemam dostupne dokumente koji odgovaraju na korisničko pitanje.

INSTRUKCIJE:
- Budi iskren da trenutno nemaš informacije o tome u bazi podataka
- Preporuči korisniku da:
  1. Proba sa drugačijim kriterijumima pretrage
  2. Kontaktira direktno turističku agenciju
  3. Pita o sličnim destinacijama ili terminima
- Budi prijateljski i pomozi koliko možeš bez izmišljanja podataka

KRITIČNO:
- NIKAD ne izmišljaj destinacije, cene, datume ili hotele
- Budi transparentan o ograničenjima"""

                # Add conversation context if available
                if recent_conv:
                    context_text = "\n\nKONTEKST RAZGOVORA:\n"
                    for msg in recent_conv[-2:]:
                        context_text += f"{msg['role']}: {msg['content'][:100]}...\n"
                    system_prompt += context_text

                # Step 6: Stream response from OpenAI
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
                
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    stream=True,
                    temperature=0.1,
                    max_tokens=400
                )

                # Step 7: Stream response to frontend
                full_response = ""
                chunk_count = 0
                
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        chunk_count += 1
                        
                        data = {
                            "type": "content",
                            "content": content,
                            "chunk_id": chunk_count
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        
                        await asyncio.sleep(0.02)

                # Step 8: Generate suggested questions
                suggested_questions = []
                intent = structured_query.intent.lower() if structured_query.intent else ""
                
                if "hotel" in intent or "accommodation" in intent:
                    suggested_questions = ["Koliko košta?", "Ima li spa centar?", "Kada je dostupno?"]
                elif "price" in intent or "cost" in intent:
                    suggested_questions = ["Šta je uključeno?", "Ima li popusta?", "Kako se plaća?"]
                elif "tour" in intent or "travel" in intent:
                    suggested_questions = ["Koliko traje?", "Šta je uključeno?", "Kada su termini?"]
                else:
                    suggested_questions = ["Recite mi više", "Koliko košta?", "Ima li alternativa?"]

                # Step 9: Calculate confidence
                confidence = 0.90
                confidence_factors = []
                
                if len(search_results.results) == 0:
                    confidence = 0.20
                    confidence_factors.append("No search results (-70%)")
                elif len(structured_query.filters) > 0:
                    confidence = 0.95
                    confidence_factors.append(f"Filters applied (+5%): {structured_query.filters}")
                elif len(search_results.results) < 3:
                    confidence = 0.70
                    confidence_factors.append(f"Few results (-20%): {len(search_results.results)} results")
                else:
                    confidence_factors.append(f"Good results: {len(search_results.results)} results")

                # Step 10: Send final metadata
                final_data = {
                    "type": "complete",
                    "sources": [{"document_name": source, "similarity": 0.90} for source in sources[:5]],
                    "suggestions": suggested_questions,
                    "confidence": confidence,
                    "total_chunks": chunk_count,
                    "response_length": len(full_response),
                    "enhanced_rag": True,
                    "filters_applied": len(structured_query.filters),
                    "entities_extracted": len(entity_extraction_result.entities) if entity_extraction_result.entities else 0
                }
                
                yield f"data: {json.dumps(final_data)}\n\n"
                
                # Step 11: Save AI response to conversation memory
                await conversation_memory_service.save_message(
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                    entities=entity_extraction_result.entities if entity_extraction_result.entities else None,
                    sources=sources,
                    confidence=confidence
                )

            except Exception as e:
                error_data = {
                    "type": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "session_id": session_id,
                    "fallback_message": "Izvinjavam se, došlo je do greške pri obradi vašeg upita. Molim pokušajte ponovo sa drugačijim pitanjem."
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            enhanced_rag_stream_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
        
    except Exception as e:
        logger.error(f"Enhanced RAG streaming error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Simple chat endpoint for testing/fallback
@app.post("/chat/simple")
async def simple_chat(message: dict):
    """Simple chat endpoint for testing - direct search without LLM generation"""
    try:
        user_message = message.get("message", "")
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Direct search without complex RAG pipeline
        search_query = SearchQuery(
            query=user_message,
            filters=None,
            limit=3
        )
        
        search_results = vector_service.search(search_query)
        
        # Simple response formatting
        if search_results.results:
            response_text = f"Pronašao sam {len(search_results.results)} relevantnih rezultata za '{user_message}':\n\n"
            
            for i, result in enumerate(search_results.results, 1):
                source = result.metadata.source_file or "Nepoznat izvor"
                preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
                response_text += f"{i}. {source} (relevantnost: {result.similarity_score:.1%})\n{preview}\n\n"
        else:
            response_text = "Nažalost, nisam pronašao relevantne informacije za vaš upit. Molim pokušajte sa drugim terminima."
        
        return {
            "response": response_text,
            "sources": [{"document_name": r.metadata.source_file, "similarity": r.similarity_score} for r in search_results.results],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Simple chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    ) 