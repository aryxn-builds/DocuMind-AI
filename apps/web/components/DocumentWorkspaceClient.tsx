'use client'

import { useState, useCallback, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { ChatHistorySidebar } from './ChatHistorySidebar'
import { ChatPanel } from './ChatPanel'
import { DocumentViewer } from './DocumentViewer'
import { ArrowLeft, FileText } from 'lucide-react'
import Link from 'next/link'

// Imported type shared with ChatHistorySidebar
export type Conversation = {
  id: string
  title: string
  document_id: string | null
  document_filename: string | null
  updated_at: string
}

interface DocumentWorkspaceClientProps {
  documentId: string
  accessToken: string
  /** Passed from the server component by reading ?conversation= from the URL. */
  initialConversationId: string | null
}

export function DocumentWorkspaceClient({
  documentId,
  accessToken,
  initialConversationId,
}: DocumentWorkspaceClientProps) {
  const router = useRouter()
  const searchParams = useSearchParams()

  // Initialise from the URL param passed by the server — survives hard refresh.
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    initialConversationId
  )
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0)

  // Keep URL in sync whenever the active conversation changes.
  // This ensures the browser URL always reflects the current conversation so
  // a hard refresh or link-share restores the exact state.
  useEffect(() => {
    const current = searchParams.get('conversation')
    if (activeConversationId && current !== activeConversationId) {
      const params = new URLSearchParams(searchParams.toString())
      params.set('conversation', activeConversationId)
      router.replace(`?${params.toString()}`, { scroll: false })
    } else if (!activeConversationId && current) {
      const params = new URLSearchParams(searchParams.toString())
      params.delete('conversation')
      router.replace(`?${params.toString()}`, { scroll: false })
    }
  }, [activeConversationId, router, searchParams])

  /**
   * Called when the user clicks a conversation in the sidebar.
   *
   * If the conversation belongs to a different document, navigate to that
   * document's workspace with the conversation ID in the URL. The server
   * component at the destination will read the param and initialise the
   * correct conversation on mount.
   *
   * If the conversation belongs to the current document, just update local
   * state (the URL-sync effect above will update the URL accordingly).
   */
  const handleSelectConversation = useCallback(
    (conversation: Conversation) => {
      if (conversation.document_id && conversation.document_id !== documentId) {
        // Cross-document navigation — navigate to the other document's workspace.
        console.log(
          `[CHAT_HISTORY] cross_doc_navigate conversation_id=${conversation.id} ` +
            `from_document_id=${documentId} to_document_id=${conversation.document_id}`
        )
        router.push(
          `/dashboard/documents/${conversation.document_id}?conversation=${conversation.id}`
        )
      } else {
        // Same document — just switch conversation in place.
        console.log(
          `[CHAT_HISTORY] select_conversation conversation_id=${conversation.id} document_id=${documentId}`
        )
        setActiveConversationId(conversation.id)
      }
    },
    [documentId, router]
  )

  /**
   * "New Chat" clears the active conversation and removes ?conversation= from
   * the URL. No DB record is created until the first message is submitted.
   */
  const handleNewChat = useCallback(() => {
    console.log(`[CHAT_HISTORY] new_chat document_id=${documentId}`)
    setActiveConversationId(null)
  }, [documentId])

  /**
   * Called by ChatPanel after a new conversation row is created in the DB
   * (triggered by the first user message in a new chat).
   */
  const handleConversationCreated = useCallback((id: string) => {
    console.log(`[CHAT_HISTORY] conversation_created conversation_id=${id} document_id=${documentId}`)
    setActiveConversationId(id)
    setSidebarRefreshTrigger(prev => prev + 1)
  }, [documentId])

  const handleMessageSent = useCallback(() => {
    setSidebarRefreshTrigger(prev => prev + 1)
  }, [])

  return (
    <div className="flex h-screen w-full flex-col bg-zinc-50 dark:bg-zinc-950 font-sans selection:bg-zinc-200 dark:selection:bg-zinc-800">
      {/* Workspace Header */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 bg-white px-4 sm:px-6 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="flex items-center justify-center w-8 h-8 rounded-full text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-800 hidden sm:block"></div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center">
              <FileText className="w-3.5 h-3.5 text-zinc-500" />
            </div>
            <span className="font-medium text-sm text-zinc-900 dark:text-zinc-100 truncate max-w-[150px] sm:max-w-xs">
              Document Workspace
            </span>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat History Sidebar */}
        <ChatHistorySidebar
          accessToken={accessToken}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onNewChat={handleNewChat}
          refreshTrigger={sidebarRefreshTrigger}
        />

        {/* Document Viewer Side */}
        <div className="hidden lg:flex flex-1 flex-col bg-zinc-50/50 dark:bg-zinc-950/50 border-r border-zinc-200 dark:border-zinc-800 relative">
          <DocumentViewer documentId={documentId} accessToken={accessToken} />
        </div>

        {/* AI Chat Side */}
        <div className="w-full lg:w-[450px] xl:w-[500px] flex flex-col bg-white dark:bg-zinc-950 h-full relative z-10 shadow-[-4px_0_24px_-12px_rgba(0,0,0,0.1)] dark:shadow-[-4px_0_24px_-12px_rgba(0,0,0,0.5)]">
          <ChatPanel
            documentId={documentId}
            accessToken={accessToken}
            activeConversationId={activeConversationId}
            onConversationCreated={handleConversationCreated}
            onMessageSent={handleMessageSent}
          />
        </div>
      </div>
    </div>
  )
}
