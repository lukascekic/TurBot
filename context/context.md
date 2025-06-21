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
- **Workflow:** 
  - Radi na local-dev za development
  - Switch na master za GitHub push
  - Context fajlovi ostaju privatni

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

---

*Poslednja izmena: Jun 21, 2025 - Chat 1*
*Status: Phase 1 ZAVRŠENA ✅ - Spreman za Phase 2* 