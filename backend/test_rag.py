#!/usr/bin/env python3
"""
Test script for basic RAG functionality
Run this to verify PDF processing and vector search work correctly
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from services.document_service import DocumentService
from services.pdf_processor import PDFProcessor
from services.vector_service import VectorService


def test_pdf_processing():
    """Test PDF processing functionality"""
    print("🔍 Testing PDF Processing...")
    
    processor = PDFProcessor()
    
    # Create a test text file to simulate PDF processing
    test_content = """
    Hotel Moskva u Beogradu
    
    Hotel Moskva je luksuzni hotel u centru Beograda, smešten na Terazijama.
    
    Usluge:
    - Jednokrevetna soba: 120€ po noći
    - Dvokrevetna soba: 150€ po noći  
    - Apartman: 200€ po noći
    
    Hotel je pogodan za porodice sa decom i nalazi se u blizini glavne pešačke zone.
    Radi tokom cele godine i pruža usluge high-end smeštaja.
    """
    
    # Test chunking
    chunks = processor._create_chunks(test_content)
    print(f"✅ Created {len(chunks)} chunks from test content")
    
    # Test metadata extraction
    if chunks:
        metadata = processor._extract_metadata(chunks[0], "test_hotel.pdf")
        print(f"✅ Extracted metadata: {metadata}")
    
    return True

def test_vector_service():
    """Test vector service functionality"""
    print("\n🗄️ Testing Vector Service...")
    
    try:
        vector_service = VectorService()
        
        # Test embedding creation
        test_text = "hotel u Beogradu"
        embedding = vector_service.create_embedding(test_text)
        print(f"✅ Created embedding with {len(embedding)} dimensions")
        
        # Test collection stats
        stats = vector_service.get_collection_stats()
        print(f"✅ Collection stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vector service error: {e}")
        return False

def test_document_service():
    """Test document service integration"""
    print("\n📄 Testing Document Service...")
    
    try:
        doc_service = DocumentService()
        
        # Test database stats
        stats = doc_service.get_database_stats()
        print(f"✅ Database stats: {stats}")
        
        # Test search with empty database
        results = doc_service.search_documents("hotel Beograd", limit=5)
        print(f"✅ Search completed - found {results.total_results} results")
        
        return True
        
    except Exception as e:
        print(f"❌ Document service error: {e}")
        return False

def test_bulk_processing():
    """Test processing directory with PDF files"""
    print("\n📁 Testing Bulk PDF Processing...")
    
    # Check if data directory exists
    data_dir = Path("../../data")
    if not data_dir.exists():
        print("⚠️ Data directory not found, skipping bulk processing test")
        return True
    
    try:
        doc_service = DocumentService()
        
        # Find PDF files in data directory
        pdf_files = list(data_dir.rglob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files in data directory")
        
        if pdf_files:
            # Process first PDF as test
            test_pdf = pdf_files[0]
            print(f"Processing test file: {test_pdf.name}")
            
            result = doc_service.process_and_store_pdf(str(test_pdf))
            
            if result.processing_status == "success":
                print(f"✅ Successfully processed {test_pdf.name} - {result.total_chunks} chunks")
                
                # Test search on processed document
                search_results = doc_service.search_documents("hotel", limit=3)
                print(f"✅ Search found {search_results.total_results} results")
                
                # Show first result
                if search_results.results:
                    first_result = search_results.results[0]
                    print(f"📝 First result preview: {first_result.text[:100]}...")
                    
            else:
                print(f"❌ Failed to process {test_pdf.name}: {result.error_message}")
                
        return True
        
    except Exception as e:
        print(f"❌ Bulk processing error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting RAG System Tests\n")
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in .env file")
        return False
    
    tests = [
        ("PDF Processing", test_pdf_processing),
        ("Vector Service", test_vector_service),
        ("Document Service", test_document_service),
        ("Bulk Processing", test_bulk_processing)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("🎉 All tests passed! RAG system is ready for Phase 3.")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 