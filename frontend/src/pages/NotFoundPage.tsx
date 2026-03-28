import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PublicShell } from '@/components/PublicShell'

export default function NotFoundPage() {
  return (
    <PublicShell>
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">404</p>
        <h1 className="mt-3 text-4xl font-semibold text-on-surface">Page not found</h1>
        <p className="mt-3 max-w-lg text-sm leading-6 text-on-surface-variant">
          The page you are looking for does not exist. Head back to the dashboard or the landing
          page.
        </p>
        <Link
          className="mt-6 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-primary to-primary-container px-5 py-3 text-sm font-semibold text-on-primary transition hover:opacity-95"
          to="/dashboard"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
      </div>
    </PublicShell>
  )
}
