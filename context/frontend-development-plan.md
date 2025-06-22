# TurBot Frontend Development Plan

## 🎯 **Project Overview**

**Objective:** Create a mock web app with 2 pages to demonstrate TurBot AI agent functionality for hackathon
**Timeline:** Quick implementation for demo purposes
**Technology:** Next.js + React + TypeScript + TailwindCSS

## 📊 **Updated Backend API Status**

### ✅ **Completed Backend Endpoints:**

#### **Core Functionality:**
- `POST /chat` - **Enhanced RAG pipeline** (self-querying → query expansion → vector search → response generation)
- `POST /chat/simple` - Simple search without LLM generation (fallback)
- `GET /health` - Health check

#### **Document Management:**
- `POST /documents/upload` - PDF upload and processing
- `POST /documents/search` - Advanced semantic search with filters
- `GET /documents/stats` - Database statistics
- `GET /documents/list` - List all documents
- `GET /documents/categories` - Available categories
- `GET /documents/locations` - Available locations
- `GET /documents/search-suggestions` - Suggested search queries

#### **Session Management:**
- `POST /sessions/create` - Create new conversation session
- `GET /sessions/{session_id}` - Get session info
- `GET /sessions/{session_id}/history` - Conversation history
- `POST /sessions/{session_id}/message` - Add message to history
- `POST /sessions/{session_id}/preferences` - Update user preferences

### 🔧 **API Response Formats:**

#### **Enhanced Chat Response:**
```typescript
interface ChatResponse {
  response: string;                    // Natural language response
  sources: Array<{                     // Source attribution
    document_name: string;
    similarity: number;
    content_preview: string;
    metadata: any;
  }>;
  suggested_questions: string[];       // Follow-up suggestions
  session_id?: string;                 // Session tracking
  confidence: number;                  // Response confidence (0-1)
  structured_data: {                   // Structured information
    total_results: number;
    price_range: { min?: number; max?: number; currency: string };
    locations: string[];
    categories: string[];
    amenities: string[];
    average_similarity: number;
  };
}
```

## 🏗️ **Frontend Architecture**

### **Two-Page Design:**

#### **Page 1: Client Interface** (`/client`)
- **Target User:** Potential tourists looking for travel arrangements
- **UI Focus:** Consumer-friendly, clean, attractive
- **Functionality:** 
  - Search for travel arrangements
  - Get recommendations
  - View prices and details
  - Ask questions about destinations

#### **Page 2: Agent Interface** (`/agent`)
- **Target User:** Tourism agency staff helping clients
- **UI Focus:** Professional, information-dense, efficient
- **Functionality:**
  - Access to all documents and data
  - Advanced search capabilities
  - Conversation history with clients
  - Quick access to common queries

### **Shared Components:**
- **ChatBubble Component** - Core chat interface
- **Header Component** - Navigation and branding
- **SessionManager** - Handle session state
- **API Client** - Centralized API communication

## 📱 **Page Designs**

### **Client Page Design:**

```
┌─────────────────────────────────────────────────────────┐
│ TurBot - Vaš Turistički Asistent        [🏠] [ℹ️] [📞] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🎯 "Zdravo! Ja sam TurBot, vaš AI turistički         │
│      asistent. Kako vam mogu pomoći danas?"            │
│                                                         │
│  💡 BRZE PRETRAGE:                                     │
│  [Hotel u Rimu] [Letovanje Grčka] [Amsterdam maj]      │
│  [Budžet €500] [Romantičan vikend] [Porodično]         │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 💬 CHAT INTERFACE                               │   │
│  │                                                 │   │
│  │ [Previous conversation messages...]             │   │
│  │                                                 │   │
│  │ TurBot: "Pronašao sam 3 odlična hotela..."     │   │
│  │ • Hotel Roma ⭐⭐⭐⭐ - 180€/noć                 │   │
│  │ • Hotel Centrale ⭐⭐⭐ - 150€/noć              │   │
│  │                                                 │   │
│  │ Vi: "Pokaži mi više o Hotel Roma"               │   │
│  │                                                 │   │
│  │ [Možete li mi dati više detalja o cenama?]     │   │
│  │ [Da li postoje alternativne opcije?]           │   │
│  │                                                 │   │
│  │ ┌─────────────────────────────────────────────┐ │   │
│  │ │ Ukucajte vašu poruku...                   │ │   │
│  │ └─────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### **Agent Page Design:**

```
┌─────────────────────────────────────────────────────────┐
│ TurBot Agent Panel                    [📊] [⚙️] [👤]    │
├─────────────────────────────────────────────────────────┤
│ 📋 DASHBOARD                  │ 💬 ACTIVE CONVERSATION  │
│                              │                          │
│ 📊 Stats:                    │ [Chat interface...]     │
│ • 112 Documents loaded       │                          │  
│ • 5 Active sessions          │ [Previous messages...]   │
│ • 89% Avg. confidence        │                          │
│                              │ Client: "Tražim hotel..." │
│ 🔍 Quick Search:             │                          │
│ ┌─────────────────────────┐  │ TurBot: "Pronašao sam..."│
│ │ Search documents...     │  │                          │
│ └─────────────────────────┘  │ 📎 Sources (3):          │
│                              │ • hotel_rim_2024.pdf    │
│ 📁 Recent Documents:         │ • rome_accommodation.pdf │  
│ • Amsterdam_maj_2025.pdf     │ • italy_travel.pdf       │
│ • Istanbul_4_noci.pdf        │                          │  
│ • Malta_prvi_maj.pdf         │ 💡 Suggested Questions:  │
│                              │ • Cene dodatnih usluga?  │
│ 🎯 Common Queries:           │ • Dostupnost parking?     │
│ • [Rim hoteli]              │ • Uslovi otkazivanja?     │
│ • [Grčka letovanje]          │                          │
│ • [Amsterdam maj]            │ ┌──────────────────────┐  │
│ • [Budget €500]              │ │ Agent response...    │  │
│                              │ └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🛠️ **Implementation Steps**

### **Step 1: Setup & Foundation** (30 minutes)
```bash
# Already done - Next.js project exists
cd app/frontend
npm install
```

**Add new dependencies:**
```bash
npm install @heroicons/react @headlessui/react date-fns uuid
npm install -D @types/uuid
```

### **Step 2: Core Components** (60 minutes)

#### **2.1 API Client Service**
```typescript
// lib/api.ts
class TurBotAPI {
  private baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  
  async chat(message: string, sessionId?: string, userType?: string): Promise<ChatResponse> {
    // Implementation
  }
  
  async createSession(userType: string): Promise<SessionResponse> {
    // Implementation  
  }
  
  async getSearchSuggestions(): Promise<string[]> {
    // Implementation
  }
}
```

#### **2.2 Chat Bubble Component** 
```typescript
// components/ChatBubble.tsx
interface ChatBubbleProps {
  userType: 'client' | 'agent';
  sessionId?: string;
  onNewMessage?: (message: any) => void;
}

export function ChatBubble({ userType, sessionId }: ChatBubbleProps) {
  // Shared chat interface logic
  // Message rendering
  // Input handling
  // Source attribution display
  // Suggested questions
}
```

#### **2.3 Session Management**
```typescript  
// hooks/useSession.ts
export function useSession(userType: 'client' | 'agent') {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const createSession = async () => {
    // Create new session via API
  };
  
  return { sessionId, createSession, isLoading };
}
```

### **Step 3: Client Page Implementation** (45 minutes)

#### **3.1 Client Page Layout**
```typescript
// pages/client.tsx or app/client/page.tsx
export default function ClientPage() {
  const { sessionId, createSession } = useSession('client');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <WelcomeSection />
        <QuickSearchButtons suggestions={suggestions} />
        <ChatBubble userType="client" sessionId={sessionId} />
      </main>
    </div>
  );
}
```

#### **3.2 Welcome & Quick Search**
```typescript
function WelcomeSection() {
  return (
    <div className="text-center mb-8">
      <h1 className="text-4xl font-bold text-gray-800 mb-4">
        🎯 Zdravo! Ja sam TurBot
      </h1>
      <p className="text-xl text-gray-600">
        Vaš AI turistički asistent. Kako vam mogu pomoći danas?
      </p>
    </div>
  );
}

function QuickSearchButtons({ suggestions }: { suggestions: string[] }) {
  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-3">💡 Brze pretrage:</h3>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200 transition"
            onClick={() => handleSuggestionClick(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
```

### **Step 4: Agent Page Implementation** (45 minutes)

#### **4.1 Agent Dashboard Layout**
```typescript
// pages/agent.tsx
export default function AgentPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <DashboardStats />
              <QuickTools />
            </div>
            <div className="lg:col-span-2">
              <ChatBubble userType="agent" />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
```

#### **4.2 Dashboard Components**
```typescript
function DashboardStats() {
  const [stats, setStats] = useState(null);
  
  useEffect(() => {
    // Fetch document stats
  }, []);
  
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h3 className="text-lg font-semibold mb-4">📊 Statistike</h3>
      <div className="space-y-2">
        <div>📄 {stats?.total_documents || 0} Dokumenata</div>
        <div>💬 {activeSessions} Aktivnih sesija</div>
        <div>🎯 {averageConfidence}% Avg. pouzdanost</div>
      </div>
    </div>
  );
}

function QuickTools() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">🛠️ Brzi alati</h3>
      <div className="space-y-2">
        <button className="w-full text-left p-2 hover:bg-gray-50 rounded">
          🔍 Pretraži dokumente
        </button>
        <button className="w-full text-left p-2 hover:bg-gray-50 rounded">
          📊 Prikaži statistike
        </button>
        <button className="w-full text-left p-2 hover:bg-gray-50 rounded">
          ⚙️ Postavke
        </button>
      </div>
    </div>
  );
}
```

### **Step 5: Chat Interface Polish** (30 minutes)

#### **5.1 Message Rendering**
```typescript
function MessageBubble({ message, isUser, sources, suggestedQuestions }: MessageProps) {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
        isUser 
          ? 'bg-blue-500 text-white' 
          : 'bg-white text-gray-800 shadow-md'
      }`}>
        <p className="text-sm">{message}</p>
        
        {sources && sources.length > 0 && (
          <SourceAttribution sources={sources} />
        )}
        
        {suggestedQuestions && suggestedQuestions.length > 0 && (
          <SuggestedQuestions questions={suggestedQuestions} />
        )}
      </div>
    </div>
  );
}
```

#### **5.2 Source Attribution**
```typescript
function SourceAttribution({ sources }: { sources: Source[] }) {
  return (
    <div className="mt-2 pt-2 border-t border-gray-200">
      <p className="text-xs text-gray-500 mb-1">📎 Izvor informacija:</p>
      <div className="space-y-1">
        {sources.map((source, index) => (
          <div key={index} className="text-xs">
            <span className="font-medium">{source.document_name}</span>
            <span className="text-gray-400 ml-1">
              ({(source.similarity * 100).toFixed(0)}% relevantnost)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### **Step 6: Responsive Design & Polish** (30 minutes)

#### **6.1 Mobile Responsiveness**
- Responsive grid layouts
- Mobile-friendly chat interface  
- Touch-friendly buttons
- Optimized for phones and tablets

#### **6.2 Loading States**
```typescript
function LoadingMessage() {
  return (
    <div className="flex justify-start mb-4">
      <div className="bg-white rounded-lg p-4 shadow-md">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
          <span className="text-sm text-gray-600">TurBot tipkuje...</span>
        </div>
      </div>
    </div>
  );
}
```

## 🚀 **Deployment Strategy**

### **Environment Variables:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=TurBot
NEXT_PUBLIC_VERSION=1.0.0
```

### **Build & Deploy:**
```bash
# Development
npm run dev

# Production build
npm run build
npm run start

# Deploy to Vercel
vercel --prod
```

## 🎯 **Success Metrics for Demo**

### **Functional Requirements:**
- ✅ Two distinct pages (client/agent) working
- ✅ Chat interface functional on both pages
- ✅ Real-time communication with Enhanced RAG backend
- ✅ Source attribution displayed
- ✅ Suggested questions working
- ✅ Session management functional
- ✅ Mobile responsive design

### **Demo Killer Features:**
- 🎯 **Live conversation flow** - Real chat with AI responses
- 🎯 **Source transparency** - Show which PDF documents were used
- 🎯 **Professional UI** - Clean, modern interface
- 🎯 **Dual interfaces** - Client vs Agent differentiation
- 🎯 **Serbian language** - Natural Serbian responses
- 🎯 **Real-time suggestions** - Dynamic follow-up questions

## ⏱️ **Implementation Timeline**

| Step | Duration | Task |
|------|----------|------|
| 1 | 30 min | Setup & Dependencies |
| 2 | 60 min | Core Components (API, Chat, Session) |
| 3 | 45 min | Client Page Implementation |
| 4 | 45 min | Agent Page Implementation |
| 5 | 30 min | Chat Interface Polish |
| 6 | 30 min | Responsive Design & Testing |
| **Total** | **4 hours** | **Complete Frontend** |

## 🔧 **Post-Implementation Tasks**

1. **Testing:** Test all chat flows with real queries
2. **Performance:** Optimize loading times and API calls
3. **Error Handling:** Robust error states and fallbacks
4. **Documentation:** Usage guide for both client and agent interfaces
5. **Demo Preparation:** Prepare sample conversations and scenarios

---

*Status: Ready for Implementation*
*Next: Execute Step 1 - Setup & Foundation* 