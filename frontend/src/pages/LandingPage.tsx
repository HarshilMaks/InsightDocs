import { ArrowRight, BookOpenText, FileSearch, Layers3, MessageSquareQuote, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { PublicShell } from '@/components/PublicShell'
import { useAuth } from '@/context/auth-context'
import { StatCard } from '@/components/StatCard'

const features = [
  {
    icon: MessageSquareQuote,
    title: 'Threaded Ask Your PDF',
    description:
      'Keep one conversation id alive while the assistant remembers the prior turn and follows up naturally.',
  },
  {
    icon: FileSearch,
    title: 'Citations with context',
    description:
      'The right-side panel shows exact document names, chunks, page references, and spatial bbox metadata.',
  },
  {
    icon: Layers3,
    title: 'Workspace for teams',
    description:
      'Upload files, review tasks, manage API keys, and keep your knowledge base organized in one place.',
  },
]

export default function LandingPage() {
  const { isAuthenticated } = useAuth()

  return (
    <PublicShell>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-center lg:py-10">
        <motion.section
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
          initial={{ opacity: 0, y: 16 }}
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low px-4 py-2 text-xs uppercase tracking-[0.24em] text-on-surface-variant">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            AI-driven document intelligence
          </div>

          <div className="space-y-4">
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-on-surface sm:text-5xl lg:text-6xl">
              Turn uploaded documents into a{' '}
              <span className="bg-gradient-to-r from-primary to-primary-container bg-clip-text text-transparent">
                cited conversation
              </span>
              .
            </h1>
            <p className="max-w-2xl text-base leading-7 text-on-surface-variant sm:text-lg">
              InsightDocs combines threaded RAG chat, citation-backed answers, document actions,
              and BYOK controls in a premium workspace designed for serious reading.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-primary to-primary-container px-5 py-3 text-sm font-semibold text-on-primary transition hover:opacity-95"
              to={isAuthenticated ? '/dashboard' : '/register'}
            >
              {isAuthenticated ? 'Open dashboard' : 'Start free'}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              className="inline-flex items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low px-5 py-3 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface"
              to={isAuthenticated ? '/settings' : '/login'}
            >
              {isAuthenticated ? 'Configure BYOK' : 'Sign in'}
            </Link>
          </div>

          <div className="grid gap-4 pt-4 sm:grid-cols-3">
            <StatCard
              description="Conversation ids keep every follow-up connected."
              icon={MessageSquareQuote}
              label="Threaded chat"
              tone="primary"
              value="1 flow"
            />
            <StatCard
              description="Exact chunk, page, and bbox metadata for every answer."
              icon={FileSearch}
              label="Citation depth"
              tone="sky"
              value="100%"
            />
            <StatCard
              description="React 18, Tailwind v3, React Query, and framer-motion."
              icon={BookOpenText}
              label="Frontend stack"
              tone="emerald"
              value="Ready"
            />
          </div>
        </motion.section>

        <motion.section
          animate={{ opacity: 1, y: 0 }}
          className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/80 p-6 shadow-2xl shadow-black/10"
          initial={{ opacity: 0, y: 16 }}
        >
          <div className="rounded-[1.75rem] border border-outline-variant/15 bg-gradient-to-br from-surface-container-high to-surface-container-low px-6 py-6">
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
              Product surface
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-on-surface">
              Clean workspace, fast uploads, cited answers.
            </h2>
            <div className="mt-5 space-y-3 text-sm leading-6 text-on-surface-variant">
              <p>• Upload PDFs, docs, spreadsheets, and images.</p>
              <p>• Ask follow-ups using the same conversation id.</p>
              <p>• Inspect source snippets and page references alongside the answer.</p>
              <p>• Toggle BYOK and manage your Gemini API key from settings.</p>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="flex gap-4 rounded-3xl border border-outline-variant/15 bg-surface-container-low px-5 py-4"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <feature.icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold text-on-surface">{feature.title}</p>
                  <p className="mt-1 text-sm leading-6 text-on-surface-variant">
                    {feature.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </motion.section>
      </div>
    </PublicShell>
  )
}
