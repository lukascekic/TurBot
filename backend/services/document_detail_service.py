import logging
from typing import Dict, List, Optional, Any
from services.vector_service import VectorService
from models.document import SearchQuery

logger = logging.getLogger(__name__)

class DocumentDetailService:
    """
    Service for retrieving detailed document content when AI needs 
    comprehensive information about specific arrangements
    """
    
    def __init__(self, vector_service: VectorService):
        self.vector_service = vector_service
        
    def get_detailed_content(self, document_name: str, max_chunks: int = 3) -> Dict[str, Any]:
        """
        Retrieve full content for a specific document when AI needs details
        
        Args:
            document_name: Name of the document to retrieve
            max_chunks: Maximum number of chunks to return
            
        Returns:
            Dictionary with full document content and metadata
        """
        try:
            # Search for chunks from this specific document
            search_query = SearchQuery(
                query="",  # Empty query, we just want document chunks
                filters={"source_file": document_name},
                limit=max_chunks,
                threshold=0.0  # Accept all chunks from this document
            )
            
            # Get all chunks from this document
            search_results = self.vector_service.search(search_query)
            
            if not search_results.results:
                logger.warning(f"No content found for document: {document_name}")
                return {"error": "Document not found"}
            
            # Combine all chunks into comprehensive content
            full_content = ""
            metadata_combined = {}
            
            for result in search_results.results:
                full_content += result.text + "\n\n"
                # Use metadata from first chunk (they should be the same)
                if not metadata_combined:
                    metadata_combined = result.metadata.model_dump()
            
            # Clean and structure the content
            structured_content = self._structure_document_content(full_content)
            
            logger.info(f"Retrieved detailed content for {document_name}: {len(full_content)} characters")
            
            return {
                "document_name": document_name,
                "full_content": full_content,
                "structured_content": structured_content,
                "metadata": metadata_combined,
                "total_chunks": len(search_results.results),
                "content_length": len(full_content)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving detailed content for {document_name}: {e}")
            return {"error": str(e)}
    
    def get_documents_by_criteria(self, criteria: Dict[str, str], max_docs: int = 5) -> List[Dict[str, Any]]:
        """
        Get detailed content for multiple documents matching criteria
        
        Args:
            criteria: Search criteria (destination, category, etc.)
            max_docs: Maximum number of documents to return details for
            
        Returns:
            List of documents with full content
        """
        try:
            # Create broader search to find relevant documents
            query_text = " ".join([f"{k} {v}" for k, v in criteria.items()])
            
            search_query = SearchQuery(
                query=query_text,
                filters=criteria,
                limit=max_docs * 3,  # Get more results to find diverse documents
                threshold=0.1
            )
            
            search_results = self.vector_service.search(search_query)
            
            # Group results by document name
            documents_by_name = {}
            for result in search_results.results:
                doc_name = result.metadata.source_file
                if doc_name not in documents_by_name:
                    documents_by_name[doc_name] = []
                documents_by_name[doc_name].append(result)
            
            # Get detailed content for top documents
            detailed_documents = []
            for doc_name in list(documents_by_name.keys())[:max_docs]:
                doc_detail = self.get_detailed_content(doc_name)
                if "error" not in doc_detail:
                    detailed_documents.append(doc_detail)
            
            logger.info(f"Retrieved detailed content for {len(detailed_documents)} documents")
            return detailed_documents
            
        except Exception as e:
            logger.error(f"Error retrieving documents by criteria: {e}")
            return []
    
    def _structure_document_content(self, content: str) -> Dict[str, Any]:
        """
        Extract structured information from full document content
        
        Args:
            content: Full document text
            
        Returns:
            Structured content with sections identified
        """
        structured = {
            "sections": {},
            "prices": [],
            "dates": [],
            "amenities": [],
            "transport": [],
            "highlights": []
        }
        
        lines = content.split('\n')
        current_section = "general"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section headers
            if any(keyword in line.lower() for keyword in ['program', 'itinerar', 'opis']):
                current_section = "program"
            elif any(keyword in line.lower() for keyword in ['cena', 'cenovnik', 'price']):
                current_section = "pricing"
            elif any(keyword in line.lower() for keyword in ['hotel', 'smeštaj', 'accommodation']):
                current_section = "accommodation"
            elif any(keyword in line.lower() for keyword in ['prevoz', 'transport', 'let']):
                current_section = "transport"
            
            # Add line to appropriate section
            if current_section not in structured["sections"]:
                structured["sections"][current_section] = []
            structured["sections"][current_section].append(line)
            
            # Extract specific information
            # Prices
            import re
            price_pattern = r'(\d+[\.,]?\d*)\s*(EUR|€|din|rsd|\$)'
            prices = re.findall(price_pattern, line, re.IGNORECASE)
            for price, currency in prices:
                structured["prices"].append(f"{price} {currency}")
            
            # Dates
            date_pattern = r'(\d{1,2}[\./]\d{1,2}[\./]\d{4})|(\d{1,2}[\./]\d{1,2})'
            dates = re.findall(date_pattern, line)
            for date_match in dates:
                date = date_match[0] or date_match[1]
                if date:
                    structured["dates"].append(date)
            
            # Amenities
            amenity_keywords = ['spa', 'bazen', 'wifi', 'parking', 'klima', 'restoran', 'bar', 'fitness']
            for keyword in amenity_keywords:
                if keyword in line.lower() and keyword not in structured["amenities"]:
                    structured["amenities"].append(keyword)
        
        return structured
    
    def should_fetch_detailed_content(self, user_query: str, ai_response: str) -> bool:
        """
        Determine if we should fetch detailed content based on user query
        
        Args:
            user_query: User's question
            ai_response: AI's current response
            
        Returns:
            True if detailed content would help answer the question
        """
        # Detailed content triggers
        detail_keywords = [
            'datumi', 'datum', 'kada', 'koji dani',
            'detaljno', 'više informacija', 'specifično',
            'polazak', 'povratak', 'trajanje',
            'šta je uključeno', 'program', 'itinerar',
            'cene', 'košta', 'additional', 'extra'
        ]
        
        # Response inadequacy indicators
        inadequate_indicators = [
            'nemam informacije', 'nije dostupno',
            'molim kontaktirajte', 'za više detalja',
            'dodatne informacije'
        ]
        
        query_needs_details = any(keyword in user_query.lower() for keyword in detail_keywords)
        response_inadequate = any(indicator in ai_response.lower() for indicator in inadequate_indicators)
        
        return query_needs_details or response_inadequate 