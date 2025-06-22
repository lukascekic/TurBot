from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI

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

# Configure logging
logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Enhanced RAG services
self_querying_service = SelfQueryingService(client)
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

# Enhanced chat endpoint with full RAG pipeline
@app.post("/chat", response_model=ChatResponse)
async def enhanced_chat(chat_message: ChatMessage):
    """Enhanced chat endpoint using complete RAG pipeline"""
    try:
        user_message = chat_message.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        logger.info(f"🎯 Processing chat message: '{user_message}'")
        
        # Run the Enhanced RAG pipeline in thread pool
        loop = asyncio.get_event_loop()
        
        async def enhanced_rag_pipeline():
            """Complete Enhanced RAG pipeline"""
            try:
                # Step 1: Self-Querying - Parse user intent and extract filters
                logger.info("1️⃣ Self-Querying Analysis...")
                structured_query = await self_querying_service.parse_query(user_message)
                
                # Step 2: Query Expansion - Enhance semantic search
                logger.info("2️⃣ Query Expansion...")
                expanded_query = await query_expansion_service.expand_query_llm(
                    structured_query.semantic_query
                )
                
                # Step 3: Enhanced Vector Search
                logger.info("3️⃣ Enhanced Vector Search...")
                search_query = SearchQuery(
                    query=expanded_query,
                    filters=structured_query.filters,
                    limit=5  # Get top 5 results for better context
                )
                
                search_results = vector_service.search(search_query)
                
                # Convert search results to format expected by response generator
                search_results_dict = []
                for result in search_results.results:
                    search_results_dict.append({
                        'content': result.text,
                        'metadata': result.metadata.model_dump(),
                        'similarity': result.similarity_score,
                        'document_name': result.metadata.source_file or 'Unknown'
                    })
                
                # Step 4: Intelligent Response Generation
                logger.info("4️⃣ Intelligent Response Generation...")
                response_data = await response_generator.generate_response(
                    search_results=search_results_dict,
                    structured_query=structured_query
                )
                
                logger.info(f"✅ Enhanced RAG pipeline completed successfully!")
                return response_data
                
            except Exception as e:
                logger.error(f"❌ Enhanced RAG pipeline failed: {e}")
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
                )
        
        # Execute Enhanced RAG pipeline
        response_data = await enhanced_rag_pipeline()
        
        # Format response for frontend
        chat_response = ChatResponse(
            response=response_data.response,
            sources=response_data.sources,
            suggested_questions=response_data.suggested_questions,
            session_id=chat_message.session_id,
            confidence=response_data.confidence,
            structured_data=response_data.structured_data
        )
        
        logger.info(f"🎉 Chat response generated successfully (confidence: {response_data.confidence:.2f})")
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
            structured_data={}
        )

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