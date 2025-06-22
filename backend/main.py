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
        
        print(f"\n🎯 PROCESSING CHAT MESSAGE:")
        print(f"   User message: '{user_message}'")
        print(f"   Session ID: {session_id}")
        print(f"   User type: {chat_message.user_type}")
        
        logger.info(f"🎯 Processing chat message: '{user_message}' [Session: {session_id[:8]}]")
        
        async def enhanced_rag_with_memory_pipeline():
            """Complete Enhanced RAG pipeline with conversation memory"""
            try:
                print(f"\n🚀 STARTING ENHANCED RAG PIPELINE:")
                
                # STEP 0: Save user message to conversation memory
                print("0️⃣ SAVING USER MESSAGE TO CONVERSATION MEMORY...")
                await conversation_memory_service.save_message(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=user_message
                )
                
                # Step 1: Context-Aware Self-Querying - Parse with conversation context
                print("1️⃣ CONTEXT-AWARE SELF-QUERYING...")
                structured_query = await self_querying_service.parse_query_with_context(
                    user_message, session_id
                )
                print(f"   Structured query: {structured_query.semantic_query}")
                print(f"   Extracted filters: {structured_query.filters}")
                print(f"   Intent: {structured_query.intent}")
                
                # Extract entities from current message for context updating
                print("2️⃣ EXTRACTING ENTITIES FROM MESSAGE...")
                entity_extraction_result = await named_entity_extractor.extract_entities_from_message(user_message)
                if entity_extraction_result.entities:
                    # Convert TourismEntity objects to simple dict for active entities
                    extracted_entities = {}
                    for entity_type, entity_obj in entity_extraction_result.entities.items():
                        extracted_entities[entity_type] = entity_obj.entity_value
                    
                    print(f"   Extracted entities: {extracted_entities}")
                    
                    # Update active entities in conversation memory
                    await conversation_memory_service.update_active_entities(session_id, extracted_entities)
                else:
                    print(f"   No entities extracted from message")
                
                # Step 3: Query Expansion - Enhance semantic search
                print("3️⃣ QUERY EXPANSION...")
                expanded_query = await query_expansion_service.expand_query_llm(
                    structured_query.semantic_query
                )
                print(f"   Expanded query: {expanded_query}")
                
                # Step 4: Enhanced Vector Search with context-aware filters
                print("4️⃣ ENHANCED VECTOR SEARCH...")
                search_query = SearchQuery(
                    query=expanded_query,
                    filters=structured_query.filters,
                    limit=5  # Get top 5 results for better context
                )
                
                search_results = vector_service.search(search_query)
                print(f"   Found {len(search_results.results)} search results")
                
                # Convert search results to format expected by response generator
                search_results_dict = []
                for i, result in enumerate(search_results.results):
                    search_results_dict.append({
                        'content': result.text,
                        'metadata': result.metadata.model_dump(),
                        'similarity': result.similarity_score,
                        'document_name': result.metadata.source_file or 'Unknown'
                    })
                    print(f"      {i+1}. {result.metadata.source_file} (similarity: {result.similarity_score:.2f})")
                
                # Step 5: Context-Aware Response Generation
                print("5️⃣ CONTEXT-AWARE RESPONSE GENERATION...")
                
                # Get conversation context for response generation
                conversation_context = await conversation_memory_service.build_hybrid_context_for_query(session_id)
                
                print(f"   Conversation context to be sent to AI:")
                print(f"      Recent conversation: {len(conversation_context.get('recent_conversation', []))} messages")
                print(f"      Active entities: {conversation_context.get('active_entities', {})}")
                print(f"      Total messages: {conversation_context.get('total_messages', 0)}")
                
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
                
                print(f"   Generated response length: {len(response_data.response)} characters")
                print(f"   Response confidence: {response_data.confidence:.2f}")
                
                # STEP 6: Save AI response to conversation memory
                print("6️⃣ SAVING AI RESPONSE TO MEMORY...")
                await conversation_memory_service.save_message(
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=response_data.response,
                    entities=entity_extraction_result.entities if entity_extraction_result.entities else None,
                    sources=[source.get('document_name', '') for source in response_data.sources],
                    confidence=response_data.confidence
                )
                
                print(f"✅ ENHANCED RAG WITH MEMORY PIPELINE COMPLETED!")
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
        
        print(f"\n🎬 ENHANCED RAG STREAMING: '{user_message[:50]}...' [Session: {session_id[:8]}]")
        logger.info(f"🎬 Enhanced RAG streaming: '{user_message}' [Session: {session_id[:8]}]")
        
        async def enhanced_rag_stream_generator():
            """Enhanced RAG pipeline with streaming response and conversation memory"""
            try:
                print(f"\n🔍 ===== ENHANCED RAG STREAMING DEBUG SESSION =====")
                print(f"🔍 Session ID: {session_id}")
                print(f"🔍 User Type: {chat_message.user_type}")
                print(f"🔍 Timestamp: {datetime.now().strftime('%H:%M:%S')}")
                
                # Helper function to check if query needs detailed content analysis
                def check_needs_detailed_content(query: str) -> bool:
                    """Check if query requires detailed document content"""
                    detail_keywords = [
                        'datumi', 'datum', 'kada', 'koji dani', 'polazak', 'povratak',
                        'program', 'itinerar', 'šta je uključeno', 'detaljno',
                        'više informacija', 'specifično', 'dodatno', 'extra',
                        'cene', 'cenovnik', 'košta', 'price', 'koliko',
                        # Dodatne ključne reči za cene
                        'cena', 'cenu', 'cene', 'troškovi', 'troškove',
                        'plaćanje', 'plaćanja', 'novac', 'budget', 'budžet',
                        'koliko košta', 'koliko je', 'koliko je cena',
                        # Dodatne za detalje
                        'detaljnije', 'precizno', 'tačno', 'konkretno',
                        'više detalja', 'više informacija', 'šta sve',
                        'koja je cena', 'koja cena', 'koje su cene'
                    ]
                    
                    query_lower = query.lower()
                    found_keywords = [keyword for keyword in detail_keywords if keyword in query_lower]
                    needs_detailed = len(found_keywords) > 0
                    
                    return needs_detailed
                
                # STEP 0: Save user message to conversation memory
                print(f"\n🔍 STEP 0 - CONVERSATION MEMORY:")
                await conversation_memory_service.save_message(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=user_message
                )
                print(f"   ✅ User message saved to conversation memory")
                
                # Step 1: Context-Aware Self-Querying - Parse with conversation context
                print(f"\n🔍 STEP 1 - SELF-QUERYING:")
                print(f"   📝 Original Query: '{user_message}'")
                structured_query = await self_querying_service.parse_query_with_context(
                    user_message, session_id
                )
                print(f"   🎯 Semantic Query: '{structured_query.semantic_query}'")
                print(f"   🔧 Extracted Filters: {structured_query.filters}")
                print(f"   💭 Detected Intent: {structured_query.intent}")
                print(f"   📊 Filter Count: {len(structured_query.filters)}")
                
                # Extract entities from current message for context updating
                print(f"\n🔍 STEP 1.5 - ENTITY EXTRACTION:")
                entity_extraction_result = await named_entity_extractor.extract_entities_from_message(user_message)
                if entity_extraction_result.entities:
                    extracted_entities = {}
                    for entity_type, entity_obj in entity_extraction_result.entities.items():
                        extracted_entities[entity_type] = entity_obj.entity_value
                    print(f"   🏷️  Extracted Entities: {extracted_entities}")
                    await conversation_memory_service.update_active_entities(session_id, extracted_entities)
                    print(f"   ✅ Entities updated in conversation memory")
                else:
                    print(f"   ⚠️  No entities extracted from message")
                
                # Step 2: Query Expansion - Enhance semantic search
                print(f"\n🔍 STEP 2 - QUERY EXPANSION:")
                print(f"   📝 Input Query: '{structured_query.semantic_query}'")
                expanded_query = await query_expansion_service.expand_query_llm(
                    structured_query.semantic_query
                )
                print(f"   🚀 Expanded Query: '{expanded_query}'")
                print(f"   📏 Expansion Ratio: {len(expanded_query) / len(structured_query.semantic_query):.2f}x")
                
                # Step 3: Enhanced Vector Search with context-aware filters
                print(f"\n🔍 STEP 3 - VECTOR SEARCH:")
                search_query = SearchQuery(
                    query=expanded_query,
                    filters=structured_query.filters,
                    limit=5
                )
                print(f"   🔍 Search Query: '{search_query.query}'")
                print(f"   🔧 Applied Filters: {search_query.filters}")
                print(f"   📊 Result Limit: {search_query.limit}")
                
                search_results = vector_service.search(search_query)
                print(f"   📋 Search Results: {len(search_results.results)} documents found")
                
                # Debug individual search results
                for i, result in enumerate(search_results.results[:3]):
                    print(f"   📄 Result {i+1}:")
                    print(f"      📁 Source: {result.metadata.source_file}")
                    print(f"      🎯 Similarity: {result.similarity_score:.3f}")
                    print(f"      📝 Content Preview: {result.text[:100]}...")
                    print(f"      🏷️  Metadata: {dict(result.metadata)}")
                
                if len(search_results.results) == 0:
                    print(f"   ⚠️  WARNING: No search results found!")
                    print(f"   🔍 Possible causes:")
                    print(f"      - Filters too restrictive: {structured_query.filters}")
                    print(f"      - Query expansion ineffective: '{expanded_query}'")
                    print(f"      - No relevant documents in database")
                    print(f"      - Similarity threshold too high")
                
                # Step 4: Prepare context for streaming response
                print(f"\n🔍 STEP 4 - CONTEXT PREPARATION:")
                context_content = ""
                sources = []
                
                # Check if we have search results
                if len(search_results.results) == 0:
                    print(f"   ⚠️  No search results - implementing fallback strategy")
                    
                    # FALLBACK STRATEGY 1: Try search without filters
                    print(f"   🔄 FALLBACK 1: Trying search without filters...")
                    fallback_search_query = SearchQuery(
                        query=expanded_query,
                        filters={},  # Remove all filters
                        limit=5
                    )
                    fallback_results = vector_service.search(fallback_search_query)
                    print(f"   📋 Fallback Results: {len(fallback_results.results)} documents found")
                    
                    if len(fallback_results.results) > 0:
                        search_results = fallback_results
                        print(f"   ✅ Fallback search successful, using {len(search_results.results)} results")
                    else:
                        # FALLBACK STRATEGY 2: Try basic semantic search with original query
                        print(f"   🔄 FALLBACK 2: Trying basic semantic search...")
                        basic_search_query = SearchQuery(
                            query=structured_query.semantic_query,  # Use original query
                            filters={},
                            limit=5
                        )
                        basic_results = vector_service.search(basic_search_query)
                        print(f"   📋 Basic Search Results: {len(basic_results.results)} documents found")
                        
                        if len(basic_results.results) > 0:
                            search_results = basic_results
                            print(f"   ✅ Basic search successful, using {len(search_results.results)} results")
                        else:
                            print(f"   ❌ All fallback strategies failed - no relevant documents found")
                
                # Prepare context from available results
                for i, result in enumerate(search_results.results[:3]):  # Top 3 results
                    context_content += f"\n## Source: {result.metadata.source_file}\n{result.text[:400]}...\n"
                    sources.append(result.metadata.source_file)
                    print(f"   📄 Added to context: {result.metadata.source_file} ({len(result.text[:400])} chars)")
                
                print(f"   📊 Final Context Stats:")
                print(f"      📝 Context Length: {len(context_content)} characters")
                print(f"      📁 Sources Count: {len(sources)}")
                print(f"      📋 Sources: {sources}")
                
                # Get conversation context
                print(f"\n🔍 STEP 4.5 - CONVERSATION CONTEXT:")
                conversation_context = await conversation_memory_service.build_hybrid_context_for_query(session_id)
                recent_conv = conversation_context.get('recent_conversation', [])
                active_entities = conversation_context.get('active_entities', {})
                print(f"   💬 Recent Conversation: {len(recent_conv)} messages")
                print(f"   🏷️  Active Entities: {active_entities}")
                
                # Step 5: Create enhanced system prompt with anti-hallucination instructions
                print(f"\n🔍 STEP 5 - SYSTEM PROMPT CREATION:")
                
                # Check if we need detailed content for this query
                needs_detailed = check_needs_detailed_content(user_message)
                print(f"   🔍 DETAILED CONTENT CHECK:")
                print(f"      Query: '{user_message}'")
                print(f"      Needs detailed: {needs_detailed}")
                
                # Determine if we have sufficient context
                has_context = len(context_content.strip()) > 0
                print(f"   📋 Has Context: {has_context}")
                
                # If needs detailed content and we have results, use FULL content
                if needs_detailed and has_context:
                    print(f"   🔍 USING DETAILED CONTENT STRATEGY...")
                    
                    # Rebuild context with FULL content (not limited to 400 chars)
                    detailed_context = ""
                    for i, result in enumerate(search_results.results[:3], 1):  # Top 3 for detailed
                        content = result.text  # FULL CONTENT!
                        metadata = result.metadata.model_dump()
                        source_file = metadata.get('source_file', f'Document {i}')
                        similarity = result.similarity_score
                        
                        print(f"      Document {i}: {source_file}")
                        print(f"         Content length: {len(content)} characters (FULL)")
                        print(f"         Similarity: {similarity:.2f}")
                        
                        detailed_context += f"\n--- DOKUMENT {i}: {source_file} (Relevantnost: {similarity:.1%}) ---\n"
                        detailed_context += f"KOMPLETNI SADRŽAJ:\n{content}\n"
                        detailed_context += f"METADATA: {metadata}\n"
                        detailed_context += "-" * 80 + "\n"
                    
                    print(f"      Total detailed context: {len(detailed_context)} characters")
                    
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
                    
                    print(f"   💰 DETAILED CONTENT MODE: ~{len(system_prompt) // 4} estimated tokens")
                    
                elif has_context:
                    # Standard mode with limited content
                    system_prompt = f"""Ti si TurBot, AI asistent za turističke agencije. Odgovori na srpskom jeziku koristeći dostupne informacije.

DOSTUPNI SADRŽAJ:
{context_content}

INSTRUKCIJE:
- Odgovori prirodno i prijateljski na srpskom jeziku
- Koristi SAMO informacije iz dostupnih dokumenata iznad
- Ako nemaš tačne informacije u dostupnim dokumentima, jasno reci da nemaš podatke
- Fokusiraj se na korisne detalje (cene, datumi, lokacije)
- Budi kratak i precizan (maksimalno 3-4 pasusa)
- Izbegavaj dugačke strukture i sekcije

KRITIČNO - PROTIV HALUCINACIJE:
- NIKAD ne izmišljaj destinacije, cene, datume ili hotele
- Ako informacija nije u dostupnim dokumentima, reci "Nemam tu informaciju"
- Uvek navedi odakle su informacije (nazivi dokumenata)"""
                else:
                    # No context available - use no-data prompt
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
                
                print(f"   📏 System Prompt Length: {len(system_prompt)} characters")
                print(f"   🛡️  Anti-Hallucination: {'✅ Enabled' if has_context else '✅ No-Data Mode'}")

                # Add conversation context if available
                recent_conv = conversation_context.get('recent_conversation', [])
                if recent_conv:
                    context_text = "\n\nKONTEKST RAZGOVORA:\n"
                    for msg in recent_conv[-2:]:  # Last 2 messages
                        context_text += f"{msg['role']}: {msg['content'][:100]}...\n"
                    system_prompt += context_text

                # Step 6: OpenAI streaming call with Enhanced RAG context
                print(f"\n🔍 STEP 6 - OPENAI STREAMING:")
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
                print(f"   📨 Messages to OpenAI:")
                print(f"      🤖 System Prompt: {len(system_prompt)} chars")
                print(f"      👤 User Message: '{user_message}'")
                print(f"   ⚙️  Model: gpt-4o-mini")
                print(f"   🌡️  Temperature: 0.1")
                print(f"   📏 Max Tokens: 400")
                
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    stream=True,
                    temperature=0.1,
                    max_tokens=400
                )
                
                # Step 7: Stream chunks to frontend
                print(f"\n🔍 STEP 7 - STREAMING TO FRONTEND:")
                full_response = ""
                chunk_count = 0
                start_time = datetime.now()
                
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        chunk_count += 1
                        
                        # Send content chunk
                        data = {
                            "type": "content",
                            "content": content,
                            "chunk_id": chunk_count
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        
                        # Small delay for natural typing feel
                        await asyncio.sleep(0.02)
                
                streaming_time = (datetime.now() - start_time).total_seconds()
                print(f"   ⏱️  Streaming completed in {streaming_time:.2f} seconds")
                print(f"   📊 Streaming Stats:")
                print(f"      📝 Response Length: {len(full_response)} characters")
                print(f"      📦 Total Chunks: {chunk_count}")
                print(f"      ⚡ Avg Chunk Size: {len(full_response) / chunk_count:.1f} chars" if chunk_count > 0 else "      ⚡ Avg Chunk Size: 0 chars")
                print(f"      🚀 Streaming Speed: {len(full_response) / streaming_time:.1f} chars/sec" if streaming_time > 0 else "      🚀 Streaming Speed: N/A")
                
                # Step 8: Generate suggested questions based on structured query intent
                print(f"\n🔍 STEP 8 - SUGGESTED QUESTIONS GENERATION:")
                suggested_questions = []
                intent = structured_query.intent.lower() if structured_query.intent else ""
                print(f"   💭 Detected Intent: '{intent}'")
                
                if "hotel" in intent or "accommodation" in intent:
                    suggested_questions = ["Koliko košta?", "Ima li spa centar?", "Kada je dostupno?"]
                    print(f"   🏨 Hotel-related suggestions generated")
                elif "price" in intent or "cost" in intent:
                    suggested_questions = ["Šta je uključeno?", "Ima li popusta?", "Kako se plaća?"]
                    print(f"   💰 Price-related suggestions generated")
                elif "tour" in intent or "travel" in intent:
                    suggested_questions = ["Koliko traje?", "Šta je uključeno?", "Kada su termini?"]
                    print(f"   🎯 Tour-related suggestions generated")
                else:
                    suggested_questions = ["Recite mi više", "Koliko košta?", "Ima li alternativa?"]
                    print(f"   🔄 Default suggestions generated")
                
                print(f"   📋 Generated Suggestions: {suggested_questions}")
                
                # Step 9: Calculate confidence based on search results and filters
                print(f"\n🔍 STEP 9 - CONFIDENCE CALCULATION:")
                confidence = 0.90
                confidence_factors = []
                
                if len(search_results.results) == 0:
                    confidence = 0.20
                    confidence_factors.append("No search results (-70%)")
                elif len(structured_query.filters) > 0:
                    confidence = 0.95  # Higher confidence when filters are applied
                    confidence_factors.append(f"Filters applied (+5%): {structured_query.filters}")
                elif len(search_results.results) < 3:
                    confidence = 0.70
                    confidence_factors.append(f"Few results (-20%): {len(search_results.results)} results")
                else:
                    confidence_factors.append(f"Good results: {len(search_results.results)} results")
                
                print(f"   🎯 Final Confidence: {confidence:.2f}")
                print(f"   📊 Confidence Factors: {confidence_factors}")
                
                # Step 10: Send final metadata with enhanced information
                print(f"\n🔍 STEP 10 - FINAL METADATA:")
                final_data = {
                    "type": "complete",
                    "sources": [{"document_name": source, "similarity": 0.90} for source in sources[:5]],
                    "suggestions": suggested_questions,
                    "confidence": confidence,
                    "total_chunks": chunk_count,
                    "response_length": len(full_response),
                    "enhanced_rag": True,  # Flag to indicate this is Enhanced RAG
                    "filters_applied": len(structured_query.filters),
                    "entities_extracted": len(entity_extraction_result.entities) if entity_extraction_result.entities else 0
                }
                print(f"   📋 Metadata Summary:")
                print(f"      📁 Sources: {len(final_data['sources'])} documents")
                print(f"      💡 Suggestions: {len(final_data['suggestions'])} questions")
                print(f"      🎯 Confidence: {final_data['confidence']:.2f}")
                print(f"      🔧 Filters Applied: {final_data['filters_applied']}")
                print(f"      🏷️  Entities Extracted: {final_data['entities_extracted']}")
                
                yield f"data: {json.dumps(final_data)}\n\n"
                
                # Step 11: Save AI response to conversation memory
                print(f"\n🔍 STEP 11 - SAVE TO CONVERSATION MEMORY:")
                await conversation_memory_service.save_message(
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                    entities=entity_extraction_result.entities if entity_extraction_result.entities else None,
                    sources=sources,
                    confidence=confidence
                )
                print(f"   ✅ AI response saved to conversation memory")
                print(f"   📊 Saved Data:")
                print(f"      📝 Response: {len(full_response)} characters")
                print(f"      📁 Sources: {sources}")
                print(f"      🎯 Confidence: {confidence:.2f}")
                
                total_time = (datetime.now() - start_time).total_seconds()
                print(f"\n🎉 ===== ENHANCED RAG STREAMING SESSION COMPLETED =====")
                print(f"   ⏱️  Total Processing Time: {total_time:.2f} seconds")
                print(f"   📝 Final Response: {len(full_response)} characters")
                print(f"   📦 Total Chunks: {chunk_count}")
                print(f"   📁 Sources Used: {len(sources)}")
                print(f"   🎯 Final Confidence: {confidence:.2f}")
                print(f"   🔧 Filters Applied: {len(structured_query.filters)}")
                print(f"   🏷️  Entities Extracted: {len(entity_extraction_result.entities) if entity_extraction_result.entities else 0}")
                print(f"   ✅ Session: {session_id}")
                print(f"🔍 ==================================================")
                
            except Exception as e:
                print(f"\n❌ ===== ENHANCED RAG STREAMING ERROR =====")
                print(f"❌ Error Type: {type(e).__name__}")
                print(f"❌ Error Message: {str(e)}")
                print(f"❌ Session ID: {session_id}")
                print(f"❌ User Query: '{user_message}'")
                print(f"❌ Timestamp: {datetime.now().strftime('%H:%M:%S')}")
                
                # Try to provide more context about where the error occurred
                import traceback
                print(f"❌ Full Traceback:")
                traceback.print_exc()
                
                error_data = {
                    "type": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "session_id": session_id,
                    "fallback_message": "Izvinjavam se, došlo je do greške pri obradi vašeg upita. Molim pokušajte ponovo sa drugačijim pitanjem."
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                print(f"❌ Error response sent to frontend")
                print(f"❌ ============================================")
        
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