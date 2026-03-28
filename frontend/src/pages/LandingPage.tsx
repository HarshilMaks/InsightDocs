import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
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
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-lg font-bold text-white mx-auto">
              ID
            </div>
            <div>
              <h1 className="text-3xl font-semibold text-gray-900">InsightDocs</h1>
              <p className="mt-2 text-gray-600">Ask Your PDF, better</p>
            </div>
          </div>

          <div className="space-y-3">
            <Link
              to="/register"
              className="block w-full rounded-lg bg-blue-600 px-5 py-3 text-center text-sm font-semibold text-white transition hover:bg-blue-700"
            >
              Create account
            </Link>
            <Link
              to="/login"
              className="block w-full rounded-lg border border-gray-300 bg-white px-5 py-3 text-center text-sm font-semibold text-gray-900 transition hover:bg-gray-50"
            >
              Sign in with Email
            </Link>
          </div>

          <p className="text-center text-xs text-gray-500">
            By signing in, you agree to our{' '}
            <a href="#" className="text-blue-600 hover:underline">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="#" className="text-blue-600 hover:underline">
              Privacy Policy
            </a>
          </p>
        </motion.div>
      </div>
    </PublicShell>
  )
}
