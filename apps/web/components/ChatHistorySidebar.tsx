'use client'

import { useEffect, useState, useCallback } from 'react'
import { MessageSquare, Plus, ChevronLeft, ChevronRight, FileText } from 'lucide-react'
import type { Conversation } from './DocumentWorkspaceClient'
// Native JS date utils instead of date-fns

interface ChatHistorySidebarProps {
  accessToken: string
  activeConversationId: string | null
  /** Receives the full Conversation object so the parent can use document_id for navigation. */
  onSelectConversation: (conversation: Conversation) => void
  onNewChat: () => void
  refreshTrigger: number // Bump this to re-fetch
}

export function ChatHistorySidebar({
  accessToken,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  refreshTrigger
}: ChatHistorySidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchConversations = useCallback(async (signal?: AbortSignal) => {
    if (!accessToken) return

    try {
      const res = await fetch(`${API_URL}/api/v1/conversations`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        signal
      })
      if (res.ok) {
        const data: Conversation[] = await res.json()
        console.log(
          `[CHAT_HISTORY] sidebar_loaded conversation_count=${data.length} ` +
            `user_ids=${[...new Set(data.map(c => c.document_id))].join(',')}`
        )
        setConversations(data)
      } else {
        console.error(`[CHAT_HISTORY] sidebar_fetch_failed status=${res.status}`)
      }
    } catch (e: unknown) {
      const err = e as { name?: string }
      if (err?.name !== 'AbortError') {
        console.error('[CHAT_HISTORY] sidebar_fetch_error', e)
      }
    } finally {
      setIsLoading(false)
    }
  }, [accessToken, API_URL])

  useEffect(() => {
    const abortController = new AbortController()
    fetchConversations(abortController.signal)
    return () => abortController.abort()
  }, [fetchConversations, refreshTrigger])

  const groupConversations = () => {
    const todayItems: Conversation[] = []
    const yesterdayItems: Conversation[] = []
    const previous7Days: Conversation[] = []
    const older: Conversation[] = []

    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const sevenDaysAgo = new Date(today)
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

    conversations.forEach(c => {
      const date = new Date(c.updated_at)
      if (date >= today) {
        todayItems.push(c)
      } else if (date >= yesterday && date < today) {
        yesterdayItems.push(c)
      } else if (date >= sevenDaysAgo && date < yesterday) {
        previous7Days.push(c)
      } else {
        older.push(c)
      }
    })

    return [
      { label: 'Today', items: todayItems },
      { label: 'Yesterday', items: yesterdayItems },
      { label: 'Previous 7 days', items: previous7Days },
      { label: 'Older', items: older }
    ].filter(g => g.items.length > 0)
  }

  if (isCollapsed) {
    return (
      <div className="w-16 h-full flex flex-col border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50 transition-all">
        <div className="p-4 flex flex-col items-center gap-4 shrink-0">
          <button
            onClick={() => setIsCollapsed(false)}
            className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors"
          >
            <ChevronRight className="w-4 h-4 text-zinc-500" />
          </button>
          <button
            onClick={onNewChat}
            className="w-8 h-8 rounded-full bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center hover:bg-indigo-100 dark:hover:bg-indigo-500/20 transition-colors"
            title="New Chat"
          >
            <Plus className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-64 h-full flex flex-col border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50 transition-all overflow-hidden shrink-0">
      <div className="p-4 flex items-center justify-between shrink-0 border-b border-zinc-200/50 dark:border-zinc-800/50">
        <h2 className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">Chat History</h2>
        <div className="flex items-center gap-1">
          <button
            onClick={onNewChat}
            className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors text-zinc-500"
            title="New Chat"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsCollapsed(true)}
            className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors text-zinc-500"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-6">
        {isLoading ? (
          <div className="flex justify-center p-4">
            <span className="w-5 h-5 rounded-full border-2 border-zinc-300 border-t-indigo-500 animate-spin"></span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center p-4">
            <p className="text-sm text-zinc-500">No recent chats.</p>
          </div>
        ) : (
          groupConversations().map(group => (
            <div key={group.label} className="space-y-1">
              <h3 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 px-2 mb-2 uppercase tracking-wider">
                {group.label}
              </h3>
              {group.items.map(c => (
                <button
                  key={c.id}
                  // Pass the FULL conversation object so the parent can read document_id
                  // and navigate to the correct document workspace if needed.
                  onClick={() => onSelectConversation(c)}
                  className={`w-full text-left p-2 rounded-lg transition-colors flex items-start gap-3 ${
                    activeConversationId === c.id
                      ? 'bg-zinc-200/60 dark:bg-zinc-800/60'
                      : 'hover:bg-zinc-200/40 dark:hover:bg-zinc-800/40'
                  }`}
                >
                  <MessageSquare className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />
                  <div className="flex-1 overflow-hidden">
                    <p className="text-sm text-zinc-900 dark:text-zinc-100 truncate font-medium">
                      {c.title}
                    </p>
                    {c.document_filename && (
                      <div className="flex items-center gap-1 mt-0.5 text-[10px] text-zinc-500 dark:text-zinc-400">
                        <FileText className="w-3 h-3 shrink-0" />
                        <span className="truncate">{c.document_filename}</span>
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
