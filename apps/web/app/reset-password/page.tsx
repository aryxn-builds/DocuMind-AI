import { resetPassword } from '../login/actions'
import { SubmitButton } from '@/components/SubmitButton'
import { PasswordInput } from '@/components/PasswordInput'
import { createClient } from '@/utils/supabase/server'
import Link from 'next/link'

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>
}) {
  const { error } = await searchParams
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  const isRecovery = (user as any)?.amr?.some((method: any) => method.method === 'recovery')

  if (!user || !isRecovery) {
    return (
      <div className="flex min-h-screen w-full flex-col bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 font-sans selection:bg-zinc-200 dark:selection:bg-zinc-800">
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-sm text-center">
            <h1 className="text-xl font-semibold mb-2">Invalid or expired reset session</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-6">
              Please request a new password reset link.
            </p>
            <Link 
              href="/forgot-password" 
              className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
            >
              Request new link
            </Link>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen w-full flex-col bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 font-sans selection:bg-zinc-200 dark:selection:bg-zinc-800">
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center flex flex-col items-center">
            <div className="w-12 h-12 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 rounded-xl flex items-center justify-center font-bold text-2xl leading-none mb-6 shadow-sm">
              D
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100 mb-2">
              Update password
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Please enter your new password
            </p>
          </div>

          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800/60 bg-white/50 dark:bg-zinc-900/50 p-6 sm:p-8 backdrop-blur-sm shadow-xl shadow-zinc-200/20 dark:shadow-black/40">
            <form action={resetPassword} className="flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-zinc-900 dark:text-zinc-200"
                >
                  New Password
                </label>
                <PasswordInput
                  id="password"
                  name="password"
                  autoComplete="new-password"
                  required
                  minLength={6}
                />
              </div>

              <div className="flex flex-col gap-2">
                <label
                  htmlFor="confirmPassword"
                  className="text-sm font-medium text-zinc-900 dark:text-zinc-200"
                >
                  Confirm New Password
                </label>
                <PasswordInput
                  id="confirmPassword"
                  name="confirmPassword"
                  autoComplete="new-password"
                  required
                  minLength={6}
                />
              </div>

              {error && (
                <div className="rounded-lg bg-red-50 dark:bg-red-950/50 p-3 text-sm font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900/50">
                  {error}
                </div>
              )}

              <SubmitButton loadingText="Updating password...">
                Update Password
              </SubmitButton>
            </form>
          </div>
        </div>
      </main>
    </div>
  )
}
