import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { DocumentWorkspaceClient } from '@/components/DocumentWorkspaceClient'

export default async function DocumentWorkspacePage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  
  const supabase = await createClient()
  
  // Use getUser() for secure Server-Side authentication verification
  const { data: { user }, error } = await supabase.auth.getUser()
  
  if (error || !user) {
    redirect('/login')
  }

  // Get the session solely to retrieve the access_token to pass to Client Components
  const { data: { session } } = await supabase.auth.getSession()
  const accessToken = session?.access_token || ''
  
  return (
    <DocumentWorkspaceClient documentId={id} accessToken={accessToken} />
  )
}
