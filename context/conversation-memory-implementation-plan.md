# TurBot Conversation Memory Implementation Plan

## 📋 Overview

**Cilj:** Implementirati napredni conversation memory sistem koji omogućava context-aware multi-turn razgovore  
**Scope:** Session tracking, named entity extraction, context preservation, query enhancement  
**Integration:** Proširenje postojećeg Enhanced RAG sistema  
**Deadline:** Implementation u 3-4 sata  

## 🏗️ Technical Architecture

### **Storage Strategy: JSON Files**
```
app/backend/conversation_data/
├── sessions/
│   ├── {session_id}_conversation.json
│   ├── {session_id}_entities.json
│   └── {session_id}_preferences.json
└── templates/
    ├── entity_extraction_prompt.txt
    └── context_enhancement_prompt.txt
```

### **Memory Components**
1. **ConversationMemoryService** - Core memory management
2. **NamedEntityExtractor** - Tourism-specific entity detection
3. **ContextPreservationService** - Context window management
4. **ContextAwareEnhancer** - Query enrichment integration

### **Integration Points**
```python
# Enhanced RAG Pipeline Integration
User Query → ConversationMemoryService → ContextAwareEnhancer → SelfQueryingService → QueryExpansionService → VectorService → ResponseGenerator
```

## 🔧 Implementation Steps

### **Phase 1: Core Memory Infrastructure (60 min)**

#### **Step 1.1: ConversationMemoryService (30 min)**
```python
# services/conversation_memory_service.py
class ConversationMemoryService:
    def __init__(self):
        self.storage_path = "./conversation_data/sessions"
        self.max_messages = 8
        self.max_age_hours = 24
    
    async def save_message(self, session_id: str, user_message: str, ai_response: str)
    async def get_conversation_history(self, session_id: str) -> List[ChatMessage]
    async def extract_conversation_entities(self, session_id: str) -> Dict[str, Any]
    async def cleanup_old_messages(self, session_id: str)
    async def get_context_summary(self, session_id: str) -> str
```

**Key Features:**
- JSON file-based persistent storage
- Automatic message window management (8 messages max)
- Time-based cleanup (24h retention)
- Efficient read/write operations

#### **Step 1.2: Data Models (15 min)**
```python
# models/conversation.py
class ConversationMessage(BaseModel):
    message_id: str
    session_id: str
    user_message: str
    ai_response: str
    timestamp: datetime
    entities_extracted: Dict[str, Any]
    sources_used: List[str]

class ConversationContext(BaseModel):
    session_id: str
    total_messages: int
    active_entities: Dict[str, Any]
    conversation_summary: str
    user_preferences: Dict[str, Any]
    last_updated: datetime

class TourismEntity(BaseModel):
    entity_type: str  # destination, price_range, travel_dates, etc.
    entity_value: Any
    confidence: float
    first_mentioned: datetime
    last_mentioned: datetime
    frequency: int
```

#### **Step 1.3: JSON Storage Setup (15 min)**
- Create conversation_data directory structure
- Implement file I/O utilities
- Add error handling for file operations
- Create backup/recovery mechanisms

### **Phase 2: Named Entity Extraction (45 min)**

#### **Step 2.1: NamedEntityExtractor Service (30 min)**
```python
# services/named_entity_extractor.py
class NamedEntityExtractor:
    def __init__(self, openai_client):
        self.client = openai_client
        self.tourism_entities = {
            "destination": ["locations", "cities", "countries", "regions"],
            "accommodation": ["hotels", "resorts", "apartments", "villas"],
            "budget": ["price_range", "budget_min", "budget_max", "currency"],
            "travel_dates": ["check_in", "check_out", "duration", "season"],
            "group_composition": ["adults", "children", "group_size"],
            "preferences": ["family_friendly", "luxury_level", "amenities"],
            "transport": ["flight", "bus", "car", "train"],
            "activities": ["sightseeing", "beach", "culture", "adventure"]
        }
    
    async def extract_entities_from_message(self, message: str, conversation_history: List[str]) -> Dict[str, Any]
    async def extract_entities_from_conversation(self, messages: List[ConversationMessage]) -> Dict[str, Any]
    async def merge_entity_updates(self, existing_entities: Dict, new_entities: Dict) -> Dict[str, Any]
    async def resolve_entity_conflicts(self, entities: Dict[str, Any]) -> Dict[str, Any]
```

**Entity Extraction Prompt:**
```
System: Extract tourism-specific entities from user messages. Focus on:
- Destinations (cities, countries, regions)
- Budget constraints (amounts, currency, price ranges)
- Travel dates (specific dates, seasons, duration)
- Group composition (adults, children, special needs)
- Accommodation preferences (hotel type, amenities, star rating)
- Transport preferences (flight, bus, car rental)
- Activity interests (beach, culture, adventure, family-friendly)

Return structured JSON with confidence scores for each entity.
```

#### **Step 2.2: Entity Resolution & Merging (15 min)**
- Handle entity conflicts (Rome vs Roma)
- Merge overlapping information
- Confidence scoring and priority
- Entity aging and relevance decay

### **Phase 3: Context Preservation & Enhancement (60 min)**

#### **Step 3.1: ContextPreservationService (30 min)**
```python
# services/context_preservation_service.py
class ContextPreservationService:
    def __init__(self, memory_service: ConversationMemoryService):
        self.memory_service = memory_service
        self.entity_priority = {
            "destination": 1.0,
            "budget": 0.9,
            "travel_dates": 0.8,
            "group_composition": 0.7,
            "accommodation": 0.6,
            "transport": 0.5,
            "activities": 0.4
        }
    
    async def build_conversation_context(self, session_id: str) -> ConversationContext
    async def prioritize_entities(self, entities: Dict[str, Any]) -> Dict[str, Any]
    async def generate_context_summary(self, session_id: str) -> str
    async def detect_context_switch(self, current_message: str, previous_context: ConversationContext) -> bool
    async def handle_context_reset(self, session_id: str, new_context_hints: Dict[str, Any])
```

#### **Step 3.2: ContextAwareEnhancer Integration (30 min)**
```python
# services/context_aware_enhancer.py
class ContextAwareEnhancer:
    def __init__(self, memory_service: ConversationMemoryService, entity_extractor: NamedEntityExtractor):
        self.memory_service = memory_service
        self.entity_extractor = entity_extractor
    
    async def enhance_query_with_context(self, query: str, session_id: str) -> EnhancedQuery
    async def resolve_pronoun_references(self, query: str, context: ConversationContext) -> str
    async def add_implicit_filters(self, query: str, active_entities: Dict[str, Any]) -> Dict[str, Any]
    async def detect_follow_up_intent(self, query: str, conversation_history: List[ConversationMessage]) -> str
```

**Context Enhancement Examples:**
```python
# Input: "Koliko košta?"
# Context: Previous query about "Hotel Roma Palace"
# Enhanced: "Koliko košta Hotel Roma Palace u Rimu?"

# Input: "Ima li spa?"
# Context: Active destination=Rome, accommodation=hotels
# Enhanced: "Koji hoteli u Rimu imaju spa centar?"

# Input: "A šta u Parizu?"
# Context: Previous query about Rome hotels
# Enhanced: "Koji hoteli u Parizu preporučujete?" + context_switch_detected=True
```

### **Phase 4: Self-Querying Service Integration (30 min)**

#### **Step 4.1: Enhanced Self-Querying (20 min)**
```python
# Modify services/self_querying_service.py
class SelfQueryingService:
    def __init__(self, openai_client, context_enhancer: ContextAwareEnhancer):
        self.client = openai_client
        self.context_enhancer = context_enhancer
    
    async def parse_query_with_context(self, query: str, session_id: str) -> StructuredQuery:
        # 1. Enhance query with conversation context
        enhanced_query = await self.context_enhancer.enhance_query_with_context(query, session_id)
        
        # 2. Extract structured filters (existing logic)
        structured_query = await self.parse_natural_language_query(enhanced_query.text)
        
        # 3. Merge context-derived filters
        structured_query.filters.update(enhanced_query.implicit_filters)
        
        return structured_query
```

#### **Step 4.2: Filter Inheritance Logic (10 min)**
- Persistent filters (destination, budget) vs temporary (specific hotel)
- Filter priority rules (explicit > context > default)
- Conflict resolution strategies

### **Phase 5: API Endpoints Update (30 min)**

#### **Step 5.1: Enhanced Chat Endpoint (20 min)**
```python
# Update routers/documents.py or create routers/chat.py
@router.post("/chat/message", response_model=EnhancedChatResponse)
async def enhanced_chat_message(
    message: ChatMessage, 
    session_id: str,
    conversation_memory_service: ConversationMemoryService = Depends()
):
    # 1. Save user message to conversation history
    await conversation_memory_service.save_user_message(session_id, message.content)
    
    # 2. Enhanced RAG pipeline with context
    enhanced_query = await context_aware_enhancer.enhance_query_with_context(message.content, session_id)
    structured_query = await self_querying_service.parse_query_with_context(enhanced_query, session_id)
    expanded_query = await query_expansion_service.expand_query(structured_query.text)
    search_results = await vector_service.search_with_filters(expanded_query, structured_query.filters)
    response = await response_generator.generate_response(search_results, enhanced_query)
    
    # 3. Save AI response and extract entities
    await conversation_memory_service.save_ai_response(session_id, response.text)
    await conversation_memory_service.extract_and_save_entities(session_id, message.content, response.text)
    
    return EnhancedChatResponse(
        response=response.text,
        sources=response.sources,
        suggested_questions=response.suggested_questions,
        conversation_context=await conversation_memory_service.get_context_summary(session_id),
        active_entities=await conversation_memory_service.get_active_entities(session_id)
    )
```

#### **Step 5.2: Memory Management Endpoints (10 min)**
```python
@router.get("/sessions/{session_id}/context")
async def get_conversation_context(session_id: str)

@router.post("/sessions/{session_id}/reset-context")
async def reset_conversation_context(session_id: str)

@router.get("/sessions/{session_id}/entities")  
async def get_active_entities(session_id: str)

@router.delete("/sessions/{session_id}/entity/{entity_type}")
async def remove_entity_from_context(session_id: str, entity_type: str)
```

## 🧪 Testing Strategy

### **Unit Tests**
```python
# tests/test_conversation_memory.py
async def test_entity_extraction()
async def test_context_preservation()
async def test_query_enhancement()
async def test_conversation_window_management()
async def test_context_switch_detection()
```

### **Integration Tests**
```python
# tests/test_conversation_flows.py
async def test_multi_turn_hotel_booking()
async def test_budget_context_preservation()
async def test_destination_context_switch()
async def test_pronoun_reference_resolution()
```

### **Demo Scenarios**
```python
# Demo Flow 1: Hotel Booking
# User: "Tražim hotel u Rimu"
# AI: "Evo nekoliko odličnih hotela u Rimu..."
# User: "Koliko košta?" 
# AI: [Context: Hotel Roma Palace] "Hotel Roma Palace košta 150€ po noći..."
# User: "Ima li spa?"
# AI: [Context: Hotel Roma Palace] "Da, Hotel Roma Palace ima luksuzni spa centar..."

# Demo Flow 2: Budget Planning  
# User: "Budžet mi je 500 EUR"
# AI: "Razumem, tražite aranžmane do 500€..."
# User: "Grčka u junu"
# AI: [Context: budget=500EUR] "Za budžet od 500€ u Grčkoj u junu preporučujem..."
# User: "Sa decom"
# AI: [Context: budget=500EUR, destination=Greece, dates=June] "Family-friendly hoteli u Grčkoj..."

# Demo Flow 3: Context Switch
# User: "Hoteli u Rimu"
# AI: "Evo pregleda hotela u Rimu..."
# User: "A šta u Parizu?"
# AI: [Detektovano: context switch] "Prebacujemo na Pariz. Evo hotela u Parizu..."
```

## 📊 Performance Considerations

### **Memory Optimization**
- JSON file caching (in-memory for active sessions)
- Lazy loading conversation history
- Entity compression for long conversations
- Automatic cleanup of expired sessions

### **Response Time Targets**
- Entity extraction: < 500ms
- Context enhancement: < 300ms  
- Total conversation-aware response: < 3.5s (0.5s overhead)

### **Error Handling**
- Graceful degradation when context unavailable
- Retry mechanisms for file I/O operations
- Fallback to context-free mode on errors
- User notifications for context reset

## 🎯 Success Metrics

### **Functional Requirements**
- ✅ Multi-turn conversation flows (3+ exchanges)
- ✅ Entity persistence across conversation
- ✅ Context-aware query understanding
- ✅ Pronoun and reference resolution
- ✅ Context switch detection

### **Performance Requirements**
- ✅ Response time < 3.5s for context-aware queries
- ✅ Memory usage < 50MB per active session
- ✅ 95% uptime with conversation persistence
- ✅ Graceful handling of 100+ concurrent sessions

### **User Experience**
- ✅ Natural conversation flow
- ✅ Transparent context usage ("Based on our previous discussion...")
- ✅ Easy context reset options
- ✅ Visual indicators for active entities

## 🚀 Implementation Timeline

### **Hour 1: Core Infrastructure**
- ConversationMemoryService setup
- JSON storage implementation
- Basic data models

### **Hour 2: Entity Extraction**
- NamedEntityExtractor implementation
- Tourism-specific entity recognition
- Entity merging and resolution

### **Hour 3: Context Enhancement**
- ContextAwareEnhancer integration
- Self-Querying Service updates
- Query enhancement logic

### **Hour 4: Testing & Integration**
- Unit and integration tests
- Demo scenario preparation
- Frontend integration updates
- Performance optimization

## 📝 File Changes Required

### **New Files:**
```
app/backend/services/conversation_memory_service.py
app/backend/services/named_entity_extractor.py
app/backend/services/context_preservation_service.py
app/backend/services/context_aware_enhancer.py
app/backend/models/conversation.py
app/backend/conversation_data/ (directory)
app/backend/tests/test_conversation_memory.py
app/backend/tests/test_conversation_flows.py
```

### **Modified Files:**
```
app/backend/services/self_querying_service.py
app/backend/routers/documents.py (or new chat.py)
app/backend/main.py (dependency injection)
app/frontend/lib/api.ts (enhanced chat methods)
app/frontend/components/ChatBubble.tsx (context display)
```

## 🎭 Demo Presentation Strategy

### **Demo Script:**
1. **Introduction** (30s): "Enhanced conversation memory for natural travel planning"
2. **Flow 1** (90s): Multi-turn hotel booking with context preservation
3. **Flow 2** (90s): Budget and preference tracking across conversation
4. **Flow 3** (60s): Context switch detection and handling
5. **Technical** (30s): Show active entities and conversation history UI

### **Key Selling Points:**
- ✅ **Natural conversations**: No need to repeat information
- ✅ **Smart context**: Understanding "that hotel", "how much", "with kids"
- ✅ **Persistent memory**: Context survives page refresh
- ✅ **Transparent AI**: Show what context is being used
- ✅ **Professional UX**: Clean integration with existing interface

---

**Ready to implement!** 🚀  
*Estimated time: 3-4 hours*  
*Impact: Major UX improvement + hakaton differentiator* 