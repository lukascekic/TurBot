from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import openai
import os
from pydantic import BaseModel

from services.document_service import DocumentService
from models.document import SearchQuery, SearchResponse
from services.document_detail_service import DocumentDetailService

router = APIRouter(prefix="/documents", tags=["documents"])

# Global document service instance
document_service = DocumentService()

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=2)


@router.post("/upload", response_model=Dict[str, Any])
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a PDF document"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if file.content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="Invalid content type. Only PDF files are allowed")
    
    try:
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Process PDF in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        processed_doc = await loop.run_in_executor(
            executor, 
            document_service.upload_and_process_pdf, 
            file_content, 
            file.filename
        )
        
        # Return processing result
        return {
            "filename": processed_doc.filename,
            "status": processed_doc.processing_status,
            "total_chunks": processed_doc.total_chunks,
            "error_message": processed_doc.error_message,
            "processed_at": processed_doc.processed_at.isoformat() if processed_doc.processed_at else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    query: str,
    category: Optional[str] = Query(None, description="Filter by category (hotel, restaurant, attraction, tour)"),
    location: Optional[str] = Query(None, description="Filter by location"),
    price_range: Optional[str] = Query(None, description="Filter by price range (budget, moderate, expensive, luxury)"),
    family_friendly: Optional[bool] = Query(None, description="Filter by family friendly"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """Search documents using semantic search"""
    
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Build filters
    filters = {}
    if category:
        filters["category"] = category
    if location:
        filters["location"] = location
    if price_range:
        filters["price_range"] = price_range
    if family_friendly is not None:
        filters["family_friendly"] = family_friendly
    
    try:
        # Perform search in thread pool
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            executor,
            document_service.search_documents,
            query,
            filters if filters else None,
            limit
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        stats = document_service.get_database_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/list")
async def list_documents():
    """List all uploaded documents"""
    try:
        documents = document_service.list_uploaded_documents()
        return {"documents": documents, "total": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/{filename}/info")
async def get_document_info(filename: str):
    """Get information about a specific document"""
    try:
        info = document_service.get_document_info(filename)
        if "error" in info:
            raise HTTPException(status_code=404, detail=info["error"])
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document info: {str(e)}")


@router.delete("/{filename}")
async def delete_document(filename: str):
    """Delete a document from database and storage"""
    try:
        success = document_service.remove_document(filename)
        if success:
            return {"message": f"Document {filename} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found or could not be deleted")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.post("/process-directory")
async def process_directory(directory_path: str):
    """Process all PDF files in a directory (for bulk upload)"""
    try:
        # Process in thread pool as it can be time-consuming
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            executor,
            document_service.process_documents_directory,
            directory_path
        )
        
        # Summarize results
        successful = [r for r in results if r.processing_status == "success"]
        failed = [r for r in results if r.processing_status == "error"]
        
        return {
            "total_processed": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "results": [
                {
                    "filename": r.filename,
                    "status": r.processing_status,
                    "chunks": r.total_chunks,
                    "error": r.error_message
                }
                for r in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Directory processing failed: {str(e)}")


@router.delete("/clear-database")
async def clear_database():
    """Clear all documents from the database (use with caution)"""
    try:
        success = document_service.clear_database()
        if success:
            return {"message": "Database cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear database")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear database: {str(e)}")


# Health check for document service
@router.get("/health")
async def documents_health():
    """Health check for document service"""
    try:
        stats = document_service.get_database_stats()
        return {
            "status": "healthy",
            "database_connection": "ok",
            "total_documents": stats.get("total_documents", 0)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Additional endpoints for frontend support
@router.get("/categories")
async def get_available_categories():
    """Get all available document categories"""
    try:
        stats = document_service.get_database_stats()
        categories = stats.get("categories", [])
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@router.get("/locations")
async def get_available_locations():
    """Get all available locations from documents"""
    try:
        stats = document_service.get_database_stats()
        locations = stats.get("locations", [])
        return {"locations": locations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get locations: {str(e)}")

@router.get("/search-suggestions")
async def get_search_suggestions():
    """Get suggested search queries for users"""
    suggestions = [
        "Hotel u centru Rima",
        "Letovanje u Grčkoj za porodicu", 
        "Aranžman za Amsterdam u maju",
        "Budžetno putovanje po Evropi",
        "Romantičan vikend u Parizu",
        "All inclusive u Turskoj",
        "Gradsko putovanje Madrid",
        "Krstarenje Mediteranom"
    ]
    return {"suggestions": suggestions} 

@router.get("/document-detail/{document_name}")
async def get_document_detail(document_name: str):
    """Get detailed content for a specific document"""
    try:
        detail_service = DocumentDetailService(vector_service)
        detailed_content = detail_service.get_detailed_content(document_name)
        
        if "error" in detailed_content:
            raise HTTPException(status_code=404, detail=detailed_content["error"])
        
        return {
            "status": "success",
            "document_name": detailed_content["document_name"],
            "content_length": detailed_content["content_length"],
            "total_chunks": detailed_content["total_chunks"],
            "structured_content": detailed_content["structured_content"],
            "metadata": detailed_content["metadata"]
        }
        
    except Exception as e:
        logger.error(f"Error getting document detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-detailed-response")
async def test_detailed_response(request: dict):
    """Test endpoint for detailed response generation"""
    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Get documents related to query
        search_query = SearchQuery(query=query, limit=3)
        search_results = vector_service.search(search_query)
        
        if not search_results.results:
            return {"message": "No documents found for query"}
        
        # Test detailed content retrieval
        detail_service = DocumentDetailService(vector_service)
        detailed_docs = []
        
        for result in search_results.results[:2]:  # Top 2 documents
            doc_name = result.metadata.source_file
            if doc_name:
                detailed_content = detail_service.get_detailed_content(doc_name)
                if "error" not in detailed_content:
                    detailed_docs.append(detailed_content)
        
        return {
            "status": "success",
            "query": query,
            "standard_results": len(search_results.results),
            "detailed_documents": len(detailed_docs),
            "detailed_content_summary": [
                {
                    "document": doc["document_name"],
                    "content_length": doc["content_length"],
                    "extracted_prices": doc["structured_content"].get("prices", []),
                    "extracted_dates": doc["structured_content"].get("dates", []),
                    "sections": list(doc["structured_content"].get("sections", {}).keys())
                }
                for doc in detailed_docs
            ]
        }
        
    except Exception as e:
        logger.error(f"Error testing detailed response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== STREAMING FUNCTIONALITY ====================
# Added for real-time chat experience - does not modify existing endpoints

class ChatMessage(BaseModel):
    """Simple chat message for streaming endpoint"""
    content: str

# Initialize OpenAI client for streaming (separate from existing services)
streaming_openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/chat/stream")
async def chat_stream(
    message: ChatMessage,
    session_id: str = Query(..., description="Session ID for conversation tracking"),
    user_type: str = Query("client", description="User type: client or agent")
):
    """
    Stream chat response in real-time for better UX
    Uses existing document_service for search, adds streaming response
    """
    print(f"🎬 STREAMING CHAT: '{message.content[:50]}...' [Session: {session_id[:8]}]")
    
    async def generate_stream():
        try:
            # 1. Use existing document search (no modification to existing services)
            search_query = SearchQuery(query=message.content, limit=5)
            search_results = document_service.search_documents(message.content, None, 5)
            
            # 2. Prepare context from search results
            context_content = ""
            sources = []
            if hasattr(search_results, 'results') and search_results.results:
                for result in search_results.results[:3]:  # Top 3 results
                    if hasattr(result, 'text') and hasattr(result, 'metadata'):
                        context_content += f"\n## Source: {result.metadata.source_file}\n{result.text[:400]}...\n"
                        sources.append(result.metadata.source_file)
            
            # 3. Create system prompt for tourism assistant
            system_prompt = f"""Ti si TurBot, AI asistent za turističke agencije. Odgovori na srpskom jeziku koristeći dostupne informacije.

DOSTUPNI SADRŽAJ:
{context_content}

INSTRUKCIJE:
- Odgovori prirodno i prijateljski na srpskom jeziku
- Koristi informacije iz dostupnih dokumenata
- Ako nemaš tačne informacije, budi iskren
- Fokusiraj se na korisne detalje (cene, datumi, lokacije)
- Budi kratak i precizan"""

            # 4. OpenAI streaming call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message.content}
            ]
            
            response = await streaming_openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                temperature=0.1,
                max_tokens=400
            )
            
            # 5. Stream chunks to frontend
            full_response = ""
            chunk_count = 0
            
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
            
            print(f"🎬 STREAMING COMPLETED: {len(full_response)} chars, {chunk_count} chunks")
            
            # 6. Generate suggested questions based on content
            suggested_questions = []
            content_lower = message.content.lower()
            if "hotel" in content_lower or "smeštaj" in content_lower:
                suggested_questions = ["Koliko košta?", "Ima li spa centar?", "Kada je dostupno?"]
            elif "cena" in content_lower or "košta" in content_lower:
                suggested_questions = ["Šta je uključeno?", "Ima li popusta?", "Kako se plaća?"]
            elif "putovanje" in content_lower or "aranžman" in content_lower:
                suggested_questions = ["Koliko traje?", "Šta je uključeno?", "Kada su termini?"]
            else:
                suggested_questions = ["Recite mi više", "Koliko košta?", "Ima li alternativa?"]
            
            # 7. Send final metadata
            final_data = {
                "type": "complete",
                "sources": sources[:5],
                "suggestions": suggested_questions,
                "confidence": 0.90,
                "total_chunks": chunk_count,
                "response_length": len(full_response)
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
            print(f"🎉 STREAMING CHAT COMPLETED: {len(full_response)} chars")
            
        except Exception as e:
            print(f"❌ STREAMING ERROR: {str(e)}")
            error_data = {
                "type": "error",
                "error": str(e),
                "fallback_message": "Izvinjavam se, došlo je do greške. Molim pokušajte ponovo."
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    ) 