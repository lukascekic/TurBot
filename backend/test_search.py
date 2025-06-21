#!/usr/bin/env python3
"""
Test search functionality with real data
"""

import os
import time
from dotenv import load_dotenv

# Load environment variables first!
load_dotenv()

from services.document_service import DocumentService

def test_search_queries():
    """Test various search queries"""
    doc_service = DocumentService()
    
    # Test queries
    test_queries = [
        ("hotel u Rimu", "Traži hotelе u Rimu"),
        ("aranžman za Amsterdаm", "Traži aranžmane za Amsterdam"),
        ("putovanje avionom", "Traži putovanja avionom"),
        ("cena smeštaja", "Traži informacije o cenama"),
        ("letovanje na moru", "Traži letovanja"),
        ("tura po Evropi", "Traži evropske ture"),
        ("Istanbul putovanje", "Traži putovanja u Istanbul"),
        ("Maroko aranžman", "Traži aranžmane za Maroko"),
    ]
    
    print("🔍 Testing Search Functionality\n")
    
    for i, (query, description) in enumerate(test_queries, 1):
        print(f"{i}. {description}")
        print(f"   Query: '{query}'")
        
        start_time = time.time()
        results = doc_service.search_documents(query, limit=3)
        search_time = time.time() - start_time
        
        print(f"   📊 Found {results.total_results} results in {search_time:.2f}s")
        
        if results.results:
            for j, result in enumerate(results.results, 1):
                preview = result.text[:80] + "..." if len(result.text) > 80 else result.text
                print(f"     {j}. Score: {result.similarity_score:.3f} | {preview}")
                print(f"        📄 Source: {result.metadata.source_file}")
                if result.metadata.location:
                    print(f"        📍 Location: {result.metadata.location}")
                if result.metadata.category:
                    print(f"        🏷️ Category: {result.metadata.category}")
        else:
            print("     ❌ No results found")
        
        print()

def test_database_stats():
    """Show database statistics"""
    doc_service = DocumentService()
    stats = doc_service.get_database_stats()
    
    print("📊 Database Statistics:")
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   Categories: {stats['categories']}")
    print(f"   Locations: {stats['locations']}")
    print(f"   Collection: {stats['collection_name']}")

if __name__ == "__main__":
    print("🚀 TurBot Search Test\n")
    
    test_database_stats()
    print()
    test_search_queries()
    
    print("✅ Search testing completed!") 