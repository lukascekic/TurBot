# OpenAI API Setup - Uputstvo za TurBot

## 🔑 Dobijanje OpenAI API Ključa

### Korak 1: Kreiranje OpenAI Account-a
1. Idite na [platform.openai.com](https://platform.openai.com)
2. Kliknite "Sign up" ili se prijavite ako već imate account
3. Verifikujte email adresu

### Korak 2: Dodavanje Payment Method-a
⚠️ **VAŽNO:** OpenAI API zahteva dodavanje kartice za korišćenje

1. Idite na [Billing settings](https://platform.openai.com/account/billing/overview)
2. Kliknite "Add payment method"
3. Dodajte kreditnu/debitnu karticu
4. **Preporučeno:** Postavite usage limit na $20 da izbegnete neočekivane troškove
   - Idite na "Usage limits" 
   - Postavite "Hard limit" na $20
   - Postavite "Soft limit" na $15 (dobićete notifikaciju)

### Korak 3: Kreiranje API Key-a
1. Idite na [API Keys page](https://platform.openai.com/api-keys)
2. Kliknite "Create new secret key"
3. Dajte mu ime (npr. "TurBot-Development")
4. **VAŽNO:** Kopirajte key odmah - nećete ga više videti!
5. Key izgleda ovako: `sk-proj-...` (oko 164 karaktera)

## 💳 Cene i Budžet

### Modeli koje koristimo:
- **GPT-4o-mini:** $0.15/1M input tokens, $0.60/1M output tokens
- **text-embedding-3-small:** $0.02/1M tokens

### Procena troškova za TurBot:
- **Development + Testing:** ~$5-8
- **Demo dan:** ~$2-3  
- **Buffer:** ~$5
- **Ukupno:** ~$15 budžet

### Optimizacija troškova:
- Koristimo GPT-4o-mini (10x jeftiniji od GPT-4)
- Kratki i precizni prompt-ovi
- Caching čestih upita
- Rate limiting

## 🔧 Konfiguracija u Projektu

### Environment Variables
Kreirajte fajl `.env` u `app/backend/` folderu sa sledećim sadržajem:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-actual-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# API Configuration
OPENAI_MAX_TOKENS=2048
OPENAI_TEMPERATURE=0.1
OPENAI_REQUEST_TIMEOUT=30

# Rate Limiting
OPENAI_MAX_REQUESTS_PER_MINUTE=3
OPENAI_MAX_TOKENS_PER_DAY=100000
```

### Python kod za konfiguraciju:

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=int(os.getenv("OPENAI_REQUEST_TIMEOUT", 30))
)

# Configuration constants
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", 2048))
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", 0.1))
```

## 🧪 Testiranje API Konekcije

### Jednostavan test script:

```python
# test_openai.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Test chat completion
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Pozdrav! Reci mi nešto o turizmu u Srbiji."}],
        max_tokens=100
    )
    print("✅ Chat API radi!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ Chat API error: {e}")

# Test embeddings
try:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input="Test embedding za turizam"
    )
    print("✅ Embeddings API radi!")
    print(f"Embedding dimension: {len(response.data[0].embedding)}")
except Exception as e:
    print(f"❌ Embeddings API error: {e}")
```

Pokrenite test sa: `python test_openai.py`

## 🔒 Bezbednost API Key-a

### ⚠️ NIKAD:
- Nie commit-ujte API key u Git
- Ne delite key javno
- Ne ostavljajte key u plain text fajlovima

### ✅ UVEK:
- Koristite `.env` fajlove (dodajte u `.gitignore`)
- Koristite environment varijable u production
- Rotite key-ove redovno
- Monitorirajte usage na OpenAI dashboard-u

## 📊 Monitoring i Optimizacija

### Monitoring Usage:
1. Idite na [Usage dashboard](https://platform.openai.com/usage)
2. Pratite dnevnu potrošnju
3. Analizirajte najskuplje API pozive
4. Postavite alert-e za budget limit-e

### Optimizacija:
- **Kraći prompt-ovi** = manji troškovi
- **Caching** - sačuvajte česte odgovore
- **Batch processing** - grupišite zahteve
- **Context compression** - skratite dugačke kontekste

## 🚨 Troubleshooting

### Česte greške:

**"Invalid API key"**
- Proverite da li ste pravilno kopirali key
- Proverite da li key počinje sa `sk-proj-`
- Regenerišite novi key ako treba

**"Rate limit exceeded"**  
- Čekajte 60 sekundi
- Implementirajte retry logic sa exponential backoff
- Smanjite broj paralelnih zahteva

**"Insufficient quota"**
- Dodajte payment method
- Povećajte usage limit
- Proverite billing status

**"Model not found"**
- Proverite da li koristite ispravno ime modela
- `gpt-4o-mini` (ne `gpt-4-mini`)
- `text-embedding-3-small` (ne `text-embedding-small`)

## 🎯 Production Setup

Za production deployment:

1. **Railway Environment Variables:**
   ```
   OPENAI_API_KEY=sk-proj-...
   OPENAI_MODEL=gpt-4o-mini
   ```

2. **Vercel Environment Variables:**
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app
   ```

3. **Health Checks:**
   - Implementirajte `/health` endpoint
   - Testirajte OpenAI konekciju periodično
   - Logirajte errors i performance metrics

---

**💡 Pro Tips:**
- Koristite OpenAI Playground za testiranje prompt-ova
- Čuvajte backup API key-a za emergencije  
- Monitorirajte troškove svakodnevno tokom development-a
- Koristite structured outputs za bolje performanse

*Poslednja izmena: [Trenutni datum]* 