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
  // setMessages call.  The stream owns the state until it completes.
  // ---------------------------------------------------------------------------
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
          // Bug 3 fix: do NOT overwrite state if a stream is in progress.
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
            setMessages(msgs)
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
            // NOTE: onConversationCreated triggers setActiveConversationId in the parent,
            // which triggers the conversation-load useEffect.  We set isStreamingRef
            // BEFORE calling it so the guard fires in time.
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

        // ----- PROPER SSE PARSING (Bug 1 + Bug 2 fix) -----
        //
        // We maintain a persistent buffer across all reader.read() calls.
        // extractSseEvents() splits on \n\n and returns only complete frames.
        // The remainder (incomplete frame) stays in the buffer for the next chunk.
        // After the reader is done, we do one final flush of whatever remains.

        let buffer = ''
        let readerDone = false

        while (!readerDone) {
          const { value, done } = await reader.read()
          readerDone = done

          // Bug 2 fix: decode even on the final chunk (done=true, value may have data)
          if (value) {
            buffer += decoder.decode(value, { stream: !done })
          }

          // Final flush: when the reader is done, decode any remaining bytes
          // the TextDecoder held internally (e.g. multi-byte UTF-8 boundary).
          if (done) {
            const tail = decoder.decode() // flush internal buffer
            if (tail) buffer += tail
          }

          // Process all complete SSE frames in the buffer right now.
          // extractSseEvents returns the leftover (incomplete frame) as `remaining`.
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
                }
                return next
              })
            } else if (event.kind === 'citations') {
              setMessages(prev => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.role === 'assistant') {
                  next[next.length - 1] = { ...last, citations: event.citations }
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
              // Treat error as terminal — stop reading.
              readerDone = true
              break
            } else if (event.kind === 'done') {
              const ttotal = Math.round(performance.now() - t_send)
              console.log(`[PERF_CHAT] stream_completed_ms=${ttotal}`)
              // Mark done — let the outer loop finish normally (don't break;
              // the reader may already be exhausted or have one last read returning done=true).
            }
          }
        }

        // ----- Bug 4 fix: fallback fetch if stream produced no content -----
        if (assistantContent === '' && currentConvoId) {
          await fetchConversationFallback(currentConvoId)
        }

        onMessageSent()
      } catch (e) {
        console.error('[CHAT] stream error', e)

        // Show error in the assistant bubble rather than leaving it empty.
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

        // Attempt to recover persisted content even after a client-side error.
        if (assistantContent === '' && currentConvoId) {
          await fetchConversationFallback(currentConvoId).catch(() => {})
        }
      } finally {
        // Always clear streaming state — no matter what path exits.
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
  // Render
  // ---------------------------------------------------------------------------
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
