#!/usr/bin/env python3
"""
Bulk load PDF documents script
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

def main():
    print('🚀 Starting bulk PDF processing...')
    start_time = time.time()
    
    doc_service = DocumentService()
    
    # Check multiple possible directories for PDF files
    possible_dirs = [
        '../ulazni-podaci',  # From app/ to ulazni-podaci/
        '../../ulazni-podaci',  # Correct path according to user
        '../../data/Ulazni podaci-20250621T091254Z-1-001/Ulazni podaci',
        '../../../ulazni-podaci',
    ]
    
    pdf_dir = None
    for dir_path in possible_dirs:
        if os.path.exists(dir_path):
            pdf_files = [f for f in os.listdir(dir_path) if f.endswith('.pdf')]
            if pdf_files:
                pdf_dir = dir_path
                print(f'✅ Found PDF directory: {pdf_dir} with {len(pdf_files)} files')
                break
    
    if pdf_dir is None:
        print('❌ PDF directory not found in any of these locations:')
        for dir_path in possible_dirs:
            print(f'   - {dir_path}')
        return False
    
    if os.path.exists(pdf_dir):
        print(f'📁 Processing PDFs from: {pdf_dir}')
        results = doc_service.process_documents_directory(pdf_dir)
        
        successful = len([r for r in results if r.processing_status == 'success'])
        total = len(results)
        processing_time = time.time() - start_time
        
        print(f'\n📊 RESULTS: {successful}/{total} PDFs processed successfully')
        print(f'⏱️ Processing time: {processing_time:.1f} seconds')
        
        # Show some stats
        stats = doc_service.get_database_stats()
        print(f'\n📈 Database now contains {stats["total_documents"]} chunks')
        print(f'📂 Categories: {stats["categories"]}')
        print(f'🏙️ Locations: {stats["locations"]}')
        
        # Show some failed docs if any
        failed = [r for r in results if r.processing_status == 'error']
        if failed:
            print(f'\n❌ Failed documents ({len(failed)}):')
            for doc in failed[:5]:  # Show first 5 failures
                print(f'  - {doc.filename}: {doc.error_message}')
        
        return successful == total
        
    else:
        print(f'❌ PDF directory not found: {pdf_dir}')
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 