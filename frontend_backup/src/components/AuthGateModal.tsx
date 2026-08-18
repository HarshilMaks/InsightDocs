import { ArrowRight, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '@/context/auth-context'
import { useWorkspace } from '@/context/workspace-context'
import { getApiErrorMessage } from '@/lib/api'
import { cn } from '@/lib/utils'

const intentCopy: Record<string, { title: string; subtitle: string }> = {
  upload: {
    title: 'Sign in to upload',
    subtitle: 'Create an account to upload documents and ask questions.',
  },
  ask: {
    title: 'Sign in to ask',
    subtitle: 'Create an account to ask questions about your documents.',
  },
}

export function AuthGateModal() {
  const { login, register } = useAuth()
  const { authGateOpen, setAuthGateOpen, pendingIntent } = useWorkspace()
  const [mode, setMode] = useState<'login' | 'register'>('register')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const firstInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (authGateOpen) {
      dialogRef.current?.showModal()
      setTimeout(() => firstInputRef.current?.focus(), 50)
    } else {
      dialogRef.current?.close()
    }
  }, [authGateOpen])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    const handleClose = () => setAuthGateOpen(false)
    dialog.addEventListener('close', handleClose)
    return () => dialog.removeEventListener('close', handleClose)
  }, [setAuthGateOpen])

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      if (mode === 'register') {
        await register({ name, email, password })
      }
      await login({ email, password })
      setAuthGateOpen(false)
      // Intent is preserved in workspace context - the parent will handle resumption
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  const close = () => {
    setAuthGateOpen(false)
  }

  const intentType = pendingIntent?.type ?? 'upload'
  const copy = intentCopy[intentType] ?? intentCopy.upload

  if (!authGateOpen) return null

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-[100] m-0 h-full w-full max-w-none border-0 bg-black/60 p-0 backdrop-blur-sm open:flex open:items-center open:justify-center"
      onClick={(e) => {
        if (e.target === dialogRef.current) close()
      }}
    >
      <div
        className="relative w-full max-w-sm rounded-2xl border border-white/[0.08] bg-[hsl(227,28%,9%)] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          type="button"
          className="absolute right-3 top-3 flex h-7 w-7 items-center justify-center rounded-lg text-white/40 transition hover:bg-white/[0.06] hover:text-white/70"
          onClick={close}
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Header */}
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-white/90">{copy.title}</h2>
          <p className="mt-1 text-sm text-white/50">{copy.subtitle}</p>
        </div>

        {/* Form */}
        <form className="space-y-3" onSubmit={(e) => void handleSubmit(e)}>
          {mode === 'register' && (
            <label className="block">
              <span className="text-xs font-medium text-white/50">Name</span>
              <input
                ref={firstInputRef}
                className="mt-1 w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white/90 outline-none placeholder:text-white/25 focus:border-sky-500/40"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                autoComplete="name"
              />
            </label>
          )}

          <label className="block">
            <span className="text-xs font-medium text-white/50">Email</span>
            <input
              ref={mode === 'login' ? firstInputRef : undefined}
              className="mt-1 w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white/90 outline-none placeholder:text-white/25 focus:border-sky-500/40"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </label>

          <label className="block">
            <span className="text-xs font-medium text-white/50">Password</span>
            <input
              className="mt-1 w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white/90 outline-none placeholder:text-white/25 focus:border-sky-500/40"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
            />
          </label>

          {error && (
            <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className={cn(
              'flex w-full items-center justify-center gap-2 rounded-lg bg-sky-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-sky-400 disabled:opacity-50',
            )}
          >
            {mode === 'register' ? 'Create account' : 'Sign in'}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </form>

        {/* Mode switch */}
        <div className="mt-4 flex items-center justify-between text-xs text-white/40">
          <span>{mode === 'register' ? 'Already have an account?' : 'New to InsightDocs?'}</span>
          <button
            type="button"
            className="font-medium text-sky-400 transition hover:text-sky-300"
            onClick={() => {
              setMode(mode === 'register' ? 'login' : 'register')
              setError(null)
            }}
          >
            {mode === 'register' ? 'Sign in' : 'Create account'}
          </button>
        </div>
      </div>
    </dialog>
  )
}
