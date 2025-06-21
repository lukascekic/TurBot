#!/usr/bin/env python3
"""
Test search functionality with real data - FULL CHUNK CONTENT VIEW
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import time
from dotenv import load_dotenv

# Load environment variables first!
load_dotenv()

from services.document_service import DocumentService

def test_search_queries_full_content():
    """Test search queries with full chunk content display"""
    doc_service = DocumentService()
    
    # Reduced set of test queries for detailed analysis
    test_queries = [
        ("hotel u Rimu", "Traži hotelе u Rimu"),
        ("Istanbul putovanje", "Traži putovanja u Istanbul"),
        ("Amsterdam aranžman", "Traži aranžmane za Amsterdam"),
    ]
    
    print("🔍 Search Test with Full Chunk Content\n")
    print("=" * 90)
    
    for i, (query, description) in enumerate(test_queries, 1):
        print(f"\n{i}. {description}")
        print(f"   Query: '{query}'")
        print("-" * 90)
        
        start_time = time.time()
        results = doc_service.search_documents(query, limit=2)  # Reduced to 2 results
        search_time = time.time() - start_time
        
        print(f"   📊 Found {results.total_results} results in {search_time:.2f}s")
        
        if results.results:
            for j, result in enumerate(results.results, 1):
                print(f"\n   📄 RESULT {j}:")
                print(f"   └─ Score: {result.similarity_score:.3f}")
                print(f"   └─ Source: {result.metadata.source_file}")
                print(f"   └─ Location: {result.metadata.location or 'N/A'}")
                print(f"   └─ Category: {result.metadata.category or 'N/A'}")
                print(f"   └─ Price Range: {result.metadata.price_range or 'N/A'}")
                print()
                print("   💬 FULL CHUNK TEXT:")
                print("   " + "▼" * 85)
                
                # Display full chunk with proper formatting
                chunk_lines = result.text.split('\n')
                for line in chunk_lines:
                    if line.strip():  # Skip empty lines
                        # Word wrap for better readability
                        if len(line) > 80:
                            words = line.split()
                            current_line = ""
                            for word in words:
                                if len(current_line + word) > 80:
                                    print(f"   │ {current_line}")
                                    current_line = word + " "
                                else:
                                    current_line += word + " "
                            if current_line.strip():
                                print(f"   │ {current_line}")
                        else:
                            print(f"   │ {line}")
                    else:
                        print("   │")  # Preserve empty lines
                
                print("   " + "▲" * 85)
                print()
        else:
            print("     ❌ No results found")
        
        print("\n" + "=" * 90)

def test_search_queries_brief():
    """Brief version of search test (original functionality)"""
    doc_service = DocumentService()
    
    # More queries for quick overview
    test_queries = [
        ("hotel u Rimu", "Traži hotelе u Rimu"),
        ("aranžman za Amsterdam", "Traži aranžmane za Amsterdam"),
        ("putovanje avionom", "Traži putovanja avionom"),
        ("cena smeštaja", "Traži informacije o cenama"),
        ("letovanje na moru", "Traži letovanja"),
        ("tura po Evropi", "Traži evropske ture"),
        ("Istanbul putovanje", "Traži putovanja u Istanbul"),
        ("Maroko aranžman", "Traži aranžmane za Maroko"),
    ]
    
    print("🔍 Brief Search Test (Original)\n")
    
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
    print("🚀 TurBot Search Test - Enhanced Version\n")
    
    # Show database stats
    test_database_stats()
    print()
    
    # Ask user which test to run
    print("Choose test mode:")
    print("1. Full chunk content view (detailed, slower)")
    print("2. Brief overview (quick, original)")
    print("3. Both tests")
    
    choice = input("\nEnter choice (1-3) or press Enter for full content: ").strip()
    
    if choice == "2":
        test_search_queries_brief()
    elif choice == "3":
        test_search_queries_full_content()
        print("\n" + "="*50 + " BRIEF TEST " + "="*50)
        test_search_queries_brief()
    else:
        # Default to full content view
        test_search_queries_full_content()
    
    print("\n✅ Search testing completed!") 