#!/usr/bin/env python3
"""
Simple search test with broader terms
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import time
from dotenv import load_dotenv

load_dotenv()

from services.document_service import DocumentService

def test_simple_searches():
    doc_service = DocumentService()
    
    # Simple broad terms that should match content
    simple_queries = [
        "Istanbul",
        "avion",
        "hotel", 
        "cena",
        "putovanje",
        "Amsterdam",
        "Rim",
        "Maroko",
        "noćenje",
        "avio",
        "Turska",
        "noći"
    ]
    
    print("🔍 Simple Search Tests\n")
    
    for query in simple_queries:
        print(f"Query: '{query}'")
        results = doc_service.search_documents(query, limit=2)
        print(f"  📊 Found {results.total_results} results")
        
        if results.results:
            for i, result in enumerate(results.results, 1):
                preview = result.text[:60] + "..." if len(result.text) > 60 else result.text
                print(f"    {i}. Score: {result.similarity_score:.3f} | {preview}")
        print()

if __name__ == "__main__":
    test_simple_searches() 