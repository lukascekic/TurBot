"use client"

import * as React from "react"
import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { MessageCircle, X, Send, Bot, User, FileText, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"
import turBotAPI, { ChatMessage, ChatResponse, Source } from "@/lib/api"
import ReactMarkdown from 'react-markdown'

interface ChatBubbleProps {
  isOpen: boolean
  onToggle: () => void
  userType?: 'client' | 'agent'
  sessionId?: string
  className?: string
}

export default function ChatBubble({ 
  isOpen, 
  onToggle, 
  userType = 'client',
  sessionId,
  className 
}: ChatBubbleProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: "Zdravo! Ja sam RBTours AI asistent. Kako mogu da vam pomognem sa planiranjem vašeg putovanja?",
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // ==================== STREAMING STATE ====================
  // Added for real-time streaming - does not affect existing functionality
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState("")

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Check API health on mount
    const checkHealth = async () => {
      try {
        const healthy = await turBotAPI.healthCheck()
        setIsConnected(healthy)
      } catch (error) {
        setIsConnected(false)
      }
    }
    checkHealth()
  }, [])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isTyping || isStreaming) return

    // Try streaming first, fallback to regular chat
    if (sessionId) {
      await handleSendMessageStreaming()
    } else {
      await handleSendMessageRegular()
    }
  }

  // ==================== STREAMING MESSAGE HANDLER ====================
  // New streaming functionality - does not replace existing method
  const handleSendMessageStreaming = async () => {
    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    const messageText = inputValue
    setInputValue("")
    setIsStreaming(true)
    setStreamingContent("")

    // Store the complete response content
    let completeResponse = ""

    try {
      await turBotAPI.chatStreamEnhanced(messageText, sessionId!, userType, {
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

          setMessages((prev) => [...prev, assistantMessage])
          setStreamingContent("")
          setIsConnected(true)
        },
        onError: (error: string) => {
          console.error('Streaming error:', error)
          setIsConnected(false)
          
          const errorMessage: ChatMessage = {
            role: 'assistant',
            content: "Izvinjavam se, došlo je do greške sa streaming-om. Pokušavam standardni način...",
            timestamp: new Date(),
          }
          setMessages((prev) => [...prev, errorMessage])
          
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
    if (!inputValue.trim() && !isStreaming) return

    const messageText = inputValue || "Ponovi poslednji odgovor"
    
    if (!isStreaming) {
      const userMessage: ChatMessage = {
        role: 'user',
        content: messageText,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMessage])
      setInputValue("")
    }
    
    setIsTyping(true)

    try {
      const response: ChatResponse = await turBotAPI.chat(
        messageText, 
        sessionId, 
        userType
      )

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        sources: response.sources,
        suggested_questions: response.suggested_questions,
      }

      setMessages((prev) => [...prev, assistantMessage])
      setIsConnected(true)
    } catch (error) {
      console.error('Chat error:', error)
      setIsConnected(false)
      
      // Add error message
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: "Izvinjavam se, trenutno imam problema sa povezivanjem. Molim vas pokušajte ponovo za nekoliko sekundi.",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
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

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion)
  }

  if (!isOpen) {
    return (
      <div className={cn("fixed bottom-4 right-4 z-50", className)}>
        <button 
          onClick={onToggle}
          className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-red-600 hover:bg-red-700 shadow-lg text-white flex items-center justify-center transition-colors"
        >
          <MessageCircle className="h-5 w-5 sm:h-6 sm:w-6" />
        </button>
      </div>
    )
  }

  return (
    <div className={cn("fixed bottom-4 right-4 z-50", className)}>
      <Card className="w-96 h-[500px] max-w-[90vw] max-h-[80vh] shadow-xl border-2 border-red-600">
        <CardHeader className="bg-red-600 text-white p-4 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Bot className="h-5 w-5" />
              <CardTitle className="text-sm">RBTours AI Asistent</CardTitle>
            </div>
            <button 
              onClick={onToggle}
              className="text-white hover:bg-red-700 p-1 rounded transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex items-center space-x-1 text-xs">
            <div className={cn(
              "w-2 h-2 rounded-full",
              isConnected ? "bg-green-400" : "bg-red-400"
            )}></div>
            <span>{isConnected ? "Online" : "Offline"}</span>
          </div>
        </CardHeader>

        <CardContent className="p-0 flex flex-col h-[420px]">
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}

            {/* ==================== STREAMING DISPLAY ==================== */}
            {/* Real-time streaming content display */}
            {isStreaming && streamingContent && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-2 max-w-[85%]">
                  <div className="w-6 h-6 bg-red-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot className="h-3 w-3 text-white" />
                  </div>
                  <div className="bg-gray-100 p-3 rounded-lg overflow-hidden">
                    <div className="text-sm text-gray-800 break-words prose prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                      <ReactMarkdown 
                        components={{
                          p: ({ children }) => <p className="mb-1 last:mb-0 inline break-words">{children}</p>,
                          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                          em: ({ children }) => <em className="italic">{children}</em>,
                          code: ({ children }) => <code className="bg-gray-200 px-1 py-0.5 rounded text-xs break-all">{children}</code>,
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
                <div className="flex items-start space-x-2">
                  <div className="w-6 h-6 bg-red-600 rounded-full flex items-center justify-center">
                    <Bot className="h-3 w-3 text-white" />
                  </div>
                  <div className="bg-gray-100 p-3 rounded-lg">
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

          <div className="p-3 border-t bg-white">
            <div className="flex space-x-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Kucajte poruku..."
                className="flex-1 text-sm"
                disabled={isTyping || isStreaming || !isConnected}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isTyping || isStreaming || !isConnected}
                className="bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white p-2 rounded-md transition-colors"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

interface MessageBubbleProps {
  message: ChatMessage
}

function MessageBubble({ message }: MessageBubbleProps) {
  return (
    <div className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`flex items-start space-x-2 max-w-[85%]`}>
        {message.role === "assistant" && (
          <div className="w-6 h-6 bg-red-600 rounded-full flex items-center justify-center flex-shrink-0">
            <Bot className="h-3 w-3 text-white" />
          </div>
        )}
        <div className="space-y-2 overflow-hidden">
          <div
            className={cn(
              "p-3 rounded-lg text-sm overflow-hidden",
              message.role === "user" 
                ? "bg-black text-white" 
                : "bg-gray-100 text-black"
            )}
          >
            <div className="prose prose-sm max-w-none break-words [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
              <ReactMarkdown 
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0 break-words">{children}</p>,
                  ul: ({ children }) => <ul className="mb-2 ml-4 list-disc">{children}</ul>,
                  ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal">{children}</ol>,
                  li: ({ children }) => <li className="mb-1 break-words">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  code: ({ children }) => <code className="bg-gray-200 px-1 py-0.5 rounded text-xs break-all">{children}</code>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
          
          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className="bg-gray-50 p-2 rounded-lg border text-xs">
              <div className="flex items-center space-x-1 mb-1">
                <FileText className="h-3 w-3 text-gray-500" />
                <span className="text-gray-600 font-medium">Sources:</span>
              </div>
              <div className="space-y-1">
                {message.sources.map((source: Source, index: number) => (
                  <div key={index} className="flex items-center justify-between">
                    <span className="text-gray-700 truncate">{source.document_name}</span>
                    <span className="text-gray-500">
                      {(source.similarity * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested Questions */}
          {message.suggested_questions && message.suggested_questions.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs text-gray-500">Možda vas zanima:</span>
              {message.suggested_questions.map((question: string, index: number) => (
                <button
                  key={index}
                  onClick={() => {/* Handle suggestion click */}}
                  className="block w-full text-left text-xs text-blue-600 hover:text-blue-800 hover:underline p-1 rounded"
                >
                  {question}
                </button>
              ))}
            </div>
          )}
        </div>
        {message.role === "user" && (
          <div className="w-6 h-6 bg-black rounded-full flex items-center justify-center flex-shrink-0">
            <User className="h-3 w-3 text-white" />
          </div>
        )}
      </div>
    </div>
  )
} 