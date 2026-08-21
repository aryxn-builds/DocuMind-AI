'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Sparkles, Send, Bot, User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

type Citation = {
  document_id: string
  chunk_id: string
  page_number?: number
  relevance_score: number
  filename?: string
}

type Message = {
  id?: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
}

interface ChatPanelProps {
  documentId: string
  accessToken: string
  activeConversationId: string | null
  onConversationCreated: (id: string) => void
  onMessageSent: () => void
}

export function ChatPanel({ 
  documentId, 
  accessToken, 
  activeConversationId, 
  onConversationCreated,
  onMessageSent
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [answerDepth, setAnswerDepth] = useState<'low' | 'medium' | 'high'>('medium')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)

  const accessTokenRef = useRef(accessToken)
  useEffect(() => {
    accessTokenRef.current = accessToken
  }, [accessToken])

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const handleScroll = () => {
    if (chatContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current
      setAutoScroll(scrollHeight - scrollTop - clientHeight < 100)
    }
  }

  useEffect(() => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, autoScroll])

  // Load selected conversation
  useEffect(() => {
    if (!activeConversationId) {
      setMessages([])
      return
    }

    let isMounted = true
    const abortController = new AbortController()

    const fetchConversation = async () => {
      const t0 = performance.now()
      try {
        const res = await fetch(`${API_URL}/api/v1/conversations/${activeConversationId}`, {
          headers: { Authorization: `Bearer ${accessTokenRef.current}` },
          signal: abortController.signal,
        })
        if (res.ok && isMounted) {
          const data = await res.json()
          const loadMs = Math.round(performance.now() - t0)
          console.log(
            `[PERF_CHAT] conversation_load_ms=${loadMs} conversation_id=${activeConversationId} ` +
              `message_count=${(data.messages || []).length}`
          )
          setMessages(data.messages || [])
        }
      } catch (e: unknown) {
        const err = e as { name?: string }
        if (err?.name !== 'AbortError') {
          console.error('[CHAT_HISTORY] fetch_conversation_error', e)
        }
      }
    }

    fetchConversation()

    return () => {
      isMounted = false
      abortController.abort()
    }
  }, [activeConversationId, API_URL])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!input.trim() || isStreaming) return

      let currentConvoId = activeConversationId

      if (!currentConvoId) {
        try {
          const res = await fetch(`${API_URL}/api/v1/conversations`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${accessTokenRef.current}`,
            },
            body: JSON.stringify({
              title: input.trim().substring(0, 40) + (input.length > 40 ? '...' : ''),
              document_id: documentId,
            }),
          })
          if (res.ok) {
            const data = await res.json()
            currentConvoId = data.id
            onConversationCreated(data.id)
          } else {
            console.error('Failed to create conversation')
            return
          }
        } catch (err) {
          console.error('Failed to create conversation', err)
          return
        }
      }

      const userMessage = input.trim()
      setInput('')
      setMessages(prev => [...prev, { role: 'user', content: userMessage }])
      setIsStreaming(true)

      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      try {
        const response = await fetch(
          `${API_URL}/api/v1/conversations/${currentConvoId}/messages`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${accessTokenRef.current}`,
            },
            body: JSON.stringify({
              query: userMessage,
              document_id: documentId,
              answer_depth: answerDepth,
            }),
          }
        )

        if (!response.ok) throw new Error('Failed to send message')

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
        let done = false
        const t_send = performance.now()
        let firstChunkLogged = false

        if (reader) {
          let buffer = ''
          while (!done) {
            const { value, done: readerDone } = await reader.read()
            done = readerDone
            if (value) {
              buffer += decoder.decode(value, { stream: true })
              let boundary = buffer.indexOf('\n\n')
              
              while (boundary !== -1) {
                const chunk = buffer.slice(0, boundary)
                buffer = buffer.slice(boundary + 2)

                const lines = chunk.split('\n')
                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = line.slice(6)
                    if (data === '[DONE]') {
                      const ttui = Math.round(performance.now() - t_send)
                      console.log(`[PERF_CHAT] stream_completed_ms=${ttui}`)
                      done = true
                      break
                    }
                    try {
                      const parsed = JSON.parse(data)
                    if (parsed.type === 'citations') {
                      setMessages(prev => {
                        const next = [...prev]
                        const last = next[next.length - 1]
                        if (last?.role === 'assistant') {
                          next[next.length - 1] = { ...last, citations: parsed.citations }
                        }
                        return next
                      })
                    } else if (parsed.type === 'chunk' || parsed.content) {
                      if (!firstChunkLogged) {
                        const ttui = Math.round(performance.now() - t_send)
                        console.log(`[PERF_CHAT] first_chunk_to_ui_ms=${ttui}`)
                        firstChunkLogged = true
                      }
                      setMessages(prev => {
                        const next = [...prev]
                        const last = next[next.length - 1]
                        if (last?.role === 'assistant') {
                          next[next.length - 1] = {
                            ...last,
                            content: last.content + (parsed.content || ''),
                          }
                        }
                        return next
                      })
                    } else if (parsed.error) {
                      setMessages(prev => {
                        const next = [...prev]
                        const last = next[next.length - 1]
                        if (last?.role === 'assistant' && last.content === '') {
                          next[next.length - 1] = { ...last, content: `⚠ ${parsed.error}` }
                        }
                        return next
                      })
                      done = true
                    }
                  } catch {
                    // Ignore incomplete JSON frames
                  }
                }
              }
              boundary = buffer.indexOf('\n\n')
            } // end while(boundary)
          } // end if(value)
        } // end while(!done)
      } // end if(reader)

      onMessageSent()
      
    } catch (e) {
        console.error(e)
      } finally {
        setIsStreaming(false)
      }
    },
    [API_URL, answerDepth, activeConversationId, documentId, input, isStreaming, onConversationCreated, onMessageSent]
  )

  return (
    <div className="flex flex-col h-full bg-white dark:bg-zinc-950 font-sans">
      <div className="shrink-0 border-b border-zinc-200 dark:border-zinc-800 p-4 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">DocuMind AI</h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">Ask questions about this document</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Depth:</span>
          <select
            value={answerDepth}
            onChange={e => setAnswerDepth(e.target.value as 'low' | 'medium' | 'high')}
            className="text-xs bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md px-2 py-1 text-zinc-700 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="low">Low (Concise)</option>
            <option value="medium">Medium (Balanced)</option>
            <option value="high">High (Detailed)</option>
          </select>
        </div>
      </div>

      <div
        ref={chatContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="w-12 h-12 rounded-2xl bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-zinc-400" />
            </div>
            <h4 className="text-sm font-medium text-zinc-900 dark:text-zinc-100 mb-1">How can I help you today?</h4>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-[250px]">
              Ask me anything about the content of this document and I&apos;ll find the answers.
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
                  <div className="flex flex-col gap-4">
                    {msg.content === '' && isStreaming && i === messages.length - 1 ? (
                      <div className="flex items-center gap-1.5 h-6">
                        <span className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                        <span className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                        <span className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce"></span>
                      </div>
                    ) : (
                      <div className="prose prose-sm prose-zinc dark:prose-invert max-w-none break-words [&>p:first-child]:mt-0 [&>p:last-child]:mb-0">
                        <ReactMarkdown>{msg.content.replace(/\[Source:\s*(\d+)\]/gi, '[$1]')}</ReactMarkdown>
                      </div>
                    )}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2 border-t border-zinc-200 dark:border-zinc-800 pt-3 flex flex-wrap gap-2">
                        {msg.citations.map((c, idx) => (
                          <div
                            key={idx}
                            className="inline-flex items-center gap-1 px-2 py-1 bg-zinc-200/50 dark:bg-zinc-800 rounded text-[11px] font-medium text-zinc-600 dark:text-zinc-400 cursor-default"
                            title={`Document source (Score: ${c.relevance_score.toFixed(2)})`}
                          >
                            <span>[{idx + 1}]</span>
                            <span>{c.filename || 'Document'} {c.page_number ? `(Page ${c.page_number})` : ''}</span>
                          </div>
                        ))}
                      </div>
                    )}
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

      <div className="shrink-0 p-4 bg-white dark:bg-zinc-950">
        <form
          onSubmit={handleSubmit}
          className="relative flex items-end gap-2 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl p-1.5 shadow-sm focus-within:ring-2 focus-within:ring-zinc-900 dark:focus-within:ring-zinc-100 transition-shadow"
        >
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
            disabled={isStreaming}
            placeholder={isStreaming ? 'AI is typing...' : 'Ask a question...'}
            className="flex-1 min-h-[44px] max-h-[150px] resize-none bg-transparent px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-500 focus:outline-none disabled:opacity-50"
            rows={1}
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
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
