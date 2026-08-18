import { useState } from 'react'
import { useAuth } from '@/context/auth-context'
import { getApiErrorMessage } from '@/lib/api'
import { BrandLogo } from './BrandLogo'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const { login, register } = useAuth()
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      if (activeTab === 'register') {
        await register({ name, email, password })
      }
      await login({ email, password })
      onClose()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <main className="w-full max-w-md flex flex-col items-center z-10">
        {/* Branding */}
        <div className="flex flex-col items-center mb-6 gap-3 text-center">
          <div className="p-2 border-4 border-[#ffcc00] brutal-shadow bg-zinc-900">
            <BrandLogo size={56} />
          </div>
          <h1 className="font-black text-3xl sm:text-4xl uppercase tracking-tighter text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            InsightDocs
          </h1>
          <p className="font-bold text-sm text-[#ffcc00] uppercase tracking-widest bg-zinc-900 px-3 py-1 brutal-shadow border-2 border-[#ffcc00]" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Provable RAG
          </p>
        </div>

        {/* Auth Card */}
        <div className="w-full bg-zinc-900 border-4 border-[#ffcc00] brutal-shadow p-6 sm:p-8 flex flex-col gap-6 relative overflow-hidden text-white">
          <button
            onClick={onClose}
            className="absolute top-3 right-3 text-white/60 hover:text-white p-1 hover:bg-white/10 transition-colors cursor-pointer"
          >
            ✕
          </button>

          {/* Tabs */}
          <div className="flex border-b-4 border-[#ffcc00]">
            <button
              type="button"
              onClick={() => { setActiveTab('login'); setError(null) }}
              className={`flex-1 py-3 font-bold uppercase text-sm tracking-wider transition-colors border-r-4 border-[#ffcc00] border-t-4 border-l-4 cursor-pointer ${
                activeTab === 'login' ? 'bg-[#ffcc00] text-black' : 'text-white hover:bg-zinc-800'
              }`}
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => { setActiveTab('register'); setError(null) }}
              className={`flex-1 py-3 font-bold uppercase text-sm tracking-wider transition-colors border-t-4 border-r-4 border-[#ffcc00] cursor-pointer ${
                activeTab === 'register' ? 'bg-[#ffcc00] text-black' : 'text-white hover:bg-zinc-800'
              }`}
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              Register
            </button>
          </div>

          {/* Form */}
          <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-5">
            {activeTab === 'register' && (
              <div className="flex flex-col gap-1.5">
                <label className="font-bold uppercase text-xs tracking-wide text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="YOUR NAME"
                  className="w-full bg-zinc-950 border-4 border-[#ffcc00] text-white px-4 py-2.5 focus:ring-0 focus:border-[#ffcc00] font-medium placeholder-zinc-500 text-sm"
                />
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="font-bold uppercase text-xs tracking-wide text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ENTER EMAIL"
                className="w-full bg-zinc-950 border-4 border-[#ffcc00] text-white px-4 py-2.5 focus:ring-0 focus:border-[#ffcc00] font-medium placeholder-zinc-500 text-sm"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-bold uppercase text-xs tracking-wide text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="ENTER PASSWORD"
                className="w-full bg-zinc-950 border-4 border-[#ffcc00] text-white px-4 py-2.5 focus:ring-0 focus:border-[#ffcc00] font-medium placeholder-zinc-500 text-sm"
              />
            </div>

            {error && (
              <div className="bg-red-900/30 border-2 border-red-500 px-4 py-2 text-sm text-red-300">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-[#ffcc00] text-black border-4 border-black py-3.5 px-6 font-black text-lg uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-[#e6b800] transition-all brutal-shadow disabled:opacity-50 cursor-pointer"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              {isSubmitting ? 'Loading...' : activeTab === 'login' ? 'Sign In →' : 'Create Account →'}
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}
