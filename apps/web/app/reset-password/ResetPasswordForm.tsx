'use client'

import { useState } from 'react'
import { resetPassword } from '../login/actions'
import { SubmitButton } from '@/components/SubmitButton'
import { PasswordInput } from '@/components/PasswordInput'

export function ResetPasswordForm({ initialError }: { initialError?: string }) {
  const [error, setError] = useState<string | null>(initialError || null)

  const handleSubmit = async (formData: FormData) => {
    const password = formData.get('password') as string
    const confirmPassword = formData.get('confirmPassword') as string

    if (!password || !confirmPassword) {
      setError('Both fields are required.')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setError(null)
    
    // Server action handles the rest (update, sign out, redirect)
    await resetPassword(formData)
  }

  return (
    <form action={handleSubmit} className="flex flex-col gap-5">
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
          minLength={8}
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
          minLength={8}
        />
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950/50 p-3 text-sm font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900/50">
          {error}
        </div>
      )}

      <SubmitButton loadingText="Updating password...">
        Reset Password
      </SubmitButton>
    </form>
  )
}
