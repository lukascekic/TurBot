# TurBot - Projektne Odluke i Kontekst

## 📋 Pregled Projekta

**Naziv:** TurBot - Gen AI Agent za turističke agencije  
**Cilj:** Funkcionalan turistički AI agent koji zamenjuje/asistira turističkom agentu  
**Deadline:** Sutra 11:00  
**Budžet:** ~$15 za API pozive  

## 🏗️ Arhitektura Sistema

### Backend Stack
- **Framework:** FastAPI (Python)
- **LLM:** OpenAI GPT-4o-mini (cost-effective choice)
- **Embeddings:** OpenAI text-embedding-3-small
- **Vector DB:** ChromaDB (lokalna persistence)
- **PDF Processing:** pdfplumber
- **Server:** Uvicorn

### Frontend Stack
- **Framework:** Next.js (React)
- **Styling:** TailwindCSS
- **HTTP Client:** Axios
- **Deployment:** Vercel

### External Services
- **OpenAI API** - LLM i embeddings
- **WeatherAPI** - vremenska prognoza (optional)
- **Deployment:** Railway (backend) + Vercel (frontend)

## 🔧 Ključne Tehničke Odluke

### RAG Implementation
- **Chunking Strategy:** 1024 tokens per chunk, 20% overlap
- **Retrieval:** Semantic search + metadata filtering
- **Query Expansion:** Sinonimi i regionalni termini za srpski jezik
- **Context Window:** Optimizovan za GPT-4o-mini

### Document Processing
- **Format:** PDF dokumenti (50 turističkih aranžmana)
- **Extraction:** Text + tabele (cene, radno vreme)
- **Metadata Schema:**
  ```json
  {
    "category": "hotel|restaurant|attraction|tour",
    "location": "city|district|specific_address", 
    "price_range": "budget|moderate|expensive|luxury",
    "family_friendly": true|false,
    "seasonal": "year_round|summer|winter|spring|autumn"
  }
  ```

### Language Processing
- **Jezik:** Srpski (primarni)
- **Query Expansion:** Morfološke varijante, sinonimi, regionalni termini
- **Response Generation:** Strukturirani odgovori sa source attribution

## 🎯 Prioritizovane Funkcionalnosti

### Must-Have (MVP)
1. PDF document ingestion i RAG search
2. Semantic search sa metadata filtering
3. Basic srpski query processing
4. Functional chat interface
5. Source attribution

### Nice-to-Have (Bonus)
1. Advanced RAG (hybrid search, re-ranking)
2. Conversational memory
3. Weather integration
4. Advanced UI sa filterima
5. Performance optimizations

### Demo Killer Features
1. Live document upload
2. Multi-turn conversations
3. Real-time weather integration
4. Mobile responsiveness
5. Source citations

## 💰 Cost Optimization Strategy

- **GPT-4o-mini** umesto GPT-4 (10x jeftiniji)
- **Efficient chunking** - minimize token usage
- **Caching** - repeat queries
- **Rate limiting** - prevent abuse
- **Target:** < $15 ukupno, < 0.5€ per 1000 queries

## 📊 Success Metrics

### Technical KPIs
- Response time < 3 sekunde
- Accuracy rate > 75%
- System uptime > 99%
- API costs < $15

### Business KPIs  
- Query resolution rate > 80%
- Average conversation length > 3 exchanges
- Source coverage > 70% dokumenata
- Error rate < 5%

## 🚀 Deployment Strategy

### Development
- **Local:** FastAPI + Next.js dev servers
- **Database:** ChromaDB lokalna persistence
- **Environment:** Python venv + Node.js

### Production
- **Backend:** Railway (Dockerfile deployment)
- **Frontend:** Vercel (automatic deployment)
- **Domain:** Custom domain setup
- **Monitoring:** Health checks + error tracking

## 📁 Project Structure

```
app/
├── backend/
│   ├── main.py
│   ├── routers/
│   ├── models/
│   ├── services/
│   └── utils/
├── frontend/
│   ├── pages/
│   ├── components/
│   └── styles/
└── shared/
    └── types/

context/
├── context.md
├── planning-todo.md
├── openai-setup.md
└── deployment-guide.md
```

## 🔑 Integration Points

### OpenAI Integration
- **API Key:** Environment variable
- **Models:** gpt-4o-mini, text-embedding-3-small
- **Rate Limits:** Tier 1 (3 RPM, 200 RPD)
- **Error Handling:** Retry logic + fallbacks

### Database Integration
- **ChromaDB:** Persistent local storage
- **Collections:** tourist_documents
- **Indexing:** Automatic with metadata
- **Backup:** Export/import functionality

## 📋 Testing Strategy

### Unit Tests
- PDF processing functions
- RAG retrieval accuracy
- Query expansion logic
- Response generation quality

### Integration Tests
- End-to-end conversation flows
- API endpoint functionality
- Frontend-backend communication
- External service integrations

### Demo Tests
- Sample tourism questions
- Edge case handling
- Performance under load
- Mobile responsiveness

## 🛡️ Risk Mitigation

### Technical Risks
- **API Rate Limits:** Implement caching + retry logic
- **PDF Processing Errors:** Robust error handling
- **Vector DB Performance:** Optimize indexing
- **Response Quality:** Prompt engineering + validation

### Business Risks
- **Cost Overrun:** Monitor usage + implement limits
- **Accuracy Issues:** Comprehensive testing + validation
- **Demo Failures:** Backup plans + fallback scenarios
- **Time Constraints:** MVP-first approach

## 📝 Chat 1 - Environment Setup (ZAVRŠENO)

### Ključne Odluke i Implementacije:

#### Environment Setup ✅
- **Git Repository:** Kreiran local + GitHub setup
- **Python Backend:** FastAPI sa venv, svi dependencies instalirani
- **Next.js Frontend:** Kreiran sa TypeScript, Tailwind, Lucide icons
- **Project Structure:** app/{backend, frontend, shared} + context/

#### Secret Branch Strategy ✅
- **local-dev branch:** Čuva context/ fajlove lokalno
- **master branch:** Samo kod, ide na GitHub (bez context fajlova)

#### Git Workflow (KRITIČNO - UVEK PRATITI):

**Development Workflow:**
```bash
# 1. Radi na local-dev branch-u
git checkout local-dev

# 2. Napravi izmene (kod + context fajlovi)
# ... rad na kodu ...

# 3. Commit na local-dev
git add .
git commit -m "Feature: implementirana nova funkcionalnost"

# 4. Switch na master za GitHub
git checkout master

# 5. Merge SAMO kod izmene (bez context/ foldera)
git merge local-dev

# 6. Push na GitHub (javno)
git push origin master

# 7. Vratiti se na local-dev za dalji rad
git checkout local-dev
```

**⚠️ NIKAD NE RADI:**
- `git push origin local-dev` - Context fajlovi bi postali javni!
- Development direktno na master branch-u
- Commit context fajlova na master

**✅ UVEK RADI:**
- Development na local-dev
- Context fajlovi ostaju na local-dev
- Samo clean kod ide na GitHub

#### Environment Configuration ✅
- **.env-copy fajlovi:** Template fajlovi za korisnika
- **.gitignore:** Ažuriran da ne čuva .env-copy i environment fajlove
- **OpenAI API:** Setup guide kreiran, korisnik dodao svoj API key

#### Basic Architecture ✅
- **Backend:** FastAPI app sa health check i basic chat endpoint
- **Frontend:** Funkcionalni chat interface sa real-time porukama
- **CORS:** Konfigurisan za komunikaciju frontend-backend
- **Error Handling:** Basic error handling implementiran

#### ML Explanations Framework ✅
- **explanations/** folder kreiran (lokalno, ne ide na git)
- **01-rag-basic-concepts.md:** Objašnjeni RAG osnovi za nekoga bez ML iskustva

#### Deployment Strategy ✅
- **Timing:** Nakon Phase 2, pre mentorske sesije
- **Railway:** Backend deployment setup guide
- **Vercel:** Frontend deployment setup guide
- **Monitoring:** Performance targets i troubleshooting guide

### Sledeći Koraci (Phase 2):
1. PDF document ingestion i processing
2. ChromaDB vector database setup
3. OpenAI embeddings integration
4. Basic RAG retrieval implementation
5. Query expansion za srpski jezik

### Tehnički Stack Konfirmovan:
- **Backend:** FastAPI + ChromaDB + OpenAI + pdfplumber
- **Frontend:** Next.js + TypeScript + Tailwind + Axios
- **Deployment:** Railway (backend) + Vercel (frontend)
- **Cost Target:** < $15 ukupno

## 📝 Chat 2 - Core RAG Implementation (ZAVRŠENO)

### Ključne Implementacije Phase 2:

#### PDF Processing & Document Ingestion ✅
- **PDFProcessor servis:** pdfplumber za ekstraktovanje teksta i tabela
- **Smart chunking:** 1024 tokena per chunk sa 20% overlap
- **Metadata extraction:** automatska detekcija kategorije, lokacije, cena, family-friendly
- **Document validation:** error handling i status tracking

#### Vector Database Setup ✅  
- **ChromaDB:** persistent local storage (`./chroma_db`)
- **OpenAI embeddings:** text-embedding-3-small (1536 dimensions)
- **Collection management:** tourism_documents sa metadata
- **Batch processing:** optimizovano za embeddings kreiranje

#### Basic Retrieval System ✅
- **VectorService:** semantic search sa similarity scoring
- **Metadata filtering:** kombinovano filtriranje po kategoriji, lokaciji, ceni
- **SearchResponse:** strukturirani JSON sa similarity scores i source attribution
- **Query processing:** embedding creation i vector similarity search

#### FastAPI Endpoints ✅
- **POST /documents/upload:** PDF upload i processing
- **POST /documents/search:** semantic search sa filterima  
- **GET /documents/stats:** database statistike
- **GET /documents/list:** lista uploaded dokumenata
- **DELETE /documents/{filename}:** document management
- **POST /documents/process-directory:** bulk processing

#### Models & Architecture ✅
- **Pydantic models:** DocumentChunk, SearchQuery, SearchResponse, DocumentMetadata
- **Service layer:** PDFProcessor, VectorService, DocumentService
- **Router layer:** documents.py sa async endpoints i thread pool
- **Error handling:** comprehensive error handling i validation

#### Testing & Validation ✅
- **test_rag.py:** comprehensive test suite za sve komponente
- **All tests passing:** PDF processing, vector service, document service, bulk processing
- **Real PDF testing:** successful processing of actual tourism PDFs
- **API validation:** endpoints rade sa real data

### Git Workflow Uspešno Izvršen ✅

**Local-dev branch (sa context fajlovima):**
- Sav kod + context fajlovi commitovani
- Development environment sa punim pristupom

**Master branch (clean kod za GitHub):**
- Samo kod bez context fajlova
- Push-ovano na https://github.com/lukascekic/TurBot
- Javno dostupno i clean

## 📝 Chat 3 - Critical Problem Solving & Testing (ZAVRŠENO)

### Ključni Problemi Rešeni:

#### Problem 1: Virtual Environment Issues ✅
- **Error:** `ModuleNotFoundError: No module named 'dotenv'`
- **Root Cause:** Virtual environment nije bio aktiviran
- **Solution:** Uvek aktiviraj sa `venv\Scripts\Activate.ps1`
- **Status:** ✅ REŠENO

#### Problem 2: PowerShell Command Issues ✅  
- **Error:** `SyntaxError: unterminated string literal`
- **Root Cause:** Complex quoting u PowerShell sa f-strings
- **Solution:** Kreiran `bulk_load_pdfs.py` script umesto inline commands
- **Status:** ✅ REŠENO

#### Problem 3: Pydantic Validation Errors ✅
- **Error:** `page_number Input should be a valid integer`
- **Root Cause:** Empty string umesto None za page_number field
- **Solution:** Special handling u vector_service.py za page_number conversion
- **Status:** ✅ REŠENO

#### Problem 4: Search Returning 0 Results (KRITIČNI!) ✅
- **Error:** Svi search queries vraćaju 0 rezultata uprkos loaded data
- **Root Cause:** Distance-to-similarity conversion bio pogrešan
  - ChromaDB cosine distance: 1.118, 1.125, 1.163
  - Stara formula: `similarity = 1 - distance`
  - Rezultat: `1 - 1.118 = -0.118` (NEGATIVAN!)
  - Negativne vrednosti < threshold (0.1) pa se filtriraju
- **Solution:** Promena u `similarity = 1 / (1 + distance)`
  - Distance 1.118 → Similarity = 0.472 ✅
  - Distance 1.125 → Similarity = 0.471 ✅  
- **Status:** ✅ KRITIČNO REŠENO

#### Problem 5: Metadata Detection Issues ✅
- **Problem:** Location detection vraćao "Beograd" za sve, category uvek "hotel"
- **Root Cause:** Frequency-based competition, "hotel" se pominju svugde
- **Solution 1:** Filename-based priority za lokacije
- **Solution 2:** Priority-based category classification (aranžman > hotel)
- **Result:** Amsterdam, Istanbul, Maroko, Rim tačno detektovani ✅

### Finalni Test Rezultati ✅

#### Database Performance:
- **34/34 PDF documents** uspešno obrađeno (100% success rate)
- **112 document chunks** u ChromaDB vector database
- **Processing time:** 86.4 sekundi za sve PDF-ove
- **Categories extracted:** tour (priority-based logic working!)
- **Locations extracted:** Beograd, Rim, Amsterdam, Istanbul, Maroko...

#### Search Functionality:
- **All complex queries working:** "hotel u Rimu", "Istanbul putovanje", "aranžman za Amsterdam"
- **Similarity scores:** 0.44-0.58 (excellent range)
- **Response times:** 0.20-0.56 sekundi
- **Source attribution:** ✅ Every result shows origin PDF
- **Metadata filtering:** ✅ By category, location, price_range

#### API Endpoints Testing:
- **GET /health** → ✅ `{"status": "healthy", "service": "TurBot API"}`
- **POST /documents/search** → ✅ Returns SearchResponse with results
- **GET /documents/stats** → ✅ `{"total_documents": 112, "categories": ["tour"]}`
- **GET /documents/health** → ✅ Database connection OK
- **GET /documents/list** → ✅ Working properly

## 📝 Chat 4 - Strategy Shift & Phase 3 Preparation (ZAVRŠENO)

### Major Strategic Decision: Advanced RAG Prioritet ✅

#### **Analiza: Manual vs Advanced RAG**
- **Zaključak:** Query expansion + self-querying > manual category optimization
- **Razlog:** LLM automatski rešava probleme koje manual approaches teško pokrivaju
- **Trade-off:** MVP brzina vs long-term elegance
- **Odluka:** Hibridni pristup - minimal manual fix + full Advanced RAG

#### **Implementirane Pripreme za Phase 3:**
- ✅ **Quick Category Fix:** Priority-based classification implementiran
- ✅ **Database Reprocessed:** 112 chunks sa poboljašnm metadata
- ✅ **Context Updated:** Strategy shift dokumentovan
- ✅ **Architecture Ready:** Sav kod pripremljen za Query Expansion integration

#### **Manual Category Improvements (Pre-Advanced RAG):**
```python
# OLD: Frequency-based (problematic)
category = max(category_scores, key=category_scores.get)

# NEW: Priority-based triggers (MVP solution)
if "aranžman" in text → category = "tour"  # Overrides hotel frequency
elif "menu" in text → category = "restaurant"
else → fallback to hotel detection
```

#### **Results Validation:**
- **Before:** Mixed categories (hotel, restaurant, tour)
- **After:** Consistent "tour" classification ✅
- **Impact:** Proper recognition of tourism documents as organized trips

### Phase 3 Implementation Plan 🚀

#### **Core Advanced RAG Features:**
1. **Query Expansion** - Serbian language synonyms & semantic variants
2. **Self-Querying** - Structured query parsing from natural language  
3. **Conversational Memory** - Multi-turn dialog context
4. **Response Generation** - LLM integration for natural answers
5. **Frontend Integration** - User-friendly chat interface

#### **Technical Architecture Changes:**
```python
# Current: Basic semantic search
results = vector_search(query)

# Phase 3: Advanced RAG pipeline
expanded_query = query_expansion_service.expand(query)
structured_query = self_querying_service.parse(expanded_query) 
results = hybrid_search(structured_query)
response = response_generator.generate(results, context)
```

#### **Success Metrics (Demo-Ready):**
- ✅ Core RAG working (MVP baseline)
- 🎯 Natural language understanding (Serbian queries)
- 🎯 Conversational flow (multi-turn dialogs)
- 🎯 Source attribution (transparent AI responses)
- 🎯 Real-time performance (<3s response time)

### Next Steps (Phase 3 Ready):
1. **Query Expansion Service** - LLM-powered Serbian language processing
2. **Self-Querying Implementation** - Natural language → structured search
3. **Conversational Memory System** - Context-aware multi-turn dialogs
4. **Response Generation Pipeline** - LLM integration for natural answers
5. **Frontend Chat Interface** - Production-ready user experience

---

*Poslednja izmena: Jun 21, 2025 - Chat 4*
*Status: Phase 2 KOMPLETNO ✅ + Phase 3 PRIPREMLJEN 🚀*
*Next: Advanced RAG Implementation - Query Expansion, Self-Querying, Conversational AI* 