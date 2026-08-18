import { useNavigate } from 'react-router-dom'
import { KeyRound, ShieldCheck, ArrowRight } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { useAuth } from '@/context/auth-context'

export function SettingsView() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const rows = [
    { label: 'Name', value: user?.name ?? '—' },
    { label: 'Email', value: user?.email ?? '—' },
    {
      label: 'Member since',
      value: user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—',
    },
  ]

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 p-4 md:p-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Settings</h2>
        <p className="text-sm text-muted-foreground">Your account and model configuration.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Account</CardTitle>
          <CardDescription>Details from your InsightDocs profile.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-0">
          {rows.map((row, index) => (
            <div key={row.label}>
              {index > 0 && <Separator />}
              <div className="flex items-center justify-between gap-4 py-3 text-sm">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="truncate font-medium">{row.value}</span>
              </div>
            </div>
          ))}
          <Separator />
          <div className="flex items-center justify-between gap-4 py-3 text-sm">
            <span className="text-muted-foreground">Role</span>
            <Badge variant="secondary" className="font-normal capitalize">
              {user?.role ?? 'member'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="size-4 text-primary" />
            Model access
          </CardTitle>
          <CardDescription>
            Bring your own Gemini key, or keep using the platform key.
          </CardDescription>
        </CardHeader>
        <CardFooter className="border-t">
          <Button variant="outline" onClick={() => navigate('/byok')}>
            Manage API key
            <ArrowRight className="size-4" />
          </Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="size-4 text-primary" />
            Data handling
          </CardTitle>
          <CardDescription>How your documents are stored and isolated.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>Documents are scoped to your account at both the database and vector-search layers.</p>
          <p>API keys are encrypted with AES-256 before storage and are never returned in plain text.</p>
          <p>Deleting a document removes its indexed content along with the file record.</p>
        </CardContent>
      </Card>
    </div>
  )
}
