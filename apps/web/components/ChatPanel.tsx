'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Sparkles, Send, Bot, AlertCircle } from 'lucide-react'
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

// ---------------------------------------------------------------------------
// SSE Parser — handles arbitrary TCP chunk boundaries.
//
// Maintains a mutable buffer and extracts complete SSE frames delimited by
// "\n\n" (or "\r\n\r\n"). Only complete frames are returned; leftover bytes
// stay in the buffer for the next call.
//
// Returns an array of parsed { type, content, citations, error } objects.
// Returns null entries for unrecognised / keepalive frames (caller ignores them).
// ---------------------------------------------------------------------------
type SseEvent =
  | { kind: 'chunk'; content: string }
  | { kind: 'citations'; citations: Citation[] }
  | { kind: 'done' }
  | { kind: 'error'; message: string }

function extractSseEvents(buf: string): { events: SseEvent[]; remaining: string } {
  const events: SseEvent[] = []

  // Normalise line endings so both \r\n and \n work.
  let buffer = buf.replace(/\r\n/g, '\n')

  // Frames are delimited by a blank line (\n\n).
  let boundary = buffer.indexOf('\n\n')
  while (boundary !== -1) {
    const frame = buffer.slice(0, boundary)
    buffer = buffer.slice(boundary + 2)

    // A frame may contain multiple lines; pick out "data: …" lines.
    for (const line of frame.split('\n')) {
      if (!line.startsWith('data: ')) continue

      const raw = line.slice(6).trim()

      // Sentinel
      if (raw === '[DONE]') {
        events.push({ kind: 'done' })
        break
      }

      // Keepalive / comment
      if (raw === '' || raw.startsWith(':')) continue

      try {
        const parsed = JSON.parse(raw)

        if (parsed.type === 'citations' && Array.isArray(parsed.citations)) {
          events.push({ kind: 'citations', citations: parsed.citations as Citation[] })
        } else if (parsed.error) {
          events.push({ kind: 'error', message: String(parsed.error) })
        } else if (parsed.type === 'chunk' || parsed.content !== undefined) {
          // Backend emits { type: "chunk", content: "..." }
          const content = String(parsed.content ?? '')
          if (content) events.push({ kind: 'chunk', content })
        }
        // Unknown type shapes are silently ignored — they don't kill the stream.
      } catch {
        // JSON.parse failure on an individual frame is non-fatal.
        // The frame may be incomplete (shouldn't happen because we only process
        // frames past a \n\n boundary, but be defensive).
        console.warn('[SSE_PARSER] Failed to parse frame:', raw.slice(0, 120))
      }
    }

    boundary = buffer.indexOf('\n\n')
  }

  return { events, remaining: buffer }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function ChatPanel({
  documentId,
  accessToken,
  activeConversationId,
  onConversationCreated,
  onMessageSent,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [answerDepth, setAnswerDepth] = useState<'low' | 'medium' | 'high'>('medium')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)

  // Keep a ref to the latest token so the conversation-load effect can check
  // whether a stream is currently active before overwriting React state.
  const isStreamingRef = useRef(false)

  // Track the ID of the conversation whose messages are currently loaded in state.
  // This prevents redundant/stale GET requests from wiping in-flight or streaming messages.
  const loadedConversationIdRef = useRef<string | null>(null)

  // Keep a stable ref to the access token so async callbacks always have the
  // latest value without needing to be in the dependency array.
  const accessTokenRef = useRef(accessToken)
  useEffect(() => {
    accessTokenRef.current = accessToken
  }, [accessToken])

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // ---------------------------------------------------------------------------
  // Auto-scroll
  // ---------------------------------------------------------------------------
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

  // ---------------------------------------------------------------------------
  // Load conversation history
  //
  // Guard: if a stream is currently active for this conversation, skip the
  // setMessages call. The stream owns the state until it completes.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!activeConversationId) {
      loadedConversationIdRef.current = null
      setMessages([])
      return
    }

    // Guard: If this conversation is already loaded or is currently being created/streamed locally,
    // do not trigger a stale network fetch that would overwrite client state.
    if (loadedConversationIdRef.current === activeConversationId) {
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
          // Do NOT overwrite state if a stream is in progress.
          // The streaming handler owns the message list while isStreamingRef is true.
          if (isStreamingRef.current) {
            console.log(
              '[CHAT_HISTORY] skipping setMessages — stream is active for conversation_id=' +
                activeConversationId
            )
            return
          }

          const data = await res.json()
          const loadMs = Math.round(performance.now() - t0)
          console.log(
            `[PERF_CHAT] conversation_load_ms=${loadMs} conversation_id=${activeConversationId} ` +
              `message_count=${(data.messages || []).length}`
          )

          loadedConversationIdRef.current = activeConversationId
          setMessages(prev => {
            const incoming: Message[] = data.messages || []
            // If the client state already has more messages than the incoming server response
            // (e.g. optimistic or streaming), do not overwrite with an older snapshot.
            if (prev.length > incoming.length) {
              return prev
            }
            return incoming
          })
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

  // ---------------------------------------------------------------------------
  // Fallback: fetch persisted messages after stream ends with no content.
  // This is a safety net only — the normal path is streaming content directly.
  // ---------------------------------------------------------------------------
  const fetchConversationFallback = useCallback(
    async (conversationId: string) => {
      console.log(
        '[CHAT_FALLBACK] stream produced no content — fetching persisted messages ' +
          `conversation_id=${conversationId}`
      )
      try {
        const res = await fetch(`${API_URL}/api/v1/conversations/${conversationId}`, {
          headers: { Authorization: `Bearer ${accessTokenRef.current}` },
        })
        if (res.ok) {
          const data = await res.json()
          const msgs: Message[] = data.messages || []
          if (msgs.length > 0) {
            setMessages(prev => {
              // Safety guard: only replace if we don't already have an assistant response with content
              const last = prev[prev.length - 1]
              if (last?.role === 'assistant' && last.content.trim().length > 0) {
                return prev
              }
              return msgs
            })
            console.log(
              `[CHAT_FALLBACK] recovered ${msgs.length} messages from DB for conversation_id=${conversationId}`
            )
          }
        }
      } catch (err) {
        console.error('[CHAT_FALLBACK] failed to fetch fallback messages', err)
      }
    },
    [API_URL]
  )

  // ---------------------------------------------------------------------------
  // Send message + stream response
  // ---------------------------------------------------------------------------
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!input.trim() || isStreamingRef.current) return

      let currentConvoId = activeConversationId

      // ----- Create conversation if first message in a new chat -----
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
            // Mark this conversation as already loaded locally so the subsequent activeConversationId
            // update does not trigger a stale fetchConversation() request.
            loadedConversationIdRef.current = data.id
            isStreamingRef.current = true
            setIsStreaming(true)
            onConversationCreated(data.id)
          } else {
            console.error('[CHAT] failed to create conversation', res.status)
            return
          }
        } catch (err) {
          console.error('[CHAT] failed to create conversation', err)
          return
        }
      } else {
        loadedConversationIdRef.current = currentConvoId
        isStreamingRef.current = true
        setIsStreaming(true)
      }

      const userMessage = input.trim()
      setInput('')

      // Optimistic UI: add user message + empty assistant placeholder
      setMessages(prev => [
        ...prev,
        { role: 'user', content: userMessage },
        { role: 'assistant', content: '' },
      ])

      const t_send = performance.now()
      let firstChunkLogged = false
      let assistantContent = ''

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

        if (!response.ok) {
          const errText = await response.text().catch(() => response.statusText)
          throw new Error(`Backend returned ${response.status}: ${errText}`)
        }

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        if (!reader) {
          throw new Error('Response body is not readable')
        }

        // Maintain persistent buffer across all reader.read() calls.
        let buffer = ''
        let readerDone = false

        while (!readerDone) {
          const { value, done } = await reader.read()
          readerDone = done

          // Decode even on the final chunk (done=true, value may have data)
          if (value) {
            buffer += decoder.decode(value, { stream: !done })
          }

          // Final flush when the reader is done
          if (done) {
            const tail = decoder.decode()
            if (tail) buffer += tail
          }

          // Process all complete SSE frames in the buffer right now
          const { events, remaining } = extractSseEvents(buffer)
          buffer = remaining

          for (const event of events) {
            if (event.kind === 'chunk') {
              if (!firstChunkLogged) {
                const ttui = Math.round(performance.now() - t_send)
                console.log(`[PERF_CHAT] first_chunk_to_ui_ms=${ttui}`)
                firstChunkLogged = true
              }
              const token = event.content
              assistantContent += token
              setMessages(prev => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.role === 'assistant') {
                  next[next.length - 1] = { ...last, content: last.content + token }
                } else {
                  next.push({ role: 'assistant', content: token })
                }
                return next
              })
            } else if (event.kind === 'citations') {
              setMessages(prev => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.role === 'assistant') {
                  next[next.length - 1] = { ...last, citations: event.citations }
                } else {
                  next.push({ role: 'assistant', content: '', citations: event.citations })
                }
                return next
              })
            } else if (event.kind === 'error') {
              console.error('[SSE] backend error event:', event.message)
              setMessages(prev => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.role === 'assistant' && last.content === '') {
                  next[next.length - 1] = { ...last, content: `⚠ ${event.message}` }
                }
                return next
              })
              readerDone = true
              break
            } else if (event.kind === 'done') {
              const ttotal = Math.round(performance.now() - t_send)
              console.log(`[PERF_CHAT] stream_completed_ms=${ttotal}`)
            }
          }
        }

        // Fallback fetch if stream produced no content (wait 400ms for backend DB commit)
        if (assistantContent === '' && currentConvoId) {
          await new Promise(r => setTimeout(r, 400))
          await fetchConversationFallback(currentConvoId)
        }

        onMessageSent()
      } catch (e) {
        console.error('[CHAT] stream error', e)

        setMessages(prev => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last?.role === 'assistant' && last.content === '') {
            next[next.length - 1] = {
              ...last,
              content: '⚠ Something went wrong. Please try again.',
            }
          }
          return next
        })

        // Attempt to recover persisted content even after a client-side error
        if (assistantContent === '' && currentConvoId) {
          await new Promise(r => setTimeout(r, 400))
          await fetchConversationFallback(currentConvoId).catch(() => {})
        }
      } finally {
        isStreamingRef.current = false
        setIsStreaming(false)
      }
    },
    [
      API_URL,
      answerDepth,
      activeConversationId,
      documentId,
      input,
      onConversationCreated,
      onMessageSent,
      fetchConversationFallback,
    ]
  )

  // ---------------------------------------------------------------------------
  // Render (Aligned with design-system/pages/chat.md and MASTER.md)
  // ---------------------------------------------------------------------------
  return (
    <div className="flex flex-col h-full bg-[#0A0A0A] font-sans border-l border-[#262626]">
      {/* Header */}
      <div className="shrink-0 border-b border-[#262626] px-4 py-3 bg-[#0A0A0A] flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-[#171717] border border-[#262626] flex items-center justify-center shrink-0">
            <Sparkles className="w-3.5 h-3.5 text-[#FFFFFF]" />
          </div>
          <div>
            <h3 className="font-semibold text-xs tracking-tight text-[#FFFFFF]">DocuMind AI</h3>
            <p className="text-[11px] text-[#737373]">Ask questions about this document</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-mono text-[#737373]">Depth:</span>
          <select
            value={answerDepth}
            onChange={e => setAnswerDepth(e.target.value as 'low' | 'medium' | 'high')}
            className="text-xs font-mono bg-[#111111] border border-[#262626] rounded-md px-2 py-1 text-[#E5E5E5] focus:outline-none focus:border-[#404040]"
          >
            <option value="low">Low (Concise)</option>
            <option value="medium">Medium (Balanced)</option>
            <option value="high">High (Detailed)</option>
          </select>
        </div>
      </div>

      {/* Messages */}
      <div
        ref={chatContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 space-y-6"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="w-9 h-9 rounded-lg bg-[#111111] border border-[#262626] flex items-center justify-center mb-3">
              <Bot className="w-4 h-4 text-[#A3A3A3]" />
            </div>
            <h4 className="text-xs font-medium text-[#FFFFFF] mb-1">Document Assistant Ready</h4>
            <p className="text-xs text-[#737373] max-w-[260px] leading-relaxed">
              Ask anything about this document. Citations are verified against source pages.
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'user' ? (
                /* User Message: Right-aligned text block, subtle 8px radius, elevated surface per chat.md */
                <div className="max-w-[85%] rounded-[8px] bg-[#111111] border border-[#262626] px-3.5 py-2.5 text-xs text-[#FFFFFF] leading-relaxed whitespace-pre-wrap break-words">
                  {msg.content}
                </div>
              ) : (
                /* AI Response: Left-aligned, transparent background, structured research text */
                <div className="w-full bg-transparent px-0.5 py-1 text-xs leading-relaxed text-[#E5E5E5]">
                  {msg.content.includes('[System Error:') ? (
                    <div className="rounded-[8px] bg-red-950/20 border border-red-800/40 p-3 text-xs text-red-400 font-mono flex items-start gap-2.5">
                      <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                      <div className="flex-1 whitespace-pre-wrap break-words">{msg.content.replace(/^[\n\s]+/, '')}</div>
                    </div>
                  ) : msg.content === '' && isStreaming && i === messages.length - 1 ? (
                    <div className="flex items-center gap-1.5 h-5 text-[#737373]">
                      <span className="w-1.5 h-1.5 bg-[#737373] rounded-full animate-pulse [animation-delay:-0.3s]"></span>
                      <span className="w-1.5 h-1.5 bg-[#737373] rounded-full animate-pulse [animation-delay:-0.15s]"></span>
                      <span className="w-1.5 h-1.5 bg-[#737373] rounded-full animate-pulse"></span>
                    </div>
                  ) : (
                    <div className="prose prose-invert prose-xs max-w-none break-words text-[#E5E5E5] [&_h1]:text-sm [&_h1]:font-semibold [&_h1]:text-white [&_h2]:text-xs [&_h2]:font-semibold [&_h2]:text-white [&_h3]:text-xs [&_h3]:font-medium [&_h3]:text-[#A3A3A3] [&_p]:leading-relaxed [&_code]:font-mono [&_code]:text-[11px] [&_pre]:bg-[#111111] [&_pre]:border [&_pre]:border-[#262626] [&_pre]:rounded-md [&>p:first-child]:mt-0 [&>p:last-child]:mb-0">
                      <ReactMarkdown>{msg.content.replace(/\[Source:\s*(\d+)\]/gi, '[$1]')}</ReactMarkdown>
                    </div>
                  )}

                  {/* Citations / Source Cards */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[#262626] flex flex-wrap gap-1.5">
                      {msg.citations.map((c, idx) => (
                        <div
                          key={idx}
                          className="inline-flex items-center gap-1.5 px-2 py-1 bg-[#111111] hover:bg-[#171717] border border-[#262626] rounded-md text-[11px] font-mono text-[#A3A3A3] transition-colors cursor-default"
                          title={`Relevance Score: ${c.relevance_score.toFixed(2)}`}
                        >
                          <span className="text-[#FFFFFF] font-medium">[{idx + 1}]</span>
                          <span className="truncate max-w-[140px]">{c.filename || 'Document'}</span>
                          {c.page_number && <span className="text-[#737373]">p.{c.page_number}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} className="h-2" />
      </div>

      {/* Composer (Input Area) */}
      <div className="shrink-0 p-3.5 bg-[#0A0A0A] border-t border-[#262626]">
        <form
          onSubmit={handleSubmit}
          className="relative flex items-end gap-2 bg-[#111111] border border-[#262626] rounded-lg p-2 focus-within:border-[#404040] transition-colors"
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
            placeholder={isStreaming ? 'Generating response...' : 'Ask a question about this document...'}
            className="flex-1 min-h-[38px] max-h-[140px] resize-none bg-transparent px-2 py-1 text-xs text-[#FFFFFF] placeholder:text-[#737373] focus:outline-none disabled:opacity-50"
            rows={1}
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="shrink-0 flex items-center justify-center w-7 h-7 rounded-md bg-[#FFFFFF] text-[#000000] hover:bg-[#E5E5E5] transition-colors disabled:opacity-30 disabled:hover:bg-[#FFFFFF]"
            title="Send question"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
        <div className="text-center mt-2">
          <p className="text-[10px] text-[#737373] font-mono">Answers grounded strictly in document context.</p>
        </div>
      </div>
    </div>
  )
}
