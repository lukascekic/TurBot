#!/usr/bin/env python3
"""
Database Metadata Fix Script

This script identifies and fixes wrong location assignments in ChromaDB.
Specifically targets the French and Portuguese documents that were incorrectly labeled as location="Rim".
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vector_service import VectorService
from collections import Counter

def main():
    print("🔧 DATABASE METADATA FIX")
    print("=" * 50)
    
    # Initialize vector service
    vector_service = VectorService()
    
    # Get all documents from ChromaDB
    print("1️⃣ Analyzing current database state...")
    try:
        all_results = vector_service.collection.get()
        total_docs = len(all_results['ids'])
        print(f"   Total documents in DB: {total_docs}")
        
        if total_docs == 0:
            print("   ❌ No documents found in database!")
            return
            
    except Exception as e:
        print(f"   ❌ Error fetching documents: {e}")
        return
    
    # Analyze current locations
    locations = [meta.get('location', 'NO_LOCATION') for meta in all_results['metadatas']]
    location_counts = Counter(locations)
    
    print(f"   Current location distribution:")
    for location, count in location_counts.most_common():
        print(f"     • '{location}': {count} documents")
    
    # Identify problematic documents
    print("\n2️⃣ Identifying documents with wrong location metadata...")
    
    # Define expected location mappings based on filename patterns
    filename_to_location_fixes = {
        'product_be_unique_ROMANTICNA_FRANCUSKA_5.pdf': 'Pariz',
        'Portugalska_tura_Lisabon_i_Porto': 'Lisabon',
        # Add more problematic files as discovered
    }
    
    fixes_needed = []
    
    for i, (doc_id, metadata) in enumerate(zip(all_results['ids'], all_results['metadatas'])):
        source_file = metadata.get('source_file', '')
        current_location = metadata.get('location', '')
        
        # Check if this file needs location fix
        for filename_pattern, correct_location in filename_to_location_fixes.items():
            if filename_pattern in source_file and current_location != correct_location:
                fixes_needed.append({
                    'doc_id': doc_id,
                    'source_file': source_file,
                    'current_location': current_location,
                    'correct_location': correct_location,
                    'metadata': metadata
                })
                break
    
    print(f"   Found {len(fixes_needed)} documents needing location fixes:")
    for fix in fixes_needed:
        print(f"     • {fix['source_file'][:50]}...")
        print(f"       Current: '{fix['current_location']}' → Correct: '{fix['correct_location']}'")
    
    if not fixes_needed:
        print("   ✅ No location fixes needed!")
        return
    
    # Apply fixes
    print(f"\n3️⃣ Applying {len(fixes_needed)} location fixes...")
    
    try:
        for fix in fixes_needed:
            # Update metadata
            updated_metadata = fix['metadata'].copy()
            updated_metadata['location'] = fix['correct_location']
            
            # Update in ChromaDB
            vector_service.collection.update(
                ids=[fix['doc_id']],
                metadatas=[updated_metadata]
            )
            
            print(f"   ✅ Fixed: {fix['source_file'][:40]}... → {fix['correct_location']}")
        
        print(f"\n   🎉 Successfully applied {len(fixes_needed)} fixes!")
        
    except Exception as e:
        print(f"   ❌ Error applying fixes: {e}")
        return
    
    # Verify fixes
    print("\n4️⃣ Verifying fixes...")
    
    try:
        # Get updated data
        updated_results = vector_service.collection.get()
        updated_locations = [meta.get('location', 'NO_LOCATION') for meta in updated_results['metadatas']]
        updated_location_counts = Counter(updated_locations)
        
        print(f"   Updated location distribution:")
        for location, count in updated_location_counts.most_common():
            print(f"     • '{location}': {count} documents")
        
        # Test specific queries
        print("\n5️⃣ Testing fixed queries...")
        
        test_cases = [
            ("Rim", "Should return only Rome documents"),
            ("Pariz", "Should return French documents"),
            ("Lisabon", "Should return Portuguese documents")
        ]
        
        for location, description in test_cases:
            try:
                location_docs = vector_service.collection.get(where={"location": location})
                count = len(location_docs['ids'])
                print(f"   • {location}: {count} documents ({description})")
                
                if count > 0:
                    # Show first few sources
                    sources = [meta.get('source_file', 'NO_SOURCE')[:50] for meta in location_docs['metadatas'][:3]]
                    print(f"     Sources: {sources}")
                    
            except Exception as e:
                print(f"   ❌ Error testing {location}: {e}")
        
        print("\n" + "=" * 50)
        print("🏁 DATABASE CLEANUP COMPLETE")
        print("\nNext steps:")
        print("1. Run test queries to verify search results are correct")
        print("2. Test full RAG pipeline with problematic queries")
        print("3. Monitor for any remaining location issues")
        
    except Exception as e:
        print(f"   ❌ Error verifying fixes: {e}")

if __name__ == "__main__":
    main() 