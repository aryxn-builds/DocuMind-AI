import Link from 'next/link'
import { signup } from '../login/actions'

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string, message?: string }>
}) {
  const { error, message } = await searchParams

  return (
    <div className="flex h-screen w-full items-center justify-center bg-zinc-50 dark:bg-zinc-950">
      <div className="w-full max-w-sm border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
            DocuMind AI
          </h1>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Create a new account
          </p>
        </div>

        <form action={signup} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
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
              required
              className="w-full border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500"
            />
          </div>

          <div className="flex flex-col gap-1.5">
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
              required
              className="w-full border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500"
            />
          </div>
          
          <div className="flex flex-col gap-1.5">
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
              required
              minLength={6}
              className="w-full border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-500"
            />
          </div>

          {error && (
            <div className="mt-2 text-sm font-medium text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {message && (
            <div className="mt-2 text-sm font-medium text-green-600 dark:text-green-400">
              {message}
            </div>
          )}

          <button
            type="submit"
            className="mt-2 w-full bg-zinc-900 py-2.5 text-sm font-medium text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 transition-colors"
          >
            Sign Up
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-zinc-600 dark:text-zinc-400">
          Already have an account?{' '}
          <Link
            href="/login"
            className="font-medium text-zinc-900 underline underline-offset-4 hover:text-zinc-700 dark:text-zinc-200 dark:hover:text-zinc-100"
          >
            Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
