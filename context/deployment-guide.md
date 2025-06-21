# TurBot Deployment Guide

## 🚀 Kada deployovati?

**Optimalno vreme:** Nakon završetka Phase 2 (Core RAG Implementation) i pre mentorske sesije.

**Razlog:** 
- Imaćeš funkcionalan RAG sistem za demonstraciju mentoru
- Frontend je podložan većim izmenama nakon mentorske sesije
- Možeš testirati performance u production environment-u

## 📋 Pre-deployment Checklist

### Backend spremnost:
- [ ] PDF processing radi lokalno
- [ ] ChromaDB integration funkcioniše
- [ ] OpenAI API pozivi uspešni
- [ ] /health endpoint odgovara
- [ ] Environment varijable konfigurisane

### Frontend spremnost:
- [ ] Chat interface funkcioniše
- [ ] API komunikacija stabilna
- [ ] Responsive design testiran
- [ ] Error handling implementiran

---

## 🚂 Railway Deployment (Backend)

### 1. Priprema projekta

**Kreiranje Dockerfile:**
```dockerfile
# app/backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for ChromaDB and uploads
RUN mkdir -p chroma_db uploads

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
```

### 2. Railway Setup

**Instaliranje Railway CLI:**
```bash
# Windows (PowerShell)
iwr https://railway.app/install.ps1 | iex

# macOS/Linux
curl -fsSL https://railway.app/install.sh | sh
```

**Login i kreiranje projekta:**
```bash
cd app/backend
railway login
railway init
```

### 3. Environment Variables na Railway

U Railway dashboard-u, dodaj sledeće environment varijable:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-actual-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# Railway automatski postavlja PORT varijablu
PORT=8000

# CORS Configuration
ALLOWED_ORIGINS=["https://your-vercel-app.vercel.app", "http://localhost:3000"]

# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=tourist_documents

# Upload Configuration
MAX_FILE_SIZE_MB=10
ALLOWED_FILE_TYPES=["pdf"]
UPLOAD_DIRECTORY=./uploads

# Logging
LOG_LEVEL=INFO
```

### 4. Deployment

```bash
# Deploy to Railway
railway up

# Monitor logs
railway logs

# Get deployment URL
railway domain
```

### 5. Testiranje Backend-a

```bash
# Health check
curl https://your-app.up.railway.app/health

# Test chat endpoint
curl -X POST https://your-app.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test poruka"}'
```

---

## ⚡ Vercel Deployment (Frontend)

### 1. Priprema projekta

**Instaliranje Vercel CLI:**
```bash
npm install -g vercel
```

### 2. Environment Variables

Kreiraj `.env.local` sa production values:
```bash
# API Configuration
NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app

# App Configuration
NEXT_PUBLIC_APP_NAME=TurBot
NEXT_PUBLIC_APP_VERSION=1.0.0
```

### 3. Vercel Setup

```bash
cd app/frontend

# Login to Vercel
vercel login

# Initialize project
vercel init

# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### 4. Vercel Dashboard Configuration

1. Idi na [vercel.com/dashboard](https://vercel.com/dashboard)
2. Otvori svoj projekat
3. Idi na **Settings → Environment Variables**
4. Dodaj:
   ```
   NEXT_PUBLIC_API_URL = https://your-railway-app.up.railway.app
   NEXT_PUBLIC_APP_NAME = TurBot
   NEXT_PUBLIC_APP_VERSION = 1.0.0
   ```

### 5. Redeploy nakon Environment Variables

```bash
# Redeploy da se učitaju nove env varijable
vercel --prod
```

---

## 🔧 Production Optimizacije

### Backend (Railway)

**main.py modifikacije za production:**
```python
import os
from fastapi import FastAPI
import uvicorn

app = FastAPI()

# Health check za Railway
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "TurBot API"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload in production
    )
```

### Frontend (Vercel)

**next.config.ts optimizacije:**
```typescript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
}

module.exports = nextConfig
```

---

## 🛠️ Troubleshooting

### Česti problemi i rešenja:

**Railway Backend Issues:**

1. **Build fails:**
   ```bash
   # Dodaj u requirements.txt
   wheel
   setuptools
   ```

2. **Port issues:**
   ```python
   # U main.py koristi Railway PORT
   port = int(os.getenv("PORT", 8000))
   ```

3. **CORS errors:**
   ```python
   # Dodaj production frontend URL u ALLOWED_ORIGINS
   ALLOWED_ORIGINS=["https://your-vercel-app.vercel.app"]
   ```

**Vercel Frontend Issues:**

1. **API connection fails:**
   - Proveri da li je `NEXT_PUBLIC_API_URL` pravilno postavljen
   - Proveri CORS na backend-u

2. **Build errors:**
   ```bash
   # Očisti cache i reinstaliraj
   rm -rf .next node_modules
   npm install
   npm run build
   ```

---

## 📊 Post-Deployment Monitoring

### Railway Monitoring

```bash
# Provjeri logs
railway logs --tail

# Check status
railway status

# View metrics
railway metrics
```

### Vercel Monitoring

1. Vercel Dashboard → Analytics
2. Proveri Response Times
3. Monitor Error Rates
4. Check Build Success Rate

### Performance Targets

- **Backend Response Time:** < 3 sekunde
- **Frontend Load Time:** < 2 sekunde
- **API Success Rate:** > 99%
- **Cost:** < $15 tokom development/demo

---

## 🔄 Continuous Deployment

### Automatski redeploy na git push:

**Railway:**
- Povezuje se sa GitHub repo
- Automatski deploy na svaki push u main branch

**Vercel:**
- Povezuje se sa GitHub repo
- Automatski deploy na svaki push
- Preview deployments za PR-ove

### Setup:
1. Povezti Railway i Vercel sa GitHub repo
2. Postaviti auto-deploy na main branch
3. Konfigurisati webhook-ove za notifikacije

---

## 🎯 Demo Preparation

### Pre demo-a:
1. **Warm-up API:** Pošalji test request da se aplikacija "progrije"
2. **Check logs:** Bez error-a u poslednih 24h
3. **Test end-to-end:** Kompletna user journey
4. **Backup plan:** Lokalna verzija spremna ako cloud ne radi

### Demo URL-ovi:
- **Frontend:** https://turbot-demo.vercel.app
- **Backend:** https://turbot-api.up.railway.app
- **Health Check:** https://turbot-api.up.railway.app/health

---

**💡 Pro Tip:** Nakon deployment-a, testiraj aplikaciju na mobilnom telefonu da vidiš kako radi responsive design! 