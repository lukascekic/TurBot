from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import logging

from routers.documents import router as documents_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TurBot API",
    description="AI Agent za turističke agencije - Core RAG Implementation",
    version="2.0.0",
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

# Include document processing router
app.include_router(documents_router)

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

# Basic chat endpoint (placeholder)
@app.post("/chat")
async def chat(message: dict):
    """Chat endpoint - placeholder for now"""
    try:
        user_message = message.get("message", "")
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Placeholder response
        response = {
            "response": f"Zdravo! Pitali ste: '{user_message}'. Trenutno sam u fazi razvoja, ali uskoro ću moći da vam pomognem sa turističkim informacijama!",
            "sources": [],
            "status": "success"
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
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