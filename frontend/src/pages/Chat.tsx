import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Sparkles } from 'lucide-react'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: 'assistant',
      content: 'Hello! I\'m your AI financial advisor powered by advanced language models. I can help you analyze your spending patterns, provide financial advice, and answer questions about your finances. How can I assist you today?',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: messages.length + 1,
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages([...messages, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 1, message: input })
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const data = await response.json()

      const assistantMessage: Message = {
        id: messages.length + 2,
        role: 'assistant',
        content: data.reply || 'I apologize, but I encountered an error processing your request.',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: messages.length + 2,
        role: 'assistant',
        content: 'Sorry, I\'m having trouble connecting to the AI service. Please make sure Ollama is running locally at http://localhost:11434',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const suggestedQuestions = [
    "Analyze my spending patterns",
    "How can I save more money?",
    "What's my biggest expense category?",
    "Create a budget plan for me"
  ]

  return (
    <div className="h-full flex flex-col animate-fade-in">
      {/* Header */}
      <div className="flex-shrink-0 mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-3 bg-gradient-to-br from-violet-600 to-indigo-600 rounded-2xl shadow-lg shadow-violet-500/20">
            <Sparkles className="text-white" size={24} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="text-4xl font-bold text-white tracking-tight">AI Financial Advisor</h1>
            <p className="text-gray-400 text-lg">Powered by advanced language models</p>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 card overflow-y-auto space-y-6 mb-6" style={{ maxHeight: 'calc(100vh - 24rem)' }}>
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && (
              <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                <Bot size={20} className="text-white" strokeWidth={2.5} />
              </div>
            )}

            <div
              className={`max-w-[75%] rounded-2xl p-5 ${
                message.role === 'user'
                  ? 'bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/20'
                  : 'bg-white/5 text-gray-100 border border-white/10'
              }`}
            >
              <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
              <p className="text-xs opacity-50 mt-3">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                <User size={20} className="text-white" strokeWidth={2.5} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Bot size={20} className="text-white" strokeWidth={2.5} />
            </div>
            <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
              <div className="flex gap-2">
                <div className="w-2.5 h-2.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2.5 h-2.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2.5 h-2.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {messages.length === 1 && (
          <div className="space-y-3 mt-4">
            <p className="text-sm text-gray-400 font-medium">Suggested questions:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {suggestedQuestions.map((question, i) => (
                <button
                  key={i}
                  onClick={() => setInput(question)}
                  className="text-left p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-violet-500/50 transition-all text-gray-300 text-sm"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="card p-5">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask about your finances, request insights, or get advice..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-5 py-4 text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 focus:bg-white/8 transition-all"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="btn btn-primary px-8 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            <Send size={20} strokeWidth={2.5} />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-3 text-center">
          AI responses are generated by language models and may not always be accurate. Always verify important financial decisions.
        </p>
      </div>
    </div>
  )
}
