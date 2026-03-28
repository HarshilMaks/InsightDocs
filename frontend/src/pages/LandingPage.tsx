import { useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { PublicShell } from '@/components/PublicShell'
import { useAuth } from '@/context/auth-context'

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
      <div className="flex items-center justify-center min-h-screen py-10">
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md space-y-8"
          initial={{ opacity: 0, y: 16 }}
        >
          <div className="space-y-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-container text-lg font-bold text-on-primary mx-auto">
              ID
            </div>
            <div>
              <h1 className="text-3xl font-semibold text-on-surface">InsightDocs</h1>
              <p className="mt-2 text-on-surface-variant">Ask Your PDF, better</p>
            </div>
          </div>

          <div className="space-y-3">
            <Link
              to="/register"
              className="block w-full rounded-lg bg-gradient-to-r from-primary to-primary-container px-5 py-3 text-center text-sm font-semibold text-on-primary transition hover:opacity-95"
            >
              Create account
            </Link>
            <Link
              to="/login"
              className="block w-full rounded-lg border border-outline-variant/15 bg-surface-container-low px-5 py-3 text-center text-sm font-semibold text-on-surface transition hover:bg-surface-container-high"
            >
              Sign in with Email
            </Link>
          </div>

          <p className="text-center text-xs text-on-surface-variant">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </motion.div>
      </div>
    </PublicShell>
  )
}
