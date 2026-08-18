import { AuthCard } from '@/components/AuthCard'
import { PublicShell } from '@/components/PublicShell'

export default function LoginPage() {
  return (
    <PublicShell>
      <div className="flex items-center justify-center py-10">
        <div className="w-full max-w-6xl">
          <AuthCard mode="login" />
        </div>
      </div>
    </PublicShell>
  )
}
