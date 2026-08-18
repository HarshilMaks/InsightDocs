import { useEffect, useRef, useState } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { useAuth } from '@/context/auth-context'
import { getApiErrorMessage } from '@/lib/api'
import { BrandLogo } from './BrandLogo'

const GOOGLE_CLIENT_ID = '402765757172-vb1j3ohjduunuc8ujpabe3oetihl2n0g.apps.googleusercontent.com'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
}

type Mode = 'login' | 'register'

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const { login, loginWithGoogle, register } = useAuth()
  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const googleBtnRef = useRef<HTMLDivElement>(null)

  // Load Google Identity Services script and render the button
  useEffect(() => {
    if (!isOpen) return

    const renderGoogleButton = () => {
      if (!googleBtnRef.current || !window.google?.accounts?.id) return
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
      })
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'filled_black',
        size: 'large',
        width: '100%',
        text: 'continue_with',
        shape: 'rectangular',
      })
    }

    // If script is already loaded, just render
    if (window.google?.accounts?.id) {
      renderGoogleButton()
      return
    }

    // Load the script
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = renderGoogleButton
    document.head.appendChild(script)

    return () => {
      // Cleanup not needed — script stays loaded
    }
  }, [isOpen])

  const handleGoogleResponse = async (response: { credential: string }) => {
    setError(null)
    setIsSubmitting(true)
    try {
      await loginWithGoogle(response.credential)
      toast.success('Signed in with Google')
      onClose()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      if (mode === 'register') {
        await register({ name, email, password })
      }
      await login({ email, password })
      toast.success(mode === 'register' ? 'Account created' : 'Signed in')
      setPassword('')
      onClose()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  const switchMode = (next: Mode) => {
    setMode(next)
    setError(null)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader className="items-center text-center">
          <div className="mb-1 flex size-11 items-center justify-center rounded-lg border bg-card">
            <BrandLogo size={26} />
          </div>
          <DialogTitle>
            {mode === 'login' ? 'Sign in to InsightDocs' : 'Create your account'}
          </DialogTitle>
          <DialogDescription>
            Upload documents and get answers backed by verifiable evidence.
          </DialogDescription>
        </DialogHeader>

        {/* Google Sign In Button */}
        <div ref={googleBtnRef} className="flex justify-center" />

        <div className="flex items-center gap-3">
          <Separator className="flex-1" />
          <span className="text-xs text-muted-foreground">or</span>
          <Separator className="flex-1" />
        </div>

        <Tabs value={mode} onValueChange={(v) => switchMode(v as Mode)}>
          <TabsList className="w-full">
            <TabsTrigger value="login" className="flex-1">Sign in</TabsTrigger>
            <TabsTrigger value="register" className="flex-1">Create account</TabsTrigger>
          </TabsList>

          {(['login', 'register'] as Mode[]).map((tab) => (
            <TabsContent key={tab} value={tab}>
              <form onSubmit={(e) => void submit(e)} className="grid gap-4">
                {tab === 'register' && (
                  <div className="grid gap-2">
                    <Label htmlFor="auth-name">Name</Label>
                    <Input
                      id="auth-name"
                      required
                      autoComplete="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Your name"
                    />
                  </div>
                )}

                <div className="grid gap-2">
                  <Label htmlFor={`auth-email-${tab}`}>Email</Label>
                  <Input
                    id={`auth-email-${tab}`}
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    aria-invalid={Boolean(error)}
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor={`auth-password-${tab}`}>Password</Label>
                  <Input
                    id={`auth-password-${tab}`}
                    type="password"
                    required
                    autoComplete={tab === 'register' ? 'new-password' : 'current-password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    aria-invalid={Boolean(error)}
                  />
                  {tab === 'register' && (
                    <p className="text-xs text-muted-foreground">Use at least 8 characters.</p>
                  )}
                </div>

                {error && (
                  <div
                    role="alert"
                    aria-live="polite"
                    className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
                  >
                    <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="size-4 animate-spin" />}
                  {tab === 'login' ? 'Sign in' : 'Create account'}
                </Button>
              </form>
            </TabsContent>
          ))}
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

// Type declaration for Google Identity Services
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void }) => void
          renderButton: (element: HTMLElement, options: Record<string, unknown>) => void
        }
      }
    }
  }
}
