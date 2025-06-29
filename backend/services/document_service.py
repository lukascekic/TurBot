from typing import List, Dict, Any, Optional, BinaryIO
from pathlib import Path
import shutil
import tempfile
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
import logging

from services.pdf_processor import PDFProcessor
from services.vector_service import VectorService
from models.document import ProcessedDocument, SearchQuery, SearchResponse

# Load environment variables
load_dotenv()

# Configure detailed logging
logger = logging.getLogger(__name__)

class DocumentService:
    """Service for managing document upload, processing, and search"""
    
    def __init__(self):
        logger.info("🚀 Initializing DocumentService...")
        
        # Initialize OpenAI client for enhanced metadata
        openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize services with enhanced metadata support
        self.pdf_processor = PDFProcessor(openai_client=openai_client)
        self.vector_service = VectorService()
        
        # Create uploads directory if it doesn't exist
        self.uploads_dir = Path("./uploads")
        self.uploads_dir.mkdir(exist_ok=True)
        
        logger.info("✅ DocumentService initialized successfully")
    
    def process_and_store_pdf(self, file_path: str) -> ProcessedDocument:
        """Process a PDF file and store chunks in vector database"""
        logger.info(f"📁 Starting processing for: {file_path}")
        
        # Process PDF into chunks
        processed_doc = self.pdf_processor.process_pdf(file_path)
        logger.info(f"📊 PDF processing result: {processed_doc.processing_status}, {processed_doc.total_chunks} chunks")
        
        if processed_doc.processing_status == "success" and processed_doc.chunks:
            logger.info(f"💾 Storing {len(processed_doc.chunks)} chunks in vector database...")
            
            # Store chunks in vector database
            success = self.vector_service.add_documents(processed_doc.chunks)
            logger.info(f"💾 Vector storage result: {'✅ Success' if success else '❌ Failed'}")
            
            if not success:
                processed_doc.processing_status = "error"
                processed_doc.error_message = "Failed to store chunks in vector database"
                logger.error(f"❌ Failed to store chunks for {file_path}")
        else:
            logger.warning(f"⚠️ PDF processing failed or no chunks created for {file_path}")
        
        return processed_doc
    
    def upload_and_process_pdf(self, file_content: bytes, filename: str) -> ProcessedDocument:
        """Upload a PDF file and process it"""
        try:
            # Save uploaded file temporarily
            temp_path = self.uploads_dir / filename
            
            with open(temp_path, "wb") as f:
                f.write(file_content)
            
            # Process the PDF
            processed_doc = self.process_and_store_pdf(str(temp_path))
            
            # Keep the file if processing was successful
            if processed_doc.processing_status != "success":
                # Remove file if processing failed
                if temp_path.exists():
                    temp_path.unlink()
            
            return processed_doc
            
        except Exception as e:
            return ProcessedDocument(
                filename=filename,
                chunks=[],
                total_chunks=0,
                processing_status="error",
                error_message=f"Upload failed: {str(e)}"
            )
    
    def process_documents_directory(self, directory_path: str) -> List[ProcessedDocument]:
        """Process all PDF files in a directory"""
        logger.info(f"📂 Starting bulk processing of directory: {directory_path}")
        results = []
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.error(f"❌ Directory does not exist: {directory_path}")
            return results
        
        # Find all PDF files
        pdf_files = list(directory.glob("**/*.pdf"))
        logger.info(f"📋 Found {len(pdf_files)} PDF files to process")
        
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"🔄 Processing file {i}/{len(pdf_files)}: {pdf_file.name}")
            processed_doc = self.process_and_store_pdf(str(pdf_file))
            results.append(processed_doc)
            
            if processed_doc.processing_status == "success":
                logger.info(f"✅ Successfully processed {pdf_file.name}")
            else:
                logger.error(f"❌ Failed to process {pdf_file.name}: {processed_doc.error_message}")
        
        # Summary
        successful = len([r for r in results if r.processing_status == 'success'])
        logger.info(f"🎉 Bulk processing complete: {successful}/{len(results)} files processed successfully")
        
        return results
    
    def search_documents(self, query: str, filters: Optional[Dict[str, Any]] = None, 
                        limit: int = 10) -> SearchResponse:
        """Search documents using semantic search"""
        search_query = SearchQuery(
            query=query,
            filters=filters,
            limit=limit
        )
        
        return self.vector_service.search(search_query)
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the document database"""
        return self.vector_service.get_collection_stats()
    
    def clear_database(self) -> bool:
        """Clear all documents from the database"""
        return self.vector_service.clear_collection()
    
    def remove_document(self, filename: str) -> bool:
        """Remove a document from the database and storage"""
        # Remove from vector database
        success = self.vector_service.delete_document(filename)
        
        # Remove from storage
        file_path = self.uploads_dir / filename
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                pass
        
        return success
    
    def list_uploaded_documents(self) -> List[str]:
        """List all uploaded PDF documents"""
        return [f.name for f in self.uploads_dir.glob("*.pdf")]
    
    def get_document_info(self, filename: str) -> Dict[str, Any]:
        """Get information about a specific document"""
        file_path = self.uploads_dir / filename
        
        if not file_path.exists():
            return {"error": "Document not found"}
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Get chunks count from vector database
        try:
            results = self.vector_service.collection.get(
                where={"source_file": filename}
            )
            chunks_count = len(results["ids"]) if results["ids"] else 0
            
            return {
                "filename": filename,
                "file_size": file_size,
                "chunks_count": chunks_count,
                "exists_in_db": chunks_count > 0
            }
        except Exception as e:
            return {
                "filename": filename,
                "file_size": file_size,
                "chunks_count": 0,
                "exists_in_db": False,
                "error": str(e)
            } 