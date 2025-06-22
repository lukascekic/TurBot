from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class DocumentMetadata(BaseModel):
    """Enhanced metadata for tourism documents"""
    category: Optional[str] = None  # hotel, restaurant, attraction, tour
    destination: str  # Primary destination - MANDATORY
    price_range: Optional[str] = None  # budget, moderate, expensive, luxury
    family_friendly: Optional[bool] = None
    seasonal: Optional[str] = None  # year_round, summer, winter, spring, autumn
    travel_month: Optional[str] = None  # specific month like "august", "july", etc.
    source_file: Optional[str] = None
    page_number: Optional[int] = None
    
    # AI-Enhanced metadata fields
    duration_days: Optional[int] = None  # Trip duration in days
    transport_type: Optional[str] = None  # bus, plane, train, ship
    travel_dates: Optional[str] = None  # JSON string for flexible date storage
    price_details: Optional[str] = None  # JSON string for detailed pricing
    confidence_score: Optional[float] = None  # AI extraction confidence (0-1)
    


class DocumentChunk(BaseModel):
    """Represents a chunk of processed document"""
    id: Optional[str] = None
    text: str
    metadata: DocumentMetadata
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None

class ProcessedDocument(BaseModel):
    """Represents a fully processed PDF document"""
    filename: str
    chunks: List[DocumentChunk]
    total_chunks: int
    processing_status: str  # success, error, processing
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None

class SearchQuery(BaseModel):
    """Search query with filters"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    threshold: float = 0.1  # minimum similarity score

class SearchResult(BaseModel):
    """Search result item"""
    chunk_id: str
    text: str
    metadata: DocumentMetadata
    similarity_score: float

class SearchResponse(BaseModel):
    """Search response with results"""
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time: float 