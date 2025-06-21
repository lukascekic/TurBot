# 🧪 TurBot - Lokalno Testiranje sa PDF Fajlovima

## 📋 Pre Testiranja - Checklist

### 1. Environment Setup
```bash
# Proveri da li si u backend direktorijumu
cd app/backend

# Aktiviraj virtual environment
venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate  # Linux/Mac

# Proveri instalacije
pip list | findstr "chromadb\|pdfplumber\|openai"
```

### 2. Environment Variables
```bash
# Proveri da li postoji .env fajl
type .env

# Treba da sadrži:
# OPENAI_API_KEY=sk-proj-your-key
```

---

## 🚀 Korak-po-Korak Testiranje

### Korak 1: Pokreni Backend Server

```bash
# U app/backend direktorijumu sa aktiviranim venv
python main.py
```

**Očekivani output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test da server radi:**
```bash
# U novom terminalu
curl http://localhost:8000/health
# ili idi na http://localhost:8000/docs za Swagger UI
```

### Korak 2: Test Basic RAG Functionality

```bash
# U app/backend sa aktiviranim venv
python test_rag.py
```

**Očekivani output:**
```
🚀 Starting RAG System Tests
🔍 Testing PDF Processing...
✅ Created 1 chunks from test content
✅ Extracted metadata: category='hotel' location='Beograd'...
...
🎉 All tests passed! RAG system is ready for Phase 3.
```

### Korak 3: Test sa Pravim PDF Fajlovima

**3a. Bulk Processing - Svi PDF-ovi odjednom:**
```bash
# U app/backend sa aktiviranim venv
python -c "
from services.document_service import DocumentService
import os

doc_service = DocumentService()
pdf_dir = '../../data/Ulazni podaci-20250621T091254Z-1-001/Ulazni podaci'

if os.path.exists(pdf_dir):
    print(f'Processing PDFs from: {pdf_dir}')
    results = doc_service.process_documents_directory(pdf_dir)
    
    successful = len([r for r in results if r.processing_status == 'success'])
    total = len(results)
    
    print(f'\\n📊 RESULTS: {successful}/{total} PDFs processed successfully')
    
    # Show some stats
    stats = doc_service.get_database_stats()
    print(f'📈 Database now contains {stats[\"total_documents\"]} chunks')
    print(f'📂 Categories: {stats[\"categories\"]}')
    print(f'🏙️ Locations: {stats[\"locations\"]}')
else:
    print('❌ PDF directory not found!')
"
```

**3b. Test Search Nakon Loading:**
```bash
python -c "
from services.document_service import DocumentService

doc_service = DocumentService()

# Test queries
queries = [
    'hotel u Rimu',
    'restorani u Beogradu', 
    'aranžman za Grčku',
    'letovanje na moru',
    'tura po Evropi'
]

for query in queries:
    print(f'\\n🔍 Query: \"{query}\"')
    results = doc_service.search_documents(query, limit=3)
    print(f'📊 Found {results.total_results} results in {results.processing_time:.2f}s')
    
    for i, result in enumerate(results.results[:2]):  # Show top 2
        print(f'  {i+1}. Score: {result.similarity_score:.3f} | {result.text[:100]}...')
"
```

### Korak 4: Test API Endpoints

**4a. Test Document Stats:**
```bash
curl http://localhost:8000/documents/stats
```

**4b. Test Search API:**
```bash
curl -X POST "http://localhost:8000/documents/search?query=hotel%20u%20Rimu&limit=5" \
  -H "Content-Type: application/json"
```

**4c. Test sa filterima:**
```bash
curl -X POST "http://localhost:8000/documents/search?query=smeštaj&category=hotel&location=Rim&limit=3" \
  -H "Content-Type: application/json"
```

### Korak 5: Test File Upload API

**Pripremi test PDF:**
```bash
# Kopiraj jedan PDF u backend folder za test
copy "..\..\data\Ulazni podaci-20250621T091254Z-1-001\Ulazni podaci\*.pdf" "test_upload.pdf"
```

**Upload via curl:**
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_upload.pdf"
```

---

## 📊 Očekivani Rezultati

### Uspešno Procesiranje:
```json
{
  "filename": "Amsterdam_PRVI_MAJ_2025.pdf",
  "status": "success", 
  "total_chunks": 12,
  "error_message": null,
  "processed_at": "2025-06-21T15:30:00"
}
```

### Uspešna Pretraga:
```json
{
  "query": "hotel u Rimu",
  "results": [
    {
      "chunk_id": "abc123def456",
      "text": "Hotel Colosseum u centru Rima...",
      "metadata": {
        "category": "hotel",
        "location": "Rim",
        "price_range": "expensive"
      },
      "similarity_score": 0.89
    }
  ],
  "total_results": 1,
  "processing_time": 1.23
}
```

---

## 🔧 Troubleshooting

### Problem: "ModuleNotFoundError"
```bash
# Rešenje: Aktiviraj venv i instaliraj dependencies
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Problem: "OpenAI API key not found"
```bash
# Rešenje: Proveri .env fajl
type .env
# Dodaj: OPENAI_API_KEY=sk-proj-your-actual-key
```

### Problem: "PDF processing failed"
```bash
# Rešenje: Proveri PDF putanje
dir "..\..\data\Ulazni podaci-20250621T091254Z-1-001\Ulazni podaci\"
```

### Problem: "ChromaDB errors"
```bash
# Rešenje: Obriši i recreate database
Remove-Item -Recurse -Force chroma_db\
python test_rag.py
```

---

## 🎯 Demo Preparation Commands

### Pre-load svih PDF dokumenata:
```bash
# Aktiviraj venv
venv\Scripts\Activate.ps1

# Pokreni server u background-u
Start-Process powershell -ArgumentList "-Command", "cd '$PWD'; python main.py"

# Sačekaj 5 sekundi pa ucitaj dokumente
timeout 5

# Bulk load
python -c "
from services.document_service import DocumentService
import time

print('🚀 Starting bulk PDF processing for demo...')
start_time = time.time()

doc_service = DocumentService()
results = doc_service.process_documents_directory('../../data/Ulazni podaci-20250621T091254Z-1-001/Ulazni podaci')

successful = len([r for r in results if r.processing_status == 'success'])
total = len(results)
processing_time = time.time() - start_time

print(f'\\n✅ DEMO READY!')
print(f'📊 Processed: {successful}/{total} PDFs in {processing_time:.1f}s')

stats = doc_service.get_database_stats()
print(f'📈 Total chunks: {stats[\"total_documents\"]}')
print(f'📂 Categories: {stats[\"categories\"]}')
print(f'🏙️ Locations: {stats[\"locations\"]}')
"
```

**Demo je spreman kada vidiš:**
```
✅ DEMO READY!
📊 Processed: 34/34 PDFs in 45.2s
📈 Total chunks: 487
📂 Categories: ['hotel', 'tour', 'restaurant', 'attraction']
🏙️ Locations: ['Rim', 'Amsterdam', 'Istanbul', 'Beograd', ...]
```

---

**💡 Pro Tips:**
- Čuvaj `chroma_db/` folder - to je tvoja baza podataka
- Nakon svakog bulk load-a, testiraj search da vidiš da li radi
- Za demo, pripremi standardne upite koji pokazuju različite funkcionalnosti 