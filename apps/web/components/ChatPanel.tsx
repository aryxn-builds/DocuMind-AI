'use client'

import { useState, useEffect, useRef } from 'react'

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
                  }
                } catch (e) {
                  // ignore incomplete JSON parse
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
    <div className="flex flex-col h-full bg-white dark:bg-zinc-950">
      {/* Header */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 p-4">
        <h3 className="font-medium text-zinc-900 dark:text-zinc-100">AI Assistant</h3>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">Ask questions about this document</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 ? (
          <div className="text-center text-sm text-zinc-500 dark:text-zinc-400 mt-10">
            How can I help you with this document?
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div 
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                  msg.role === 'user' 
                    ? 'bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900' 
                    : 'bg-zinc-100 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800'
                }`}
              >
                {/* Basic markdown parsing could be added here, for now just pre-wrap text */}
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!conversationId || isStreaming}
            placeholder="Ask a question..."
            className="flex-1 rounded-full border border-zinc-200 dark:border-zinc-800 bg-transparent px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100"
          />
          <button
            type="submit"
            disabled={!conversationId || isStreaming || !input.trim()}
            className="rounded-full bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
