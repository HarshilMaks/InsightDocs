import { motion } from 'framer-motion'
import { ArrowRight, BookOpenText, CircleDashed, ShieldCheck, Sparkles } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/auth-context'
import { getApiErrorMessage } from '@/lib/api'
import { cn } from '@/lib/utils'

interface AuthCardProps {
  mode: 'login' | 'register'
}

const features = [
  {
    icon: BookOpenText,
    title: 'Citation-backed answers',
    description: 'Every answer is grounded in source chunks from your uploaded documents.',
  },
  {
    icon: CircleDashed,
    title: 'Threaded follow-ups',
    description: 'Conversation ids keep the chat moving naturally across multiple turns.',
  },
  {
    icon: ShieldCheck,
    title: 'BYOK control',
    description: 'Use your own Gemini key when you want private, operator-free inference.',
  },
]

export function AuthCard({ mode }: AuthCardProps) {
  const navigate = useNavigate()
  const { login, register } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isRegister = mode === 'register'

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      if (isRegister) {
        await register({ name, email, password })
      }

      await login({ email, password })
      navigate('/dashboard')
    } catch (submitError) {
      setError(getApiErrorMessage(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <motion.section
        animate={{ opacity: 1, y: 0 }}
        className="rounded-[2rem] border border-outline-variant/15 bg-gradient-to-br from-primary/10 via-surface-container-low to-surface-container-low/80 p-8 shadow-xl shadow-black/10"
        initial={{ opacity: 0, y: 12 }}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-container text-sm font-black text-on-primary">
            ID
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">InsightDocs</p>
            <h1 className="text-2xl font-semibold text-on-surface">Ask Your PDF, but better.</h1>
          </div>
        </div>

        <p className="mt-5 max-w-xl text-sm leading-6 text-on-surface-variant">
          Upload documents, ask natural language questions, and get back threaded answers with
          exact citation metadata. The UI is designed for serious reading, quick follow-ups, and
          deep analysis.
        </p>

        <div className="mt-8 space-y-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="flex gap-4 rounded-3xl border border-outline-variant/15 bg-surface-container-low px-4 py-4"
            >
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <feature.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-on-surface">{feature.title}</p>
                <p className="mt-1 text-sm leading-6 text-on-surface-variant">{feature.description}</p>
              </div>
            </div>
          ))}
        </div>
      </motion.section>

      <motion.section
        animate={{ opacity: 1, y: 0 }}
        className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/80 p-6 shadow-xl shadow-black/10"
        initial={{ opacity: 0, y: 12 }}
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
              {isRegister ? 'Create your account' : 'Welcome back'}
            </p>
            <h2 className="text-2xl font-semibold text-on-surface">
              {isRegister ? 'Start a new workspace' : 'Sign in to your workspace'}
            </h2>
          </div>
        </div>

        <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
          {isRegister && (
            <label className="block space-y-2">
              <span className="text-sm font-medium text-on-surface">Name</span>
              <input
                className="w-full rounded-2xl border border-outline-variant/15 bg-surface-container px-4 py-3 text-sm text-on-surface outline-none ring-0 transition placeholder:text-on-surface-variant focus:border-primary/40"
                onChange={(event) => setName(event.target.value)}
                placeholder="John Doe"
                value={name}
              />
            </label>
          )}

          <label className="block space-y-2">
            <span className="text-sm font-medium text-on-surface">Email</span>
            <input
              className="w-full rounded-2xl border border-outline-variant/15 bg-surface-container px-4 py-3 text-sm text-on-surface outline-none ring-0 transition placeholder:text-on-surface-variant focus:border-primary/40"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="johndoe@example.com"
              type="email"
              value={email}
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-on-surface">Password</span>
            <input
              className="w-full rounded-2xl border border-outline-variant/15 bg-surface-container px-4 py-3 text-sm text-on-surface outline-none ring-0 transition placeholder:text-on-surface-variant focus:border-primary/40"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              type="password"
              value={password}
            />
          </label>

          {error && (
            <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {error}
            </div>
          )}

          <button
            className={cn(
              'inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-primary to-primary-container px-5 py-3 text-sm font-semibold text-on-primary transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60',
            )}
            disabled={isSubmitting}
            type="submit"
          >
            {isRegister ? 'Create account' : 'Sign in'}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <div className="mt-6 flex items-center justify-between gap-3 text-sm text-on-surface-variant">
          <span>
            {isRegister ? 'Already have an account?' : 'New to InsightDocs?'}
          </span>
          <Link
            className="font-medium text-primary transition hover:text-primary/80"
            to={isRegister ? '/login' : '/register'}
          >
            {isRegister ? 'Sign in' : 'Create one'}
          </Link>
        </div>
      </motion.section>
    </div>
  )
}
