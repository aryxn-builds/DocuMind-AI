'use client'

import { useState, useEffect, useRef } from 'react'
import { Sparkles, Send, Bot, User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

type Message = {
  id?: string
  role: 'user' | 'assistant'
  content: string
}

interface ChatPanelProps {
  documentId: string
  accessToken: string
}

export function ChatPanel({ documentId, accessToken }: ChatPanelProps) {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    // Create or fetch conversation
    const initConversation = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/conversations`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
          },
          body: JSON.stringify({
            title: 'Document Chat',
            document_id: documentId
          })
        })
        if (res.ok) {
          const data = await res.json()
          setConversationId(data.id)
        }
      } catch (e) {
        console.error("Failed to init conversation", e)
      }
    }
    
    initConversation()
  }, [API_URL, accessToken, documentId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !conversationId || isStreaming) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsStreaming(true)

    // Add empty assistant message to append to
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      const response = await fetch(`${API_URL}/api/v1/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          query: userMessage,
          document_id: documentId
        })
      })

      if (!response.ok) throw new Error('Failed to send message')

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let done = false

      if (reader) {
        while (!done) {
          const { value, done: readerDone } = await reader.read()
          done = readerDone
          if (value) {
            const chunkText = decoder.decode(value, { stream: true })
            const lines = chunkText.split('\n')
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6)
                if (data === '[DONE]') {
                  done = true
                  break
                }
                try {
                  const parsed = JSON.parse(data)
                  if (parsed.content) {
                    setMessages(prev => {
                      const newMessages = [...prev]
                      const last = newMessages[newMessages.length - 1]
                      if (last.role === 'assistant') {
                        last.content += parsed.content
                      }
                      return newMessages
                    })
                  } else if (parsed.error) {
                    // Backend signalled an error — replace the empty placeholder
                    // with an informative message so the user sees feedback.
                    setMessages(prev => {
                      const newMessages = [...prev]
                      const last = newMessages[newMessages.length - 1]
                      if (last.role === 'assistant' && last.content === '') {
                        last.content = `⚠ ${parsed.error}`
                      }
                      return newMessages
                    })
                    done = true
                  }
                } catch {
                  // ignore incomplete JSON frames
                }
              }
            }
          }
        }
      }
    } catch (e) {
      console.error(e)
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-zinc-950 font-sans">
      {/* Header */}
      <div className="shrink-0 border-b border-zinc-200 dark:border-zinc-800 p-4 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
        </div>
        <div>
          <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">DocuMind AI</h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">Ask questions about this document</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="w-12 h-12 rounded-2xl bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-zinc-400" />
            </div>
            <h4 className="text-sm font-medium text-zinc-900 dark:text-zinc-100 mb-1">How can I help you today?</h4>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-[250px]">
              Ask me anything about the content of this document and I'll find the answers.
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center shrink-0 border border-zinc-200 dark:border-zinc-800 mt-0.5">
                  <Bot className="w-4 h-4 text-zinc-600 dark:text-zinc-400" />
                </div>
              )}
              
              <div 
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900' 
                    : 'bg-zinc-50 text-zinc-900 dark:bg-zinc-900/50 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800/80 shadow-sm'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm prose-zinc dark:prose-invert max-w-none break-words [&>p:first-child]:mt-0 [&>p:last-child]:mb-0">
                    <ReactMarkdown>{msg.content || '...'}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4 text-zinc-500 dark:text-zinc-400" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} className="h-4" />
      </div>

      {/* Input Form */}
      <div className="shrink-0 p-4 bg-white dark:bg-zinc-950">
        <form onSubmit={handleSubmit} className="relative flex items-end gap-2 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl p-1.5 shadow-sm focus-within:ring-2 focus-within:ring-zinc-900 dark:focus-within:ring-zinc-100 transition-shadow">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!conversationId || isStreaming}
            placeholder={isStreaming ? "AI is typing..." : "Ask a question..."}
            className="flex-1 min-h-[44px] bg-transparent px-4 py-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-500 focus:outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!conversationId || isStreaming || !input.trim()}
            className="shrink-0 flex items-center justify-center w-[44px] h-[44px] rounded-full bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:hover:bg-zinc-900 dark:disabled:hover:bg-zinc-100"
          >
            <Send className="w-4 h-4 translate-x-[-1px] translate-y-[1px]" />
          </button>
        </form>
        <div className="text-center mt-3">
          <p className="text-[11px] text-zinc-400 font-medium">AI can make mistakes. Check important info.</p>
        </div>
      </div>
    </div>
  )
}
