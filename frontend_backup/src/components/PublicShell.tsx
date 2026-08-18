import { ArrowRight, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/auth-context'

export function PublicShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const { isAuthenticated, logout, user } = useAuth()

  return (
    <div className="min-h-screen px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-7xl flex-col">
        <header className="flex flex-wrap items-center justify-between gap-4 py-4">
          <Link className="flex items-center gap-3" to={isAuthenticated ? '/dashboard' : '/'}>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-container text-sm font-black text-on-primary shadow-lg shadow-primary/20">
              ID
            </div>
            <div>
              <p className="text-sm font-semibold text-on-surface">InsightDocs</p>
              <p className="text-[11px] uppercase tracking-[0.28em] text-on-surface-variant">
                Threaded Ask Your PDF
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-2">
            {isAuthenticated ? (
              <>
                <button
                  className="inline-flex items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low px-4 py-2 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface"
                  onClick={() => navigate('/dashboard')}
                  type="button"
                >
                  <Sparkles className="h-4 w-4" />
                  Dashboard
                </button>
                <button
                  className="inline-flex items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low px-4 py-2 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface"
                  onClick={() => {
                    logout()
                    navigate('/login')
                  }}
                  type="button"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <button
                  className="inline-flex items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low px-4 py-2 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface"
                  onClick={() => navigate('/login')}
                  type="button"
                >
                  Sign in
                </button>
                <button
                  className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-primary to-primary-container px-4 py-2 text-sm font-semibold text-on-primary transition hover:opacity-95"
                  onClick={() => navigate('/register')}
                  type="button"
                >
                  Create account
                  <ArrowRight className="h-4 w-4" />
                </button>
              </>
            )}
          </div>
        </header>

        <main className="flex-1 pb-6">{children}</main>

        <footer className="pb-4 text-center text-xs uppercase tracking-[0.28em] text-on-surface-variant">
          {user ? `Signed in as ${user.email}` : 'InsightDocs'}
        </footer>
      </div>
    </div>
  )
}
