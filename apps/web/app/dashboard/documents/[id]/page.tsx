import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { ChatPanel } from '@/components/ChatPanel'

export default async function DocumentWorkspacePage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  
  // Verify auth
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!session) {
    redirect('/login')
  }
  
  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden mt-0 border-t border-zinc-200 dark:border-zinc-800">
      {/* Document Viewer Side (Placeholder for MVP) */}
      <div className="hidden lg:flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800 relative">
        <div className="absolute inset-0 flex items-center justify-center p-8">
          <div className="text-center max-w-sm">
            <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-100 mb-2">Document Workspace</h3>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Document viewing is not yet supported in this view. Use the Chat Panel to interact with this document via AI.
            </p>
          </div>
        </div>
      </div>
      
      {/* AI Chat Side */}
      <div className="w-full lg:w-[450px] xl:w-[500px] flex flex-col bg-white dark:bg-zinc-950 h-full">
        <ChatPanel documentId={id} accessToken={session.access_token} />
      </div>
    </div>
  )
}
