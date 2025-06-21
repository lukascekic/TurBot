import chromadb
from chromadb.config import Settings
import openai
from typing import List, Dict, Any, Optional
import os
import time
from pathlib import Path

from models.document import DocumentChunk, SearchQuery, SearchResult, SearchResponse, DocumentMetadata


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
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error creating embedding: {e}")
            raise
    
    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts in batch"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Error creating batch embeddings: {e}")
            raise
    
    def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """Add document chunks to the vector database"""
        try:
            if not chunks:
                return True
            
            # Extract texts for embedding
            texts = [chunk.text for chunk in chunks]
            
            # Create embeddings in batch for efficiency
            embeddings = self.create_embeddings_batch(texts)
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            chunk_embeddings = []
            
            for i, chunk in enumerate(chunks):
                ids.append(chunk.id)
                documents.append(chunk.text)
                
                # Convert metadata to dict, handling None values
                metadata_dict = chunk.metadata.model_dump()
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
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=chunk_embeddings
            )
            
            return True
            
        except Exception as e:
            print(f"Error adding documents to vector DB: {e}")
            return False
    
    def search(self, query: SearchQuery) -> SearchResponse:
        """Search for similar documents"""
        start_time = time.time()
        
        try:
            # Create embedding for the query
            query_embedding = self.create_embedding(query.query)
            
            # Prepare ChromaDB query parameters
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": query.limit
            }
            
            # Add metadata filters if provided
            if query.filters:
                # Convert filters to ChromaDB format
                where_clause = {}
                for key, value in query.filters.items():
                    if value and value != "":  # Skip empty filters
                        where_clause[key] = value
                
                if where_clause:
                    search_params["where"] = where_clause
            
            # Perform search
            results = self.collection.query(**search_params)
            
            # Process results
            search_results = []
            if results["documents"] and results["documents"][0]:  # Check if we have results
                for i in range(len(results["documents"][0])):
                    # Extract data for this result
                    chunk_id = results["ids"][0][i]
                    text = results["documents"][0][i]
                    metadata_dict = results["metadatas"][0][i]
                    distance = results["distances"][0][i] if "distances" in results else 0
                    
                    # Convert distance to similarity score
                    # For cosine distance, use: 1 - (distance / 2) to normalize to 0-1 range
                    # Or use inverse distance: 1 / (1 + distance)
                    similarity_score = 1 / (1 + distance)
                    
                    # Skip results below threshold
                    if similarity_score < query.threshold:
                        continue
                    
                    # Convert metadata dict back to DocumentMetadata
                    # Handle page_number conversion properly 
                    if "page_number" in metadata_dict:
                        page_num = metadata_dict["page_number"]
                        if page_num == 0 or page_num == "" or page_num == "0":
                            metadata_dict["page_number"] = None
                        elif isinstance(page_num, str) and page_num.isdigit():
                            metadata_dict["page_number"] = int(page_num)
                    
                    metadata = DocumentMetadata(**metadata_dict)
                    
                    result = SearchResult(
                        chunk_id=chunk_id,
                        text=text,
                        metadata=metadata,
                        similarity_score=similarity_score
                    )
                    search_results.append(result)
            
            processing_time = time.time() - start_time
            
            return SearchResponse(
                query=query.query,
                results=search_results,
                total_results=len(search_results),
                processing_time=processing_time
            )
            
        except Exception as e:
            print(f"Error during search: {e}")
            processing_time = time.time() - start_time
            return SearchResponse(
                query=query.query,
                results=[],
                total_results=0,
                processing_time=processing_time
            )
    
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
            print(f"Error getting collection stats: {e}")
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
            print(f"Error clearing collection: {e}")
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
            print(f"Error deleting document {document_name}: {e}")
            return False 