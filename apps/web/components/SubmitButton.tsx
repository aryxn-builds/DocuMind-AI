'use client'

import { useFormStatus } from 'react-dom'

export function SubmitButton({
  children,
  loadingText,
  className,
}: {
  children: React.ReactNode
  loadingText: string
  className?: string
}) {
  const { pending } = useFormStatus()

  return (
    <button
      type="submit"
      disabled={pending}
      className={className || "mt-2 w-full rounded-lg bg-zinc-900 py-2.5 text-sm font-medium text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 transition-colors shadow-sm disabled:opacity-50"}
    >
      {pending ? loadingText : children}
    </button>
  )
}
