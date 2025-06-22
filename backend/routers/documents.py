from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from services.document_service import DocumentService
from models.document import SearchQuery, SearchResponse

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