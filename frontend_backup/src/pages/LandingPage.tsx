import { useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCircle2, FileSearch, ShieldCheck, Sparkles, Zap } from 'lucide-react'
import { PublicShell } from '@/components/PublicShell'
import { useAuth } from '@/context/auth-context'

const features = [
  {
    icon: FileSearch,
    title: 'Pixel-level citations',
    description: 'Every answer links to the exact page and paragraph in your source document.',
  },
  {
    icon: CheckCircle2,
    title: 'Claim verification',
    description: 'Each sentence is independently verified as supported or unsupported by your documents.',
  },
  {
    icon: Zap,
    title: 'Hybrid retrieval',
    description: 'Dense + sparse vector search with cross-encoder reranking for high-precision answers.',
  },
  {
    icon: ShieldCheck,
    title: 'Bring your own key',
    description: 'Your Gemini API key, encrypted at rest. No data sent to third parties beyond your chosen LLM.',
  },
]

export default function LandingPage() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, navigate])

  if (isAuthenticated) {
    return null
  }

  return (
    <PublicShell>
      <div className="flex min-h-screen flex-col items-center justify-center px-4 py-16">
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-3xl space-y-12 text-center"
          initial={{ opacity: 0, y: 16 }}
        >
          {/* Hero */}
          <div className="space-y-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-container text-xl font-bold text-on-primary shadow-xl shadow-primary/20">
              ID
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-on-surface sm:text-5xl">
              InsightDocs
            </h1>
            <p className="mx-auto max-w-xl text-lg leading-relaxed text-on-surface-variant">
              Ask questions about your documents. Get answers backed by{' '}
              <span className="font-semibold text-primary">exact, verifiable evidence</span> —
              not vague citations.
            </p>
          </div>

          {/* CTA */}
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-primary to-primary-container px-6 py-3 text-sm font-semibold text-on-primary shadow-lg shadow-primary/20 transition hover:opacity-95"
            >
              <Sparkles className="h-4 w-4" />
              Get started free
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-xl border border-outline-variant/15 bg-surface-container-low px-6 py-3 text-sm font-semibold text-on-surface transition hover:bg-surface-container-high"
            >
              Sign in
            </Link>
          </div>

          {/* Features */}
          <div className="grid gap-4 text-left sm:grid-cols-2">
            {features.map((feature) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="rounded-2xl border border-outline-variant/15 bg-surface-container-low/70 p-5"
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <feature.icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="font-semibold text-on-surface">{feature.title}</p>
                    <p className="mt-1 text-sm leading-relaxed text-on-surface-variant">{feature.description}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Footer note */}
          <p className="text-xs text-on-surface-variant">
            Open source · Enterprise-grade architecture · No vendor lock-in
          </p>
        </motion.div>
      </div>
    </PublicShell>
  )
}
