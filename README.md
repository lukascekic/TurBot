# TurBot - AI Agent za Turističke Agencije

TurBot je napredni generativni AI agent razvijen za RBT Hakaton koji služi kao digitalni asistent turističkim agencijama. Omogućava precizno pretraživanje i preporučivanje turističkih aranžmana na srpskom jeziku koristeći Enhanced RAG arhitekturu.

## 🚀 Quick Start

### Backend Setup
```bash
cd app/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Dodaj OpenAI API key u .env fajl
echo "OPENAI_API_KEY=your_api_key_here" > .env

# Pokreni server
python main.py
```

### Frontend Setup
```bash
cd app/frontend
npm install
npm run dev
```

### Bulk Load Documents
```bash
cd app/backend/tests
python bulk_load_pdfs.py
```
**Napomena**: Script automatski traži PDF dokumente u `ulazni-podaci/` folderu u root-u projekta.

## 📋 Aplikacija

**TurBot** je AI agent sa dvojakom ulogom:
- **Client Interface** (`/client`) - Consumer-friendly chat za krajnje korisnike
- **Agent Interface** (`/agent`) - Professional dashboard za turističke agente

Sistem obrađuje PDF dokumente turističkih aranžmana i omogućava naprednu pretragu pomoću prirodnog jezika na srpskom.

## 🏗️ Struktura Projekta

```
app/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── routers/
│   │   ├── documents.py     # Document management endpoints
│   │   └── sessions.py      # Chat sessions endpoints
│   ├── services/
│   │   ├── pdf_processor.py           # PDF processing
│   │   ├── vector_service.py          # ChromaDB vector operations
│   │   ├── metadata_enhancement_service.py  # AI metadata extraction
│   │   ├── self_querying_service.py   # Natural language → filters
│   │   ├── query_expansion_service.py # Serbian query expansion
│   │   └── response_generator.py      # LLM response generation
│   └── models/
│       ├── document.py      # Data models
│       └── conversation.py  # Chat models
└── frontend/
    ├── app/
    │   ├── client/          # Consumer interface
    │   └── agent/           # Professional interface
    ├── components/
    │   └── ChatBubble.tsx   # Shared chat component
    └── lib/
        └── api.ts           # API client
```

## 🛠️ Tehnologije

### Backend Stack
- **FastAPI** - Python web framework
- **ChromaDB** - Vector database (lokalna persistence)
- **OpenAI GPT-4o-mini** - LLM za cost-effective performance
- **OpenAI text-embedding-3-small** - Embeddings
- **pdfplumber** - PDF text extraction

### Frontend Stack
- **Next.js + TypeScript** - React framework
- **TailwindCSS + Radix UI** - Styling i komponente
- **Real-time streaming** - Server-sent events

## 🔧 Enhanced RAG Tehnike

### 1. AI-Enhanced Metadata Extraction
- **GPT-4o-mini** za kreiranje strukturisanih metadata iz PDF-ova
- **Confidence scoring** za kvalitet ekstraktovanih podataka
- **Comprehensive schema**: destinacija, kategorija, cena, transport, sezonalnost

### 2. Self-Querying
- **Natural language parsing** → strukturisani filteri
- **Serbian language optimization** za turistički sadržaj
- **Multi-filter extraction** (do 5 filtera po query-ju)

### 3. Query Expansion
- **Semantic expansion** sinonima i regionalnih termina
- **Tourism vocabulary** optimizacija za srpski jezik
- **Morphological variants** handling

### 4. Weighted Filtering & Post-Processing
- **Primary ChromaDB filter**: location (obavezno ako postoji)
- **Post-processing penalties**: sezonalnost (30%), cena (20%), trajanje (različito)
- **Priority hierarchy**: location > season > price > duration > category

### 5. Conversational Memory
- **Session-based context** retention
- **Entity extraction** i tracking kroz konverzaciju
- **Multi-turn dialog** support sa kontekstom

### 6. Response Generation
- **Source attribution** - transparentnost podataka
- **Anti-hallucination** prompting
- **Structured responses** sa suggested follow-ups

## 🎯 Performance Metrics

- **Response Time**: < 3 sekunde
- **Accuracy**: 90%+ za turističke upite
- **Cost Efficiency**: < 0.5€ per 1000 queries
- **Database**: 112 document chunks, 34 PDF dokumenta
- **Languages**: Srpski (primarni), osnovni engleski support

## 📊 Demo Endpoints

- **Health Check**: `GET /health`
- **Document Upload**: `POST /documents/upload`
- **Enhanced Search**: `POST /documents/search`
- **Streaming Chat**: `POST /chat/stream`
- **Statistics**: `GET /documents/stats`

---

*Razvijeno za RBT Hakaton 2025 | Enhanced RAG Architecture* 