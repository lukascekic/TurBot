import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Source[];
  suggested_questions?: string[];
}

export interface Source {
  document_name: string;
  similarity: number;
  content_preview: string;
  metadata: any;
}

export interface ChatResponse {
  response: string;
  sources: Source[];
  suggested_questions: string[];
  session_id?: string;
  confidence: number;
  structured_data: {
    total_results: number;
    price_range: { min?: number; max?: number; currency: string };
    locations: string[];
    categories: string[];
    amenities: string[];
    average_similarity: number;
  };
}

export interface SessionResponse {
  session_id: string;
  user_type: string;
  created_at: string;
  last_active: string;
  message_count: number;
}

export interface DocumentStats {
  total_documents: number;
  categories: string[];
  locations: string[];
  average_confidence: number;
}

export interface DocumentInfo {
  filename: string;
  upload_date: string;
  size: number;
  status: string;
  chunks: number;
}

class TurBotAPI {
  private api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Chat endpoints
  async chat(message: string, sessionId?: string, userType: string = 'client'): Promise<ChatResponse> {
    try {
      const response = await this.api.post('/chat', {
        message,
        session_id: sessionId,
        user_type: userType,
      });
      return response.data;
    } catch (error) {
      console.error('Chat API error:', error);
      throw new Error('Failed to get response from AI assistant');
    }
  }

  async simpleChatSearch(query: string): Promise<any> {
    try {
      const response = await this.api.post('/chat/simple', { query });
      return response.data;
    } catch (error) {
      console.error('Simple chat search error:', error);
      throw error;
    }
  }

  // Session management
  async createSession(userType: string = 'client'): Promise<SessionResponse> {
    try {
      const response = await this.api.post('/sessions/create', { user_type: userType });
      return response.data;
    } catch (error) {
      console.error('Create session error:', error);
      throw error;
    }
  }

  async getSession(sessionId: string): Promise<SessionResponse> {
    try {
      const response = await this.api.get(`/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Get session error:', error);
      throw error;
    }
  }

  async getConversationHistory(sessionId: string): Promise<ChatMessage[]> {
    try {
      const response = await this.api.get(`/sessions/${sessionId}/history`);
      return response.data.messages;
    } catch (error) {
      console.error('Get conversation history error:', error);
      return [];
    }
  }

  // Document management
  async uploadDocument(file: File): Promise<any> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await this.api.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Upload document error:', error);
      throw error;
    }
  }

  async getDocumentStats(): Promise<DocumentStats> {
    try {
      const response = await this.api.get('/documents/stats');
      return response.data;
    } catch (error) {
      console.error('Get document stats error:', error);
      throw error;
    }
  }

  async getDocumentList(): Promise<DocumentInfo[]> {
    try {
      const response = await this.api.get('/documents/list');
      return response.data;
    } catch (error) {
      console.error('Get document list error:', error);
      return [];
    }
  }

  async deleteDocument(filename: string): Promise<any> {
    try {
      const response = await this.api.delete(`/documents/${filename}`);
      return response.data;
    } catch (error) {
      console.error('Delete document error:', error);
      throw error;
    }
  }

  async getCategories(): Promise<string[]> {
    try {
      const response = await this.api.get('/documents/categories');
      return response.data.categories;
    } catch (error) {
      console.error('Get categories error:', error);
      return [];
    }
  }

  async getLocations(): Promise<string[]> {
    try {
      const response = await this.api.get('/documents/locations');
      return response.data.locations;
    } catch (error) {
      console.error('Get locations error:', error);
      return [];
    }
  }

  async getSearchSuggestions(): Promise<string[]> {
    try {
      const response = await this.api.get('/documents/search-suggestions');
      return response.data.suggestions;
    } catch (error) {
      console.error('Get search suggestions error:', error);
      return [
        "Hotel u Rimu",
        "Letovanje Grčka",
        "Amsterdam maj",
        "Budžet €500",
        "Romantičan vikend",
        "Porodično putovanje"
      ];
    }
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.api.get('/health');
      return response.data.status === 'healthy';
    } catch (error) {
      console.error('Health check error:', error);
      return false;
    }
  }

  async resetSession(sessionId: string): Promise<void> {
    try {
      await this.api.delete(`/sessions/${sessionId}`);
    } catch (error) {
      console.error('Reset session error:', error);
      throw error;
    }
  }

  async createSessionWithUser(userType: 'client' | 'agent', userIdentifier?: string): Promise<SessionResponse> {
    try {
      const response = await this.api.post('/sessions/create-with-user', {
        user_type: userType,
        user_id: userIdentifier
      }, {
        params: userIdentifier ? { user_identifier: userIdentifier } : {}
      });
      return response.data;
    } catch (error) {
      console.error('Create session with user error:', error);
      throw error;
    }
  }

  async getUserSessions(userIdentifier: string): Promise<SessionResponse[]> {
    try {
      const response = await this.api.get(`/sessions/user/${userIdentifier}`);
      return response.data.user_sessions;
    } catch (error) {
      console.error('Get user sessions error:', error);
      return [];
    }
  }
}

export const turBotAPI = new TurBotAPI();
export default turBotAPI; 