'use client'

import { useState, useCallback } from 'react'
import { ChatHistorySidebar } from './ChatHistorySidebar'
import { ChatPanel } from './ChatPanel'
import { DocumentViewer } from './DocumentViewer'
import { ArrowLeft, FileText } from 'lucide-react'
import Link from 'next/link'

interface DocumentWorkspaceClientProps {
  documentId: string
  accessToken: string
}

export function DocumentWorkspaceClient({ documentId, accessToken }: DocumentWorkspaceClientProps) {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0)

  const handleSelectConversation = useCallback((id: string) => {
    setActiveConversationId(id)
  }, [])

  const handleNewChat = useCallback(() => {
    setActiveConversationId(null)
  }, [])

  const handleConversationCreated = useCallback((id: string) => {
    setActiveConversationId(id)
    setSidebarRefreshTrigger(prev => prev + 1)
  }, [])

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
