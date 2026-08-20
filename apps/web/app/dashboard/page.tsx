import Link from 'next/link'
import { signout } from '../login/actions'
import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { DocumentDashboard } from '@/components/DocumentDashboard'
import { LogOut } from 'lucide-react'

export default async function DashboardPage() {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 dark:bg-zinc-950 font-sans selection:bg-zinc-200 dark:selection:bg-zinc-800">
      <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-zinc-200 bg-white/80 px-6 dark:border-zinc-800/50 dark:bg-zinc-950/80 backdrop-blur-md">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 rounded-md flex items-center justify-center font-bold text-xl leading-none">
            D
          </div>
          <span className="font-semibold text-lg tracking-tight text-zinc-900 dark:text-zinc-50">DocuMind AI</span>
        </Link>
        <div className="flex items-center gap-4">
          <div className="hidden sm:block text-sm font-medium text-zinc-600 dark:text-zinc-400">
            {user.email}
          </div>
          <div className="w-px h-4 bg-zinc-200 dark:bg-zinc-800 hidden sm:block"></div>
          <form action={signout}>
            <button
              type="submit"
              className="flex items-center gap-1.5 text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </form>
        </div>
      </header>
      
      <main className="flex-1 w-full max-w-6xl mx-auto p-6 md:p-8 lg:py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 mb-2">
            Dashboard
          </h1>
          <p className="text-base text-zinc-600 dark:text-zinc-400">
            Upload, manage, and chat with your documents.
          </p>
        </div>
        <DocumentDashboard />
      </main>
    </div>
  )
}
