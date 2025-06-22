#!/usr/bin/env python3
"""
Database Migration Script - Enhanced Metadata with GPT-4o-mini

This script migrates the existing ChromaDB database to use enhanced metadata
extracted with GPT-4o-mini for maximum precision.

USAGE:
python migrate_database_metadata.py --mode=preview  # Preview changes
python migrate_database_metadata.py --mode=migrate  # Apply migration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import argparse
import logging
from typing import Dict, List, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from services.vector_service import VectorService
from services.metadata_enhancement_service import MetadataEnhancementService
from models.document import DocumentMetadata

class DatabaseMigrator:
    """Migrate database to enhanced metadata format"""
    
    def __init__(self):
        self.vector_service = VectorService()
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.metadata_service = MetadataEnhancementService(self.client)
        
    async def preview_migration(self):
        """Preview what changes would be made without applying them"""
        print("🔍 PREVIEWING DATABASE MIGRATION")
        print("=" * 60)
        
        # Get all documents
        all_results = self.vector_service.collection.get()
        total_docs = len(all_results['ids'])
        
        print(f"📊 Total documents in database: {total_docs}")
        print()
        
        # Analyze current metadata
        current_metadata = self._analyze_current_metadata(all_results)
        print("📋 CURRENT METADATA ANALYSIS:")
        print("-" * 40)
        for field, stats in current_metadata.items():
            print(f"  {field}: {stats}")
        print()
        
        # Sample some documents for enhancement preview
        sample_size = min(5, total_docs)
        print(f"🧪 SAMPLE ENHANCEMENT PREVIEW ({sample_size} documents):")
        print("-" * 50)
        
        for i in range(sample_size):
            doc_id = all_results['ids'][i]
            content = all_results['documents'][i]
            current_meta = all_results['metadatas'][i]
            
            print(f"\n📄 Document {i+1}: {doc_id[:20]}...")
            print(f"   Current location: {current_meta.get('location', 'None')}")
            print(f"   Current category: {current_meta.get('category', 'None')}")
            
            # Preview enhanced metadata
            try:
                enhanced_meta = await self.metadata_service.enhance_document_metadata(
                    content[:1000], current_meta.get('source_file', 'unknown')
                )
                print(f"   → Enhanced destination: {enhanced_meta.destination}")
                print(f"   → Enhanced category: {enhanced_meta.category}")
                print(f"   → Duration: {enhanced_meta.duration_days} days")
                print(f"   → Transport: {enhanced_meta.transport_type}")
                print(f"   → Confidence: {enhanced_meta.confidence_score:.2f}")
                
            except Exception as e:
                print(f"   ❌ Enhancement failed: {e}")
        
        print("\n" + "=" * 60)
        print("✅ PREVIEW COMPLETE - Use --mode=migrate to apply changes")
    
    async def migrate_database(self):
        """Apply the migration to enhance all metadata"""
        print("🚀 STARTING DATABASE MIGRATION")
        print("=" * 60)
        
        # Get all documents
        all_results = self.vector_service.collection.get()
        total_docs = len(all_results['ids'])
        
        print(f"📊 Migrating {total_docs} documents...")
        print()
        
        # Track migration progress
        success_count = 0
        error_count = 0
        updates_made = []
        
        for i in range(total_docs):
            doc_id = all_results['ids'][i]
            content = all_results['documents'][i]
            current_meta = all_results['metadatas'][i]
            
            print(f"🔄 Processing {i+1}/{total_docs}: {doc_id[:30]}...")
            
            try:
                # Enhance metadata with GPT-4o-mini
                enhanced_meta = await self.metadata_service.enhance_document_metadata(
                    content, current_meta.get('source_file', 'unknown')
                )
                
                # Convert to dict for ChromaDB
                enhanced_dict = enhanced_meta.model_dump()
                
                # Clean None values for ChromaDB
                cleaned_meta = {}
                for k, v in enhanced_dict.items():
                    if k == "page_number":
                        cleaned_meta[k] = v if v is not None else 0
                    else:
                        cleaned_meta[k] = v if v is not None else ""
                
                # Update in ChromaDB
                self.vector_service.collection.update(
                    ids=[doc_id],
                    metadatas=[cleaned_meta]
                )
                
                # Track changes
                changes = self._track_changes(current_meta, cleaned_meta)
                if changes:
                    updates_made.append({
                        'doc_id': doc_id,
                        'changes': changes
                    })
                
                success_count += 1
                print(f"   ✅ Enhanced: {enhanced_meta.destination} | {enhanced_meta.category}")
                
            except Exception as e:
                error_count += 1
                print(f"   ❌ Failed: {e}")
                continue
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 MIGRATION SUMMARY:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {error_count}")
        print(f"   📝 Documents with changes: {len(updates_made)}")
        
        if updates_made:
            print("\n🔄 KEY CHANGES MADE:")
            for update in updates_made[:10]:  # Show first 10
                print(f"   📄 {update['doc_id'][:20]}...")
                for change in update['changes'][:3]:  # Show first 3 changes
                    print(f"      {change}")
        
        print("\n✅ MIGRATION COMPLETE!")
    
    def _analyze_current_metadata(self, all_results: Dict) -> Dict[str, Dict]:
        """Analyze current metadata distribution"""
        analysis = {}
        
        # Count field usage
        for field in ['location', 'category', 'price_range', 'family_friendly']:
            values = [meta.get(field) for meta in all_results['metadatas']]
            non_empty = [v for v in values if v and v != ""]
            unique_values = set(non_empty)
            
            analysis[field] = {
                'total': len(values),
                'non_empty': len(non_empty),
                'unique_values': len(unique_values),
                'coverage': f"{len(non_empty)/len(values)*100:.1f}%",
                'values': list(unique_values)[:5]  # First 5 unique values
            }
        
        return analysis
    
    def _track_changes(self, old_meta: Dict, new_meta: Dict) -> List[str]:
        """Track what changes were made"""
        changes = []
        
        # Key fields to track
        key_fields = ['destination', 'location', 'category', 'duration_days', 'transport_type']
        
        for field in key_fields:
            old_val = old_meta.get(field)
            new_val = new_meta.get(field)
            
            if old_val != new_val and new_val and new_val != "":
                changes.append(f"{field}: '{old_val}' → '{new_val}'")
        
        return changes

async def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Migrate database to enhanced metadata')
    parser.add_argument('--mode', choices=['preview', 'migrate'], required=True,
                       help='Mode: preview changes or apply migration')
    
    args = parser.parse_args()
    
    migrator = DatabaseMigrator()
    
    if args.mode == 'preview':
        await migrator.preview_migration()
    elif args.mode == 'migrate':
        # Confirmation for actual migration
        print("⚠️  WARNING: This will modify all documents in the database!")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() == 'yes':
            await migrator.migrate_database()
        else:
            print("❌ Migration cancelled")

if __name__ == "__main__":
    asyncio.run(main()) 