"use client"

import * as React from "react"
import { useState, useRef, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { 
  Home, Plus, Send, Bot, User, Trash2, Settings, LogOut, Globe, MapPin, 
  Calendar, DollarSign, Plane, Upload, FileText, AlertCircle,
  CheckCircle, Clock, Menu, X
} from "lucide-react"
import { cn } from "@/lib/utils"
import turBotAPI, { ChatMessage, ChatResponse, DocumentInfo, DocumentStats } from "@/lib/api"
import ReactMarkdown from 'react-markdown'

interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  lastActivity: Date
  userType: string
}

export default function AgentPage() {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [documentStats, setDocumentStats] = useState<DocumentStats | null>(null)
  const [uploadingFile, setUploadingFile] = useState<File | null>(null)
  const [activeTab, setActiveTab] = useState<'chat' | 'documents'>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // ==================== STREAMING STATE ====================
  // Added for real-time streaming on agent page
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState("")

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load document stats
        const stats = await turBotAPI.getDocumentStats()
        setDocumentStats(stats)

        // Load document list
        const docList = await turBotAPI.getDocumentList()
        setDocuments(docList)

        // Create initial session
        const session = await turBotAPI.createSession('agent')
        const newSession: ChatSession = {
          id: session.session_id,
          title: "Nova sesija",
          messages: [{
            role: 'assistant',
            content: "Zdravo! Ja sam vaš AI asistent za RBTours. Mogu da vam pomognem sa informacijama o destinacijama, cenama, letovima, hotelima i svim drugim pitanjima vezanim za turizam. Kako mogu da vam pomognem?",
            timestamp: new Date(),
          }],
          lastActivity: new Date(),
          userType: 'agent'
        }
        setChatSessions([newSession])
        setCurrentSessionId(newSession.id)
      } catch (error) {
        console.error('Failed to load initial data:', error)
      }
    }

    loadData()
  }, [])

  const currentSession = chatSessions.find((session) => session.id === currentSessionId)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [currentSession?.messages])

  const createNewChat = async () => {
    try {
      // Generate user identifier (in production, use proper auth)
      const userIdentifier = localStorage.getItem('turbot_user_id') || `agent_${Date.now()}`
      localStorage.setItem('turbot_user_id', userIdentifier)
      
      // Create new session with user identification
      const session = await turBotAPI.createSessionWithUser('agent', userIdentifier)
      
      const newSession: ChatSession = {
        id: session.session_id,
        title: "Nova sesija",
        messages: [{
          role: 'assistant',
          content: "Zdravo! Kako mogu da vam pomognem danas?",
          timestamp: new Date(),
        }],
        lastActivity: new Date(),
        userType: 'agent'
      }
      setChatSessions((prev) => [newSession, ...prev])
      setCurrentSessionId(newSession.id)
    } catch (error) {
      console.error('Failed to create new session:', error)
    }
  }

  const deleteChat = async (sessionId: string) => {
    try {
      // Reset conversation memory on backend
      await turBotAPI.resetSession(sessionId)
      
      // Remove from frontend state
    setChatSessions((prev) => prev.filter((session) => session.id !== sessionId))
      
    if (currentSessionId === sessionId) {
      const remainingSessions = chatSessions.filter((session) => session.id !== sessionId)
      if (remainingSessions.length > 0) {
        setCurrentSessionId(remainingSessions[0].id)
      } else {
        createNewChat()
      }
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
      // Still remove from frontend even if backend fails
      setChatSessions((prev) => prev.filter((session) => session.id !== sessionId))
    }
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentSession || isTyping || isStreaming) return

    // Agent stranica koristi streaming endpoint (isti kao client stranica)
    // Client stranica koristi streaming i daje kratke, kvalitetne odgovore
    await handleSendMessageStreaming()
  }

  // ==================== STREAMING MESSAGE HANDLER ====================
  // New streaming functionality for agent page
  const handleSendMessageStreaming = async () => {
    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    }

    // Update current session with user message
    setChatSessions((prev) =>
      prev.map((session) =>
        session.id === currentSessionId
          ? {
              ...session,
              messages: [...session.messages, userMessage],
              title: session.title === "Nova sesija" ? inputValue.slice(0, 30) + "..." : session.title,
              lastActivity: new Date(),
            }
          : session,
      ),
    )

    const messageText = inputValue
    setInputValue("")
    setIsStreaming(true)
    setStreamingContent("")

    // Store the complete response content
    let completeResponse = ""

    try {
      await turBotAPI.chatStreamEnhanced(messageText, currentSessionId!, 'agent', {
        onChunk: (chunk: string) => {
          completeResponse += chunk
          setStreamingContent(completeResponse)
        },
        onComplete: (metadata) => {
          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: completeResponse || "Izvinjavam se, odgovor nije generisan.",
            timestamp: new Date(),
            sources: metadata.sources.map(source => ({
              document_name: source,
              similarity: 0.9,
              content_preview: "",
              metadata: {}
            })),
            suggested_questions: metadata.suggestions,
          }

          setChatSessions((prev) =>
            prev.map((session) =>
              session.id === currentSessionId
                ? {
                    ...session,
                    messages: [...session.messages, assistantMessage],
                    lastActivity: new Date(),
                  }
                : session,
            ),
          )
          setStreamingContent("")
        },
        onError: (error: string) => {
          console.error('Streaming error:', error)
          
          const errorMessage: ChatMessage = {
            role: 'assistant',
            content: "Izvinjavam se, došlo je do greške sa streaming-om. Pokušavam standardni način...",
            timestamp: new Date(),
          }
          setChatSessions((prev) =>
            prev.map((session) =>
              session.id === currentSessionId
                ? {
                    ...session,
                    messages: [...session.messages, errorMessage],
                    lastActivity: new Date(),
                  }
                : session,
            ),
          )
          
          // Fallback to regular chat
          handleSendMessageRegular()
        }
      })
    } catch (error) {
      console.error('Streaming setup error:', error)
      // Fallback to regular chat
      await handleSendMessageRegular()
    } finally {
      setIsStreaming(false)
      setStreamingContent("")
    }
  }

  // ==================== REGULAR MESSAGE HANDLER ====================
  // Original functionality preserved as fallback
  const handleSendMessageRegular = async () => {
    if (!currentSession) return

    const messageText = inputValue || "Ponovi poslednji odgovor"
    
    if (!isStreaming) {
      const userMessage: ChatMessage = {
        role: 'user',
        content: messageText,
        timestamp: new Date(),
      }

      // Update current session with user message
      setChatSessions((prev) =>
        prev.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: [...session.messages, userMessage],
                title: session.title === "Nova sesija" ? messageText.slice(0, 30) + "..." : session.title,
                lastActivity: new Date(),
              }
            : session,
        ),
      )
      setInputValue("")
    }
    
    setIsTyping(true)

    try {
      const response: ChatResponse = await turBotAPI.chat(messageText, currentSessionId!, 'agent')
      
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        sources: response.sources,
        suggested_questions: response.suggested_questions,
      }

      setChatSessions((prev) =>
        prev.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: [...session.messages, assistantMessage],
                lastActivity: new Date(),
              }
            : session,
        ),
      )
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: "Izvinjavam se, došlo je do greške. Molim pokušajte ponovo.",
        timestamp: new Date(),
      }
      setChatSessions((prev) =>
        prev.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: [...session.messages, errorMessage],
                lastActivity: new Date(),
              }
            : session,
        ),
      )
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.includes('pdf')) {
      alert('Molim odaberite PDF fajl')
      return
    }

    setUploadingFile(file)

    try {
      await turBotAPI.uploadDocument(file)
      
      // Refresh document list and stats
      const [newDocList, newStats] = await Promise.all([
        turBotAPI.getDocumentList(),
        turBotAPI.getDocumentStats()
      ])
      
      setDocuments(newDocList)
      setDocumentStats(newStats)
      
      alert('Dokument je uspešno otpremljen!')
    } catch (error) {
      console.error('Upload error:', error)
      alert('Greška pri otpremanju dokumenta')
    } finally {
      setUploadingFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDeleteDocument = async (filename: string) => {
    if (!confirm(`Da li ste sigurni da želite da obrišete ${filename}?`)) return

    try {
      await turBotAPI.deleteDocument(filename)
      
      // Refresh document list and stats
      const [newDocList, newStats] = await Promise.all([
        turBotAPI.getDocumentList(),
        turBotAPI.getDocumentStats()
      ])
      
      setDocuments(newDocList)
      setDocumentStats(newStats)
    } catch (error) {
      console.error('Delete error:', error)
      alert('Greška pri brisanju dokumenta')
    }
  }

  const quickPrompts = [
    { icon: MapPin, text: "Najbolje destinacije za leto 2024", prompt: "Koje su najbolje destinacije za leto 2024?" },
    { icon: DollarSign, text: "Budget putovanja do €500", prompt: "Preporuči mi destinacije za budžet do €500 po osobi" },
    { icon: Plane, text: "Jeftini letovi iz Beograda", prompt: "Koji su najjeftiniji letovi iz Beograda trenutno?" },
    { icon: Calendar, text: "Last minute ponude", prompt: "Koje su trenutne last minute ponude?" },
  ]

  return (
    <div className="flex h-screen bg-white relative">
      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <div className={cn(
        "fixed lg:static inset-y-0 left-0 z-50 w-80 bg-gray-50 border-r border-gray-200 flex flex-col transform transition-transform duration-300 ease-in-out",
        sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Globe className="h-6 w-6 text-red-600" />
              <h1 className="font-bold text-black">RBTours AI</h1>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => window.location.href = "/"}
                className="text-gray-600 hover:text-red-600 p-2 rounded transition-colors"
              >
                <Home className="h-4 w-4" />
              </button>
              <button
                onClick={() => setSidebarOpen(false)}
                className="lg:hidden text-gray-600 hover:text-red-600 p-2 rounded transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
          
          {/* Tab Navigation */}
          <div className="flex mb-4">
            <button
              onClick={() => setActiveTab('chat')}
              className={cn(
                "flex-1 py-2 px-3 text-xs sm:text-sm font-medium rounded-l-md transition-colors",
                activeTab === 'chat'
                  ? "bg-red-600 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              )}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={cn(
                "flex-1 py-2 px-3 text-xs sm:text-sm font-medium rounded-r-md transition-colors",
                activeTab === 'documents'
                  ? "bg-red-600 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              )}
            >
              Dokumenti
            </button>
          </div>

          {activeTab === 'chat' && (
            <button onClick={createNewChat} className="w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded transition-colors">
              <Plus className="h-4 w-4 mr-2 inline" />
              Novi razgovor
            </button>
          )}

          {activeTab === 'documents' && (
            <div>
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded transition-colors mb-4"
                disabled={!!uploadingFile}
              >
                <Upload className="h-4 w-4 mr-2 inline" />
                {uploadingFile ? 'Otpremanje...' : 'Otpremi PDF'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
              />
              
              {/* Document Stats */}
              {documentStats && (
                <div className="bg-white rounded-lg p-3 shadow-sm">
                  <h3 className="text-sm font-semibold mb-2">📊 Statistike</h3>
                  <div className="space-y-1 text-xs">
                    <div>📄 {documentStats.total_documents} dokumenata</div>
                    <div>📍 {documentStats.locations?.length || 0} lokacija</div>
                    <div>📂 {documentStats.categories?.length || 0} kategorija</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden max-h-64 lg:max-h-none">
          {activeTab === 'chat' && (
            <div className="h-full overflow-y-auto p-2">
              <div className="space-y-2">
                {chatSessions.map((session) => (
                  <div
                    key={session.id}
                    className={cn(
                      "p-3 rounded-lg cursor-pointer transition-colors group",
                      currentSessionId === session.id 
                        ? "bg-red-100 border border-red-200" 
                        : "hover:bg-gray-100"
                    )}
                    onClick={() => setCurrentSessionId(session.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-black truncate">{session.title}</h3>
                        <p className="text-xs text-gray-500">{session.lastActivity.toLocaleDateString()}</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteChat(session.id)
                        }}
                        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-600 p-1 transition-colors"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="h-full overflow-y-auto p-2">
              <div className="space-y-2">
                {uploadingFile && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="flex items-center space-x-2 mb-2">
                      <Clock className="h-4 w-4 text-blue-600" />
                      <span className="text-sm font-medium">Otpremanje: {uploadingFile.name}</span>
                    </div>
                  </div>
                )}
                
                {documents && documents.length > 0 && documents.map((doc) => (
                  <div key={doc.filename} className="bg-white rounded-lg p-3 border shadow-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <FileText className="h-4 w-4 text-gray-500" />
                          <h4 className="text-sm font-medium text-black truncate">{doc.filename}</h4>
                        </div>
                        <div className="text-xs text-gray-500 space-y-1">
                          <div>📅 {new Date(doc.upload_date).toLocaleDateString()}</div>
                          <div>📊 {doc.chunks} chunks</div>
                          <div className="flex items-center space-x-1">
                            {doc.status === 'processed' ? (
                              <CheckCircle className="h-3 w-3 text-green-600" />
                            ) : (
                              <AlertCircle className="h-3 w-3 text-yellow-600" />
                            )}
                            <span>{doc.status}</span>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteDocument(doc.filename)}
                        className="text-gray-400 hover:text-red-600 p-1 transition-colors"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center space-x-2">
              <User className="h-4 w-4" />
              <span>Agent Miloš</span>
            </div>
            <div className="flex space-x-2">
              <button className="text-gray-400 hover:text-gray-600 p-1 transition-colors">
                <Settings className="h-4 w-4" />
              </button>
              <button className="text-gray-400 hover:text-gray-600 p-1 transition-colors">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-0 lg:ml-0">
        {currentSession ? (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-gray-200 bg-white">
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="lg:hidden p-2 hover:bg-gray-100 rounded-md"
                >
                  <Menu className="h-5 w-5" />
                </button>
                <div>
                  <h2 className="text-lg font-semibold text-black">{currentSession.title}</h2>
                  <p className="text-sm text-gray-500">AI asistent za turističke informacije</p>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-2 sm:p-4">
              <div className="max-w-4xl mx-auto space-y-4 sm:space-y-6">
                {currentSession.messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`flex items-start space-x-2 sm:space-x-3 max-w-[90%] sm:max-w-[80%]`}>
                      {message.role === "assistant" && (
                        <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center flex-shrink-0">
                          <Bot className="h-4 w-4 text-white" />
                        </div>
                      )}
                      <div
                        className={cn(
                          "p-3 sm:p-4 rounded-lg text-sm sm:text-base",
                          message.role === "user" 
                            ? "bg-black text-white" 
                            : "bg-gray-100 text-black border"
                        )}
                      >
                        <div className="prose prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                          <ReactMarkdown 
                            components={{
                              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                              ul: ({ children }) => <ul className="mb-2 ml-4 list-disc">{children}</ul>,
                              ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal">{children}</ol>,
                              li: ({ children }) => <li className="mb-1">{children}</li>,
                              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                              em: ({ children }) => <em className="italic">{children}</em>,
                              code: ({ children }) => <code className="bg-gray-200 px-1 py-0.5 rounded text-xs">{children}</code>,
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                        <div
                          className={cn(
                            "text-xs mt-2",
                            message.role === "user" ? "text-gray-300" : "text-gray-500"
                          )}
                        >
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                        
                        {/* Sources */}
                        {message.sources && message.sources.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <div className="flex items-center space-x-1 mb-2">
                              <FileText className="h-3 w-3 text-gray-500" />
                              <span className="text-xs font-medium">Sources:</span>
                            </div>
                            <div className="space-y-1">
                              {message.sources.map((source, sourceIndex) => (
                                <div key={sourceIndex} className="text-xs bg-gray-50 p-2 rounded">
                                  <div className="font-medium">{source.document_name}</div>
                                  <div className="text-gray-500">
                                    Relevance: {(source.similarity * 100).toFixed(0)}%
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      {message.role === "user" && (
                        <div className="w-8 h-8 bg-black rounded-full flex items-center justify-center flex-shrink-0">
                          <User className="h-4 w-4 text-white" />
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* ==================== STREAMING DISPLAY ==================== */}
                {/* Real-time streaming content display */}
                {isStreaming && streamingContent && (
                  <div className="flex justify-start">
                    <div className="flex items-start space-x-3 max-w-[90%] sm:max-w-[80%]">
                      <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center flex-shrink-0">
                        <Bot className="h-4 w-4 text-white" />
                      </div>
                      <div className="bg-gray-100 p-3 sm:p-4 rounded-lg border overflow-hidden">
                        <div className="text-sm sm:text-base text-black break-words prose prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                          <ReactMarkdown 
                            components={{
                              p: ({ children }) => <p className="mb-1 last:mb-0 inline">{children}</p>,
                              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                              em: ({ children }) => <em className="italic">{children}</em>,
                              code: ({ children }) => <code className="bg-gray-200 px-1 py-0.5 rounded text-xs">{children}</code>,
                            }}
                          >
                            {streamingContent}
                          </ReactMarkdown>
                          <span className="inline-block w-2 h-4 bg-red-600 ml-1 animate-pulse"></span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Regular typing indicator (fallback) */}
                {(isTyping || (isStreaming && !streamingContent)) && (
                  <div className="flex justify-start">
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center">
                        <Bot className="h-4 w-4 text-white" />
                      </div>
                      <div className="bg-gray-100 p-4 rounded-lg border">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div
                            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                            style={{ animationDelay: "0.1s" }}
                          ></div>
                          <div
                            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                            style={{ animationDelay: "0.2s" }}
                          ></div>
                        </div>
                        {isStreaming && (
                          <div className="text-xs text-gray-500 mt-1">Kucam...</div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Quick Prompts */}
            {currentSession.messages.length <= 1 && (
              <div className="p-2 sm:p-4 border-t border-gray-100">
                <div className="max-w-4xl mx-auto">
                  <p className="text-xs sm:text-sm text-gray-600 mb-3">Brzi upiti:</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {quickPrompts.map((prompt, index) => (
                      <button
                        key={index}
                        className="justify-start text-left h-auto p-3 border border-gray-200 hover:border-red-600 hover:text-red-600 rounded-lg transition-colors"
                        onClick={() => setInputValue(prompt.prompt)}
                      >
                        <prompt.icon className="h-4 w-4 mr-2 inline flex-shrink-0" />
                        <span className="text-sm">{prompt.text}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Input Area */}
            <div className="p-2 sm:p-4 border-t border-gray-200 bg-white">
              <div className="max-w-4xl mx-auto">
                <div className="flex space-x-2 sm:space-x-3">
                  <div className="flex-1 relative">
                                          <Input
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Postavite pitanje..."
                        className="min-h-[40px] sm:min-h-[50px] text-sm"
                        disabled={isTyping || isStreaming}
                      />
                  </div>
                                      <button
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || isTyping || isStreaming}
                      className="bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 sm:px-4 py-2 rounded-md transition-colors"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                </div>
                <p className="text-xs text-gray-500 mt-2 text-center">
                  AI može da pravi greške. Proverite važne informacije.
                </p>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden mb-4 p-2 hover:bg-gray-100 rounded-md mx-auto"
              >
                <Menu className="h-6 w-6" />
              </button>
              <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Dobrodošli u RBTours AI</h3>
              <p className="text-gray-500 mb-4">Kreirajte novi razgovor da počnete</p>
              <button
                onClick={createNewChat}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors"
              >
                Početak razgovora
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
