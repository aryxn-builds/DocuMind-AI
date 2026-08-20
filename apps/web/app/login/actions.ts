'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { headers } from 'next/headers'
import { createClient } from '@/utils/supabase/server'

export async function login(formData: FormData) {
  const email = formData.get('email') as string
  const password = formData.get('password') as string
  const supabase = await createClient()

  const { error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) {
    console.error('[Auth Error] signInWithPassword failed:', {
      message: error.message,
      status: error.status,
      name: error.name
    })
    redirect(`/login?error=${encodeURIComponent(error.message)}`)
  }

  revalidatePath('/', 'layout')
  redirect('/dashboard')
}

export async function signup(formData: FormData) {
  const email = formData.get('email') as string
  const password = formData.get('password') as string
  const fullName = formData.get('fullName') as string
  const supabase = await createClient()

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName,
      },
    }
  })

  if (error) {
    console.error('[Auth Error] signUp failed:', {
      message: error.message,
      status: error.status,
      name: error.name
    })
    redirect(`/signup?error=${encodeURIComponent(error.message)}`)
  }

  if (data?.user && !data.session) {
    // Email confirmation is required
    redirect('/signup?message=Check your email to confirm your account')
  }

  revalidatePath('/', 'layout')
  redirect('/dashboard')
}

export async function signout() {
  const supabase = await createClient()
  await supabase.auth.signOut()
  redirect('/login')
}

export async function forgotPassword(formData: FormData) {
  const email = formData.get('email') as string
  const supabase = await createClient()
  const origin = (await headers()).get('origin') ?? 'http://localhost:3000'

  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${origin}/auth/callback?next=/reset-password`,
  })

  if (error) {
    console.error('[Auth Error] resetPasswordForEmail failed:', error)
  }

  redirect('/forgot-password?message=If an account exists, a password reset link has been sent to your email.')
}

export async function resetPassword(formData: FormData) {
  const password = formData.get('password') as string
  const confirmPassword = formData.get('confirmPassword') as string

  if (!password || !confirmPassword) {
    redirect(`/reset-password?error=${encodeURIComponent('Both fields are required.')}`)
  }

  if (password !== confirmPassword) {
    redirect(`/reset-password?error=${encodeURIComponent('Passwords do not match.')}`)
  }

  const supabase = await createClient()

  const { error } = await supabase.auth.updateUser({
    password: password
  })

  if (error) {
    console.error('[Auth Error] resetPassword failed:', error)
    redirect(`/reset-password?error=${encodeURIComponent(error.message)}`)
  }

  // Very important: Sign out so the user does not stay logged in with a recovery session
  await supabase.auth.signOut()

  redirect('/login?reset=success')
}
