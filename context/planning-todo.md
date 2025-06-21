# TurBot Development Plan - To-Do Lista

## 🎯 Cilj: Funkcionalan turistički AI agent do sutra 11:00

### Phase 1: Setup & Infrastructure (Sati 1-3)

#### Environment Setup
- [x] **Kreiranje GitHub repo** - organizacija koda i backup ✅
- [x] **Python environment setup** - virtual env + dependencies ✅
- [x] **Next.js project init** - osnovni chat interface ✅
- [x] **Cursor AI workspace config** - optimizacija za Python+RAG ✅

#### Dependencies & APIs
- [x] **OpenAI API key setup** - GPT-4o-mini + embeddings (potrebno od korisnika)
- [x] **Python dependencies install:** ✅
  ```
  fastapi, uvicorn, python-dotenv
  openai, httpx, pydantic
  pdfplumber, chromadb
  ```
- [x] **Next.js dependencies:** ✅
  ```
  axios, lucide-react, clsx, tailwind-merge
  ```

#### Basic Architecture
- [x] **FastAPI app structure** - main.py + routers + models ✅
- [x] **Environment variables** - API keys, config (.env-copy fajlovi) ✅
- [x] **CORS setup** - Next.js ↔ FastAPI komunikacija ✅
- [x] **Health check endpoint** - /health za monitoring ✅

---

### Phase 2: Core RAG Implementation (Sati 4-10)

#### PDF Processing & Document Ingestion
- [ ] **PDF upload endpoint** - `/upload-documents`
- [ ] **PDF extraction sa pdfplumber:**
  - [ ] Text extraction sa formatting preservation
  - [ ] Table detection i extraction (cene, radno vreme)
  - [ ] Metadata extraction (lokacije, kategorije)
- [ ] **Document chunking strategy:**
  - [ ] 1024 tokens per chunk
  - [ ] 20% overlap između chunks
  - [ ] Semantic chunking za tabele
- [ ] **Document validation** - check format, charset, size

#### Vector Database Setup
- [ ] **Chroma initialization** - lokalna persistence
- [ ] **Collection creation** - tourist_documents collection
- [ ] **Embedding generation** - OpenAI text-embedding-3-small
- [ ] **Document indexing** - chunk storage sa metadata
- [ ] **Metadata schema definition:**
  ```json
  {
    "category": "hotel|restaurant|attraction|tour",
    "location": "city|district|specific_address", 
    "price_range": "budget|moderate|expensive|luxury",
    "family_friendly": true|false,
    "seasonal": "year_round|summer|winter|spring|autumn"
  }
  ```

#### Basic Retrieval System
- [ ] **Search endpoint** - `/search` za document retrieval
- [ ] **Semantic search** - vector similarity
- [ ] **Metadata filtering** - strukturirano filtriranje
- [ ] **Result ranking** - osnovni scoring algoritam
- [ ] **Response formatting** - strukturirani JSON output

---

### Phase 3: Advanced RAG Features (Sati 11-16)

#### Query Expansion za Srpski
- [ ] **Query expansion service:**
  - [ ] Sinonimi: restoran → kafana, gostionica, mehana
  - [ ] Regionalni termini: Belgrade → Beograd → prestonica
  - [ ] Morfološke varijante: najbolji → naj + superlativi
- [ ] **GPT-4o-mini query expander** - prompt engineering
- [ ] **Multi-query generation** - 3-5 varijanti originalnog upita
- [ ] **Query validation** - filter nonsense expansions

#### Metadata-Rich Indexing
- [ ] **Automatic metadata extraction:**
  - [ ] NER za lokacije (spaCy ili GPT)
  - [ ] Price range detection iz teksta
  - [ ] Category classification
  - [ ] Family-friendly keywords detection
- [ ] **Manual metadata enhancement** - proveriti i popuniti gaps
- [ ] **Metadata validation** - ensure consistency
- [ ] **Advanced filtering** - kombinovani filter queries

#### Self-Querying Retrieval
- [ ] **Natural language → structured query parser**
- [ ] **Query intent classification:**
  - [ ] Informational: "radno vreme", "cena"
  - [ ] Recommendation: "preporuči", "najbolji"
  - [ ] Comparison: "uporedi", "razlika"
  - [ ] Navigation: "kako da dođem", "gde se nalazi"
- [ ] **Automated filter generation** - iz natural language
- [ ] **Fallback strategies** - kada parsing ne uspe

#### Conversational Memory (Nice-to-have)
- [ ] **Session management** - user session tracking
- [ ] **Conversation history storage** - poslednih 5-10 exchanges
- [ ] **Context extraction** - imenovani entiteti iz istorije
- [ ] **Context-aware query enhancement** - dodaj kontekst u trenutni upit
- [ ] **Memory cleanup** - avoid context overflow

---

### Phase 4: LLM Integration & Response Generation (Sati 17-19)

#### Response Generation Pipeline
- [ ] **Retrieved documents → context compilation**
- [ ] **Context ranking** - najrelevantniji sources first
- [ ] **Response prompt engineering:**
  ```
  System: Ti si TurBot, ekspert za turizam u Srbiji...
  Context: [retrieved documents]
  User Query: [original question]
  Instructions: Odgovori na srpskom, koristi samo proverne informacije...
  ```
- [ ] **GPT-4o final response generation** - kvalitetni odgovori
- [ ] **Source attribution** - referenciraj korišćene dokumente
- [ ] **Response validation** - check hallucinations

#### Chat Interface Implementation
- [ ] **Chat endpoint** - `/chat` za conversation flow
- [ ] **Streaming response** - real-time typing effect
- [ ] **Error handling** - graceful failures
- [ ] **Rate limiting** - prevent abuse
- [ ] **Response formatting** - markdown support za strukture

#### Optional: Re-ranking (Bonus Feature)
- [ ] **Cohere Rerank API integration** - ako ostane budžeta
- [ ] **Custom scoring** - tourism-specific relevance
- [ ] **A/B comparison** - sa i bez re-ranking

---

### Phase 5: Frontend Development (Sati 12-18, paralelno)

#### Basic Chat Interface
- [ ] **Chat UI komponente** - message bubbles, input field
- [ ] **Responsive design** - mobile + desktop
- [ ] **Typing indicators** - better UX
- [ ] **Message history** - scroll through conversation
- [ ] **Error states** - network failures, API errors

#### Advanced UI Features
- [ ] **Quick action buttons** - "Preporuči hotel", "Cene restorana"
- [ ] **Source citations** - show document references
- [ ] **Filter widgets** - price range, location, category
- [ ] **Loading states** - during API calls
- [ ] **Copy/share functionality** - share responses

#### Polish & UX
- [ ] **Visual design** - profesionalan tourism theme
- [ ] **Accessibility** - screen readers, keyboard navigation
- [ ] **Performance optimization** - lazy loading, caching
- [ ] **Mobile optimization** - touch-friendly interface

---

### Phase 6: External Integrations (Sati 19-21)

#### Weather Integration
- [ ] **WeatherAPI setup** - free tier registration
- [ ] **Location-based weather** - trenutno + 5-day forecast
- [ ] **Weather in responses** - "Kakvo će biti vreme u Beogradu?"
- [ ] **Seasonal recommendations** - prilagodi predloge vremenu

#### Optional Integrations (ako ostane vremena)
- [ ] **Google Places API** - reviews, photos, contact info
- [ ] **OpenTripMap** - attractions, POIs
- [ ] **Currency conversion** - real-time rates za turiste
- [ ] **Transportation info** - javni prevoz, taxi info

---

### Phase 7: Testing & Quality Assurance (Sati 21-22)

#### System Testing
- [ ] **End-to-end testing** - complete user journeys
- [ ] **API testing** - svi endpoints rade
- [ ] **Edge case testing** - empty queries, long texts, invalid inputs
- [ ] **Performance testing** - response times pod opterećenjem
- [ ] **Error handling** - graceful degradation

#### Content Quality Testing
- [ ] **Sample questions testing:**
  - [ ] "Kakvu ponudu imate za letovanje na Mediteranu?"
  - [ ] "Tražim aranžman za Grčku u junu, četvoročlana porodica, budžet do 2000 eura"
  - [ ] "Koji all inclusive aranžmani za Tursku su dostupni?"
  - [ ] "Preporučite najbolje restorane u blizini mog hotela u Rimu"
  - [ ] "Kakvo će biti vreme u Parizu sledeće nedelje?"
- [ ] **Accuracy validation** - check protiv original PDF documents
- [ ] **Response quality** - naturalnost, korisnost, preciznost
- [ ] **Citation accuracy** - proveri source references

#### Deployment Testing
- [ ] **Local deployment test** - sve radi lokalno
- [ ] **Railway deployment** - backend deploy test
- [ ] **Vercel deployment** - frontend deploy test
- [ ] **Cross-deployment communication** - API connectivity
- [ ] **Environment variables** - production config

---

### Phase 8: Deployment & Demo Prep (Sati 22-23)

#### Production Deployment
- [ ] **Railway backend deployment:**
  - [ ] Dockerfile creation
  - [ ] Environment variables setup
  - [ ] Health checks configuration
  - [ ] Domain/URL configuration
- [ ] **Vercel frontend deployment:**
  - [ ] Build optimization
  - [ ] Environment variables (API URLs)
  - [ ] Domain setup
  - [ ] Performance optimization

#### Demo Preparation
- [ ] **Demo script writing** - step-by-step scenario
- [ ] **Test data preparation** - realistic tourism questions
- [ ] **Backup plans** - šta ako API ne radi tokom demo-a
- [ ] **Performance monitoring** - ensure sistema radi smooth
- [ ] **Demo environment** - staging vs production

#### Presentation Materials
- [ ] **Technical architecture diagram** - kako sistem radi
- [ ] **Demo flow planning** - logical progression pitanja
- [ ] **Metrics preparation** - response times, accuracy stats
- [ ] **Code highlights** - najvažniji technical decisions
- [ ] **Future roadmap** - šta bi se dodalo sledeće

---

## 🚨 Critical Success Factors

### Must-Have Features (za minimum viable product):
1. **PDF document ingestion** - osnovni RAG functionality
2. **Semantic search** - find relevant information
3. **Serbian query processing** - query expansion basic level
4. **Chat interface** - functional conversation
5. **Metadata filtering** - basic structured queries

### Nice-to-Have Features (za bonus poene):
1. **Advanced RAG techniques** - hybrid search, re-ranking
2. **Conversational memory** - context preservation
3. **External integrations** - weather, maps
4. **Advanced UI** - filters, quick actions
5. **Performance optimizations** - caching, streaming

### Demo Killer Features (impress komisiju):
1. **Live document upload** - dodaj novi PDF i instantly searchable
2. **Multi-turn conversation** - complex back-and-forth
3. **Source attribution** - show exactly which document provided info
4. **Real-time weather** - integrated practical information
5. **Mobile responsiveness** - works perfectly na phone

---

## 📊 Success Metrics to Track

### Technical Metrics:
- **Response time** - < 3 sekunde za kompletne odgovore
- **Accuracy rate** - >75% tačnih odgovora na test pitanja
- **System uptime** - 99%+ tokom demo perioda
- **API costs** - ostati pod $15 budžetom

### Business Metrics:
- **User engagement** - average conversation length
- **Query resolution** - % pitanja koja dobiju satisfy odgovor
- **Source coverage** - % dokumenata koji se koriste u odgovorima
- **Error rate** - < 5% failed queries

---

## 🎯 Final Checklist (Pre Demo-a)

### Technical Readiness:
- [ ] Svi endpoints rade bez grešaka
- [ ] Frontend-backend komunikacija stabilna
- [ ] Production deployment uspešan
- [ ] Backup API keys i credentials
- [ ] Error monitoring aktivan

### Content Readiness:
- [ ] Minimum 10 PDF dokumenata successfully indexed
- [ ] Test scenarios validated
- [ ] Edge cases handled gracefully
- [ ] Response quality satisfactory

### Presentation Readiness:
- [ ] Demo script practiced
- [ ] Technical questions anticipated
- [ ] Backup plans ready
- [ ] Time management planned (≤15 minuta presentation)