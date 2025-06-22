import chromadb
from chromadb.config import Settings
import openai
from typing import List, Dict, Any, Optional
import os
import time
from pathlib import Path
import logging

from models.document import DocumentChunk, SearchQuery, SearchResult, SearchResponse, DocumentMetadata

# Configure detailed logging
logger = logging.getLogger(__name__)

class VectorService:
    """Service for managing vector embeddings and similarity search"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize ChromaDB with persistent storage - NEW CLEAN DATABASE
        # Use absolute path to avoid working directory issues
        current_file = Path(__file__).parent.parent.parent  # Go from services/ to app/
        db_path = current_file / "chroma_db_new"
        db_path.mkdir(exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection for tourism documents
        self.collection = self.chroma_client.get_or_create_collection(
            name="tourism_documents",
            metadata={"description": "Tourism documents and arrangements"}
        )
        
        logger.info(f"🗄️ Vector database initialized at {db_path}")
        current_count = len(self.collection.get()["ids"])
        logger.info(f"📊 Current database contains {current_count} documents")
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise
    
    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts in batch"""
        try:
            logger.info(f"🔗 Creating embeddings for {len(texts)} texts...")
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            logger.info(f"✅ Successfully created {len(response.data)} embeddings")
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"❌ Error creating embeddings: {e}")
            raise
    
    def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """Add document chunks to the vector database"""
        try:
            if not chunks:
                logger.info("⚠️ No chunks to add")
                return True
            
            logger.info(f"💾 Adding {len(chunks)} chunks to vector database...")
            
            # Check for existing documents to handle duplicates
            existing_docs = self.collection.get()
            existing_ids = set(existing_docs["ids"])
            logger.info(f"📋 Found {len(existing_ids)} existing document IDs in database")
            
            # Filter out chunks that already exist
            new_chunks = []
            duplicate_count = 0
            for chunk in chunks:
                if chunk.id in existing_ids:
                    duplicate_count += 1
                    logger.info(f"🔄 Skipping duplicate chunk: {chunk.id}")
                else:
                    new_chunks.append(chunk)
            
            logger.info(f"📊 Processing: {len(new_chunks)} new chunks, {duplicate_count} duplicates skipped")
            
            if not new_chunks:
                logger.info("✅ All chunks already exist in database")
                return True
            
            # Extract texts for embedding
            texts = [chunk.text for chunk in new_chunks]
            
            # Create embeddings in batch for efficiency
            embeddings = self.create_embeddings_batch(texts)
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            chunk_embeddings = []
            
            for i, chunk in enumerate(new_chunks):
                ids.append(chunk.id)
                documents.append(chunk.text)
                
                # Convert metadata to dict, handling None values
                metadata_dict = chunk.metadata.model_dump()
                logger.info(f"📝 Chunk {i+1} metadata: source_file={metadata_dict.get('source_file')}, destination={metadata_dict.get('destination')}")
                
                # ChromaDB doesn't handle None values well, so convert to empty strings
                # Special handling for page_number which should be int or None
                cleaned_metadata = {}
                for k, v in metadata_dict.items():
                    if k == "page_number":
                        cleaned_metadata[k] = v if v is not None else 0
                    else:
                        cleaned_metadata[k] = v if v is not None else ""
                metadatas.append(cleaned_metadata)
                chunk_embeddings.append(embeddings[i])
            
            # Add to ChromaDB collection
            logger.info(f"💾 Saving {len(ids)} chunks to ChromaDB...")
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=chunk_embeddings
            )
            
            # Verify addition
            new_count = len(self.collection.get()["ids"])
            logger.info(f"✅ Successfully added chunks. Database now contains {new_count} total documents")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding documents to vector database: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def search(self, query: SearchQuery) -> SearchResponse:
        """
        Enhanced search with soft filtering and weighted scoring
        
        Destination is mandatory, other filters are used for ranking/scoring
        """
        """Search for similar documents"""
        start_time = time.time()
        
        try:
            # Create embedding for the query
            query_embedding = self.create_embedding(query.query)
            
            # Prepare ChromaDB query parameters
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": query.limit * 3  # Get more results for post-filtering
            }
            
            # Add metadata filters if provided using PRIORITY HIERARCHY
            primary_filter = None
            if query.filters:
                # FILTER PRIORITY HIERARCHY for non-location queries
                priority_filters = [
                    "destination",      # Priority 1: Location-specific queries
                    "location",         # Priority 1b: Backward compatibility
                    "travel_month",     # Priority 2: Seasonal queries ("u avgustu")
                    "season",           # Priority 2b: General seasonal
                    "category",         # Priority 3: Category queries ("letovanja", "hoteli")
                    "price_range",      # Priority 4: Budget queries ("jeftino")
                    "subcategory"       # Priority 5: Specific subcategories
                ]
                
                for filter_key in priority_filters:
                    if filter_key in query.filters:
                        value = query.filters[filter_key]
                        if value and value != "" and value is not None:
                            # CASE NORMALIZATION for destination/location
                            if filter_key in ["destination", "location"]:
                                # Normalize to title case to match database format
                                normalized_value = str(value).strip().title()
                                # Always use "destination" in ChromaDB query (new schema)
                                primary_filter = {"destination": normalized_value}
                                search_params["where"] = primary_filter
                                logger.info(f"🎯 Using LOCATION filter: destination={normalized_value}")
                            elif filter_key == "travel_month":
                                # Use travel_month for seasonal queries
                                primary_filter = {"travel_month": str(value).lower()}
                                search_params["where"] = primary_filter
                                logger.info(f"🗓️ Using SEASONAL filter: travel_month={value}")
                            elif filter_key == "season":
                                # Use season as fallback for travel_month
                                primary_filter = {"seasonal": str(value).lower()}
                                search_params["where"] = primary_filter
                                logger.info(f"🌸 Using SEASON filter: seasonal={value}")
                            elif filter_key == "category":
                                # Use category for type-specific queries
                                primary_filter = {"category": str(value).lower()}
                                search_params["where"] = primary_filter
                                logger.info(f"🏷️ Using CATEGORY filter: category={value}")
                            elif filter_key == "price_range":
                                # Use price_range for budget queries
                                primary_filter = {"price_range": str(value).lower()}
                                search_params["where"] = primary_filter
                                logger.info(f"💰 Using PRICE filter: price_range={value}")
                            else:
                                # Generic filter handling
                                primary_filter = {filter_key: str(value)}
                                search_params["where"] = primary_filter
                                logger.info(f"🔧 Using GENERIC filter: {filter_key}={value}")
                            break  # Use only ONE filter to avoid ChromaDB limitations
            
            # Execute ChromaDB query
            results = self.collection.query(**search_params)
            
            # Process results with post-processing filtering
            search_results = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    chunk_id = results["ids"][0][i]
                    text = results["documents"][0][i]
                    metadata_dict = results["metadatas"][0][i]
                    similarity_score = 1 / (1 + results["distances"][0][i])  # Convert distance to similarity
                    
                    # Skip results below threshold
                    if similarity_score < query.threshold:
                        continue
                    
                    # Convert to DocumentMetadata
                    try:
                        metadata = DocumentMetadata(**metadata_dict)
                    except Exception as e:
                        # Handle page_number conversion issue
                        if metadata_dict.get("page_number") == "":
                            metadata_dict["page_number"] = None
                        metadata = DocumentMetadata(**metadata_dict)
                    
                    # WEIGHTED SCORING - Apply soft filtering with weighted penalties
                    weighted_score = self._calculate_weighted_score(
                        similarity_score, metadata, query.filters, primary_filter
                    )
                    
                    # Only include results that pass mandatory filters
                    if weighted_score > 0:
                        result = SearchResult(
                            chunk_id=chunk_id,
                            text=text,
                            metadata=metadata,
                            similarity_score=weighted_score  # Use weighted score instead of raw similarity
                        )
                        search_results.append(result)
                        
                        # Stop when we have enough results
                        if len(search_results) >= query.limit:
                            break
            
            # Calculate metrics
            search_time = time.time() - start_time
            
            return SearchResponse(
                results=search_results,
                total_results=len(search_results),
                processing_time=search_time,
                query=query.query
            )
            
        except Exception as e:
            search_time = time.time() - start_time
            return SearchResponse(
                results=[],
                total_results=0,
                processing_time=search_time,
                query=query.query
            )
    
    def _calculate_weighted_score(self, base_similarity: float, metadata: DocumentMetadata, 
                                 filters: Dict[str, Any] = None, primary_filter: Dict[str, str] = None) -> float:
        """
        Calculate weighted score based on filter matching
        
        PRIORITY WEIGHTS:
        - destination: MANDATORY (∞ weight) - must match or score = 0
        - price_range: 0.9 weight (high penalty for mismatch)
        - travel_dates: 0.8 weight (high penalty for mismatch)
        - duration_days: 0.6 weight (medium penalty)
        - category: 0.5 weight (medium penalty)
        - family_friendly: 0.3 weight (low penalty)
        - transport_type: 0.2 weight (low penalty)
        """
        if not filters:
            return base_similarity
        
        # Start with base similarity
        weighted_score = base_similarity
        
        # MANDATORY: Destination must match (handled by ChromaDB primary filter)
        # If destination doesn't match, it shouldn't reach this point
        
        # Apply weighted penalties for other mismatches
        for filter_key, filter_value in filters.items():
            if filter_value is None or filter_value == "" or filter_value == []:
                continue  # Skip empty filters
            
            # Skip filters already handled by ChromaDB
            if primary_filter and filter_key in primary_filter:
                continue
            
            # Get metadata value
            metadata_value = getattr(metadata, filter_key, None)
            
            # Calculate penalty based on filter importance
            penalty = self._get_filter_penalty(filter_key, filter_value, metadata_value)
            
            # Apply penalty to score
            weighted_score *= (1.0 - penalty)
        
        return max(0.0, weighted_score)  # Ensure non-negative score
    
    def _get_filter_penalty(self, filter_key: str, filter_value: Any, metadata_value: Any) -> float:
        """Get penalty for filter mismatch based on filter importance"""
        
        # Define filter weights (penalty when mismatched)
        FILTER_WEIGHTS = {
            'price_range': 0.9,      # High penalty - price is critical
            'travel_month': 0.8,     # High penalty - timing is critical
            'duration_days': 0.6,    # Medium penalty - duration somewhat flexible
            'category': 0.5,         # Medium penalty - category can be flexible
            'family_friendly': 0.3,  # Low penalty - nice to have
            'transport_type': 0.2,   # Low penalty - transport flexible
        }
        
        base_penalty = FILTER_WEIGHTS.get(filter_key, 0.1)  # Default low penalty
        
        # Check if values match
        if self._values_match(filter_key, filter_value, metadata_value):
            return 0.0  # No penalty for match
        
        # Special handling for different filter types
        if filter_key == 'price_range':
            # Smart price penalty - reduce for small differences
            return self._calculate_price_penalty(filter_value, metadata_value, base_penalty)
            
        elif filter_key == 'travel_month':
            # Smart month penalty - reduce for adjacent months
            return self._calculate_month_penalty(filter_value, metadata_value, base_penalty)
            
        elif filter_key == 'duration_days':
            # Duration penalty based on difference
            if isinstance(filter_value, int) and isinstance(metadata_value, int):
                diff = abs(filter_value - metadata_value)
                if diff <= 1:
                    return base_penalty * 0.2  # Small difference, small penalty
                elif diff <= 2:
                    return base_penalty * 0.5  # Medium difference
                else:
                    return base_penalty  # Large difference, full penalty
            return base_penalty
            
        else:
            # Default penalty for mismatch
            return base_penalty
    
    def _values_match(self, filter_key: str, filter_value: Any, metadata_value: Any) -> bool:
        """Check if filter value matches metadata value"""
        
        if metadata_value is None:
            return False
        
        # Handle different data types
        if filter_key in ['duration_days']:
            # Numeric comparison
            try:
                return int(filter_value) == int(metadata_value)
            except (ValueError, TypeError):
                return False
                
        elif filter_key in ['family_friendly']:
            # Boolean comparison
            return bool(filter_value) == bool(metadata_value)
            
        else:
            # String comparison (case insensitive)
            return str(filter_value).lower().strip() == str(metadata_value).lower().strip()
    
    def _calculate_price_penalty(self, filter_value: Any, metadata_value: Any, base_penalty: float) -> float:
        """Calculate smart price penalty - reduce for small differences"""
        if not filter_value or not metadata_value:
            return base_penalty
        
        try:
            # Extract numeric values from price ranges or direct prices
            filter_price = self._extract_price_value(filter_value)
            metadata_price = self._extract_price_value(metadata_value)
            
            if filter_price and metadata_price:
                diff_percent = abs(filter_price - metadata_price) / filter_price
                
                if diff_percent <= 0.1:  # 10% difference
                    return base_penalty * 0.2  # Very small penalty
                elif diff_percent <= 0.25:  # 25% difference  
                    return base_penalty * 0.5  # Medium penalty
                else:
                    return base_penalty  # Full penalty
                    
        except (ValueError, TypeError):
            pass
        
        return base_penalty
    
    def _calculate_month_penalty(self, filter_value: Any, metadata_value: Any, base_penalty: float) -> float:
        """Calculate smart month penalty - reduce for adjacent months"""
        if not filter_value or not metadata_value:
            return base_penalty
        
        # Month order mapping
        MONTH_ORDER = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            # Serbian variants
            'januar': 1, 'februar': 2, 'mart': 3, 'april': 4,
            'maj': 5, 'jun': 6, 'juli': 7, 'avgust': 8,
            'septembar': 9, 'oktobar': 10, 'novembar': 11, 'decembar': 12
        }
        
        try:
            filter_month = MONTH_ORDER.get(str(filter_value).lower())
            metadata_month = MONTH_ORDER.get(str(metadata_value).lower())
            
            if filter_month and metadata_month:
                month_diff = abs(filter_month - metadata_month)
                
                if month_diff == 0:
                    return 0.0  # Perfect match
                elif month_diff == 1:
                    return base_penalty * 0.3  # Adjacent month - small penalty
                elif month_diff == 2:
                    return base_penalty * 0.6  # Close month - medium penalty
                else:
                    return base_penalty  # Distant month - full penalty
                    
        except (ValueError, TypeError):
            pass
        
        return base_penalty
    
    def _extract_price_value(self, price_input: Any) -> Optional[float]:
        """Extract numeric price value from various formats"""
        if isinstance(price_input, (int, float)):
            return float(price_input)
        
        if isinstance(price_input, str):
            # Price range mapping
            price_ranges = {
                'budget': 150,
                'moderate': 350, 
                'expensive': 600,
                'luxury': 1000
            }
            
            if price_input.lower() in price_ranges:
                return price_ranges[price_input.lower()]
            
            # Extract number from string like "500 EUR" or "do 400"
            import re
            numbers = re.findall(r'\d+', price_input)
            if numbers:
                return float(numbers[0])
        
        return None

    def _passes_additional_filters(self, metadata: DocumentMetadata, filters: Dict[str, Any], primary_filter: Dict[str, str] = None) -> bool:
        """
        Apply additional filters that weren't used as primary ChromaDB filter
        """
        # Skip filters that were already applied in ChromaDB
        filters_to_check = filters.copy()
        if primary_filter:
            for key in primary_filter.keys():
                if key in filters_to_check:
                    del filters_to_check[key]
        
        # Check each remaining filter
        for filter_key, filter_value in filters_to_check.items():
            if filter_value is None or filter_value == "" or filter_value == []:
                continue  # Skip empty filters
                
            # Get the corresponding metadata value
            metadata_value = getattr(metadata, filter_key, None)
            
            # Handle different filter types
            if filter_key == "amenities":
                # For amenities, check if all required amenities are present
                if isinstance(filter_value, list) and filter_value:
                    document_amenities = metadata_value or []
                    missing_amenities = [a for a in filter_value if a not in document_amenities]
                    if missing_amenities:
                        return False
                        
            elif filter_key == "price_max":
                # For price_max, check if document price is within limit
                if isinstance(filter_value, (int, float)) and metadata_value:
                    try:
                        doc_price = float(metadata_value)
                        if doc_price > filter_value:
                            return False
                    except (ValueError, TypeError):
                        # Don't reject if we can't parse the price
                        pass
                        
            elif filter_key == "travel_month":
                # For travel_month, this is complex - for now, skip this filter
                continue
                        
            else:
                # For other filters, check exact match
                if str(metadata_value).lower() != str(filter_value).lower():
                    return False
        
        return True
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the document collection"""
        try:
            count = self.collection.count()
            
            # Get some sample metadata to understand the data
            sample_results = self.collection.get(limit=10)
            
            categories = set()
            locations = set()
            
            if sample_results["metadatas"]:
                for metadata in sample_results["metadatas"]:
                    if metadata.get("category"):
                        categories.add(metadata["category"])
                    if metadata.get("location"):
                        locations.add(metadata["location"])
            
            return {
                "total_documents": count,
                "categories": list(categories),
                "locations": list(locations),
                "collection_name": self.collection.name
            }
            
        except Exception as e:
            return {
                "total_documents": 0,
                "categories": [],
                "locations": [],
                "collection_name": "tourism_documents"
            }
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection"""
        try:
            # Delete the collection and recreate it
            self.chroma_client.delete_collection("tourism_documents")
            self.collection = self.chroma_client.create_collection(
                name="tourism_documents",
                metadata={"description": "Tourism documents and arrangements"}
            )
            return True
        except Exception as e:
            return False
    
    def delete_document(self, document_name: str) -> bool:
        """Delete all chunks from a specific document"""
        try:
            # Get all chunks from this document
            results = self.collection.get(
                where={"source_file": document_name}
            )
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                return True
            
            return False
            
        except Exception as e:
            return False 