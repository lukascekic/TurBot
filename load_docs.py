from backend.services.document_service import DocumentService
from dotenv import load_dotenv
import time

load_dotenv()
print(" Loading documents into NEW database...")
start_time = time.time()

doc_service = DocumentService()
results = doc_service.process_documents_directory("ulazni-podaci")

successful = [r for r in results if r.processing_status == "success"]
failed = [r for r in results if r.processing_status == "error"]

elapsed = time.time() - start_time
print(f" Processed: {len(successful)}/{len(results)} documents in {elapsed:.1f}s")

if failed:
    print(f" Failed: {len(failed)}")
    for f in failed[:3]:
        print(f"  - {f.filename}: {f.error_message}")

stats = doc_service.get_database_stats()
print(f" Final: {stats[\"total_documents\"]} chunks")
print(f" Categories: {stats[\"categories\"]}")
print(f" Locations: {stats[\"locations\"]}")

