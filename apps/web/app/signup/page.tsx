import Link from 'next/link'
import { signup } from '../login/actions'
import { ArrowLeft } from 'lucide-react'
import { SubmitButton } from '@/components/SubmitButton'

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string, message?: string }>
}) {
  const { error, message } = await searchParams

  return (
    <div className="flex min-h-screen w-full flex-col bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 font-sans selection:bg-zinc-200 dark:selection:bg-zinc-800">
      {/* Simple Header */}
      <header className="w-full p-6">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to home
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center p-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center flex flex-col items-center">
            <div className="w-12 h-12 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 rounded-xl flex items-center justify-center font-bold text-2xl leading-none mb-6 shadow-sm">
              D
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100 mb-2">
              Create an account
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Start chatting with your documents today
            </p>
          </div>

          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800/60 bg-white/50 dark:bg-zinc-900/50 p-6 sm:p-8 backdrop-blur-sm shadow-xl shadow-zinc-200/20 dark:shadow-black/40">
            <form action={signup} className="flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <label
                  htmlFor="fullName"
                  className="text-sm font-medium text-zinc-900 dark:text-zinc-200"
                >
                  Full Name
                </label>
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  autoComplete="name"
                  required
                  className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-3 py-2.5 text-sm placeholder:text-zinc-400 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 focus:outline-none dark:focus:border-zinc-100 dark:focus:ring-zinc-100 transition-colors"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium text-zinc-900 dark:text-zinc-200"
                >
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-3 py-2.5 text-sm placeholder:text-zinc-400 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 focus:outline-none dark:focus:border-zinc-100 dark:focus:ring-zinc-100 transition-colors"
                />
              </div>
              
              <div className="flex flex-col gap-2">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-zinc-900 dark:text-zinc-200"
                >
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={6}
                  className="w-full rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-3 py-2.5 text-sm placeholder:text-zinc-400 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 focus:outline-none dark:focus:border-zinc-100 dark:focus:ring-zinc-100 transition-colors"
                />
              </div>

              {error && (
                <div className="rounded-lg bg-red-50 dark:bg-red-950/50 p-3 text-sm font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900/50">
                  {error}
                </div>
              )}

              {message && (
                <div className="rounded-lg bg-green-50 dark:bg-green-950/50 p-3 text-sm font-medium text-green-700 dark:text-green-400 border border-green-200 dark:border-green-900/50">
                  {message}
                </div>
              )}

              <SubmitButton loadingText="Signing up...">
                Sign Up
              </SubmitButton>
            </form>

            <div className="mt-6 text-center text-sm text-zinc-600 dark:text-zinc-400">
              Already have an account?{' '}
              <Link
                href="/login"
                className="font-medium text-zinc-900 hover:text-zinc-700 dark:text-zinc-200 dark:hover:text-zinc-50 transition-colors"
              >
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
