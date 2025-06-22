"use client"

import { useState, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { MapPin, Phone, Mail, Star, Users, Globe, Calendar } from "lucide-react"
import ChatBubble from "@/components/ChatBubble"
import turBotAPI from "@/lib/api"

export default function HomePage() {
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [sessionId, setSessionId] = useState<string | undefined>()

  useEffect(() => {
    // Load search suggestions
    const loadSuggestions = async () => {
      try {
        const suggestionsData = await turBotAPI.getSearchSuggestions()
        setSuggestions(suggestionsData)
      } catch (error) {
        console.error('Failed to load suggestions:', error)
      }
    }

    // Create session for client
    const createSession = async () => {
      try {
        const session = await turBotAPI.createSession('client')
        setSessionId(session.session_id)
      } catch (error) {
        console.error('Failed to create session:', error)
      }
    }

    loadSuggestions()
    createSession()
  }, [])

  const handleSuggestionClick = (suggestion: string) => {
    setIsChatOpen(true)
    // Pass suggestion to chat bubble - would need to modify ChatBubble to accept initial message
  }

  const createNewSession = async () => {
    try {
      // Generate user identifier for client (in production, use proper auth)
      const userIdentifier = localStorage.getItem('turbot_client_id') || `client_${Date.now()}`
      localStorage.setItem('turbot_client_id', userIdentifier)
      
      // Create new session with user identification
      const sessionResponse = await turBotAPI.createSessionWithUser('client', userIdentifier)
      const newSessionId = sessionResponse.session_id
      
      setSessionId(newSessionId)
      localStorage.setItem('turbot_session_id', newSessionId)
      
      return newSessionId
    } catch (error) {
      console.error('Failed to create new session:', error)
      // Fallback to timestamp-based session
      const fallbackSessionId = `client_${Date.now()}`
      setSessionId(fallbackSessionId)
      localStorage.setItem('turbot_session_id', fallbackSessionId)
      return fallbackSessionId
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-white border-b-2 border-red-600 shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Globe className="h-8 w-8 text-red-600" />
              <h1 className="text-2xl font-bold text-black">RBTours</h1>
            </div>
            <nav className="hidden md:flex space-x-6">
              <a href="#" className="text-black hover:text-red-600 transition-colors">
                Destinacije
              </a>
              <a href="#" className="text-black hover:text-red-600 transition-colors">
                Paketi
              </a>
              <a href="#" className="text-black hover:text-red-600 transition-colors">
                O nama
              </a>
              <a href="#" className="text-black hover:text-red-600 transition-colors">
                Kontakt
              </a>
            </nav>
            <button
              onClick={() => window.location.href = "/agent"}
              className="bg-black text-white border-black hover:bg-red-600 hover:border-red-600 px-4 py-2 rounded transition-colors"
            >
              Agent AI Asistent
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-r from-red-600 to-black text-white py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-5xl font-bold mb-6">Otkrijte Svet sa RBTours</h2>
          <p className="text-xl mb-8 max-w-2xl mx-auto">
            Vaša avantura počinje ovde. Nudimo nezaboravna putovanja po celom svetu sa profesionalnim vodičima i
            vrhunskim servisom.
          </p>
          <button
            className="bg-white text-red-600 hover:bg-gray-100 text-lg px-8 py-3 rounded-lg transition-colors"
            onClick={() => setIsChatOpen(true)}
          >
            Počnite Razgovor sa AI Asistentom
          </button>
        </div>
      </section>

      {/* Quick Search Section */}
      {suggestions.length > 0 && (
        <section className="py-12 bg-gray-50">
          <div className="container mx-auto px-4">
            <h3 className="text-3xl font-bold text-center text-black mb-8">💡 Brze pretrage</h3>
            <div className="flex flex-wrap justify-center gap-3 max-w-4xl mx-auto">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  className="px-6 py-3 bg-red-100 text-red-800 rounded-full hover:bg-red-200 transition-colors text-sm font-medium"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Features */}
      <section className="py-16">
        <div className="container mx-auto px-4">
          <h3 className="text-3xl font-bold text-center text-black mb-12">Zašto RBTours?</h3>
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="border-2 border-red-100 hover:border-red-600 transition-colors">
              <CardContent className="p-6 text-center">
                <Users className="h-12 w-12 text-red-600 mx-auto mb-4" />
                <h4 className="text-xl font-semibold text-black mb-2">Ekspertni Tim</h4>
                <p className="text-gray-600">Naši iskusni agenti će vam pomoći da pronađete savršeno putovanje</p>
              </CardContent>
            </Card>
            <Card className="border-2 border-red-100 hover:border-red-600 transition-colors">
              <CardContent className="p-6 text-center">
                <Star className="h-12 w-12 text-red-600 mx-auto mb-4" />
                <h4 className="text-xl font-semibold text-black mb-2">Vrhunski Servis</h4>
                <p className="text-gray-600">24/7 podrška i personalizovane preporuke za svaki ukus</p>
              </CardContent>
            </Card>
            <Card className="border-2 border-red-100 hover:border-red-600 transition-colors">
              <CardContent className="p-6 text-center">
                <Calendar className="h-12 w-12 text-red-600 mx-auto mb-4" />
                <h4 className="text-xl font-semibold text-black mb-2">Fleksibilno Planiranje</h4>
                <p className="text-gray-600">Prilagođavamo putovanja vašim potrebama i budžetu</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Popular Destinations */}
      <section className="py-16 bg-gray-50">
        <div className="container mx-auto px-4">
          <h3 className="text-3xl font-bold text-center text-black mb-12">Popularne Destinacije</h3>
          <div className="grid md:grid-cols-4 gap-6">
            {["Pariz", "Rim", "Barcelona", "Amsterdam"].map((city) => (
              <Card key={city} className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => handleSuggestionClick(`${city} putovanje`)}>
                <div className="h-48 bg-gradient-to-br from-red-400 to-red-600"></div>
                <CardContent className="p-4">
                  <h4 className="font-semibold text-black">{city}</h4>
                  <p className="text-sm text-gray-600">Od €299</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-black text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Globe className="h-6 w-6 text-red-600" />
                <h4 className="text-xl font-bold">RBTours</h4>
              </div>
              <p className="text-gray-300">Vaš partner za nezaboravna putovanja širom sveta.</p>
            </div>
            <div>
              <h5 className="font-semibold mb-4">Kontakt</h5>
              <div className="space-y-2 text-gray-300">
                <div className="flex items-center space-x-2">
                  <Phone className="h-4 w-4" />
                  <span>+381 11 123 4567</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Mail className="h-4 w-4" />
                  <span>info@rbtours.rs</span>
                </div>
                <div className="flex items-center space-x-2">
                  <MapPin className="h-4 w-4" />
                  <span>Beograd, Srbija</span>
                </div>
              </div>
            </div>
            <div>
              <h5 className="font-semibold mb-4">Radni Sati</h5>
              <div className="text-gray-300">
                <p>Pon - Pet: 09:00 - 18:00</p>
                <p>Sub: 09:00 - 14:00</p>
                <p>Ned: Zatvoreno</p>
              </div>
            </div>
          </div>
        </div>
      </footer>

      {/* Chat Bubble */}
      <ChatBubble 
        isOpen={isChatOpen} 
        onToggle={() => setIsChatOpen(!isChatOpen)} 
        userType="client"
        sessionId={sessionId}
      />
    </div>
  )
}
