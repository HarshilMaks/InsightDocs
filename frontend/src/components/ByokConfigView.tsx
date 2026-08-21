import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Eye, EyeOff, KeyRound, Loader2, ShieldCheck, Trash2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  getByokStatus,
  saveApiKey,
  removeApiKey,
  updateByokSettings,
  getApiErrorMessage,
} from '@/lib/api'

const KEY_PATTERN = /^(?:AIza[A-Za-z0-9_-]{31,41}|AQ\.[A-Za-z0-9_-]{20,200})$/

export function ByokConfigView() {
  const queryClient = useQueryClient()
  const [keyInput, setKeyInput] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const statusQuery = useQuery({ queryKey: ['byok-status'], queryFn: getByokStatus })
  const status = statusQuery.data
  const isUsable = status?.status === 'healthy' || status?.status === 'degraded'

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['byok-status'] })

  const saveMutation = useMutation({
    mutationFn: (key: string) => saveApiKey(key),
    onSuccess: (data) => {
      setKeyInput('')
      setError(null)
      void invalidate()
      toast.success('API key saved', {
        description: data.active_model ? `Active model: ${data.active_model}` : data.message,
      })
    },
    onError: (err) => {
      const message = getApiErrorMessage(err)
      setError(message)
      toast.error('Could not save the key', { description: message })
    },
  })

  const removeMutation = useMutation({
    mutationFn: removeApiKey,
    onSuccess: () => {
      void invalidate()
      toast.success('API key removed')
    },
    onError: (err) => toast.error('Could not remove the key', { description: getApiErrorMessage(err) }),
  })

  const toggleMutation = useMutation({
    mutationFn: (enabled: boolean) => updateByokSettings(enabled),
    onSuccess: () => void invalidate(),
    onError: (err) => toast.error('Could not update setting', { description: getApiErrorMessage(err) }),
  })

  const handleSave = () => {
    const trimmed = keyInput.trim()
    if (!KEY_PATTERN.test(trimmed)) {
      setError('Use a Gemini key beginning with "AIza" or a current authorization key beginning with "AQ.".')
      return
    }
    setError(null)
    saveMutation.mutate(trimmed)
  }

  const cards = [
    {
      label: 'Your key',
      value: status?.has_api_key ? 'Saved' : 'Not saved',
      tone: status?.has_api_key ? 'text-[color:var(--success)]' : 'text-muted-foreground',
    },
    {
      label: 'Routing',
      value: status?.byok_enabled ? 'Your key' : 'Platform key',
      tone: status?.byok_enabled ? 'text-primary' : 'text-muted-foreground',
    },
    {
      label: 'Health',
      value: status?.status ?? 'unknown',
      tone: isUsable ? 'text-[color:var(--success)]' : 'text-[color:var(--warning)]',
    },
    {
      label: 'Active model',
      value: status?.active_model ?? 'None',
      tone: status?.active_model ? 'text-foreground' : 'text-muted-foreground',
    },
  ]

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 p-4 md:p-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">API key</h2>
        <p className="text-sm text-muted-foreground">
          Use your own Gemini key. It is encrypted before storage and never returned in plain text.
        </p>
      </div>

      {/* Status */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.label} className="gap-0 py-0">
            <CardContent className="p-4">
              <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                {card.label}
              </p>
              {statusQuery.isLoading ? (
                <Skeleton className="mt-2 h-5 w-20" />
              ) : (
                <p className={`mt-1 truncate text-sm font-medium ${card.tone}`}>{card.value}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {status?.message && (
        <p className="text-xs text-muted-foreground">{status.message}</p>
      )}

      {/* Key management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="size-4 text-primary" />
            Gemini API key
          </CardTitle>
          <CardDescription>
            Saving a key runs a live capability check and selects the best available model.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-2">
            <Label htmlFor="gemini-key">
              {status?.has_api_key ? 'Replace key' : 'Key'}
            </Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="gemini-key"
                  type={showKey ? 'text' : 'password'}
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                  placeholder="AIza… or AQ.…"
                  autoComplete="off"
                  spellCheck={false}
                  aria-invalid={Boolean(error)}
                  className="pr-9 font-mono"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={showKey ? 'Hide key' : 'Show key'}
                  className="absolute top-1/2 right-1 size-7 -translate-y-1/2"
                  onClick={() => setShowKey((v) => !v)}
                >
                  {showKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </Button>
              </div>
              <Button onClick={handleSave} disabled={!keyInput.trim() || saveMutation.isPending}>
                {saveMutation.isPending && <Loader2 className="size-4 animate-spin" />}
                Save
              </Button>
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </CardContent>

        {status?.has_api_key && (
          <CardFooter className="border-t">
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              disabled={removeMutation.isPending}
              onClick={() => removeMutation.mutate()}
            >
              {removeMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Trash2 className="size-4" />
              )}
              Remove saved key
            </Button>
          </CardFooter>
        )}
      </Card>

      {/* Routing toggle */}
      <Card>
        <CardContent className="flex items-center justify-between gap-4 pt-6">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 size-4 text-primary" />
            <div className="space-y-0.5">
              <Label htmlFor="byok-toggle" className="text-sm font-medium">
                Route requests through your key
              </Label>
              <p className="text-xs text-muted-foreground">
                {status?.has_api_key
                  ? isUsable
                    ? 'Your saved key is healthy and can serve requests.'
                    : 'Save a healthy key before enabling this.'
                  : 'Save a key first to enable this.'}
              </p>
            </div>
          </div>
          <Switch
            id="byok-toggle"
            checked={Boolean(status?.byok_enabled)}
            disabled={!status?.has_api_key || !isUsable || toggleMutation.isPending}
            onCheckedChange={(checked) => toggleMutation.mutate(checked)}
          />
        </CardContent>
      </Card>

      {/* Models */}
      {status?.available_models && status.available_models.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Available models</CardTitle>
            <CardDescription>Reachable with the saved key, in fallback order.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-1.5">
            {status.available_models.map((model) => (
              <Badge
                key={model}
                variant="outline"
                className={
                  model === status.active_model
                    ? 'border-primary/40 font-mono text-xs text-primary'
                    : 'font-mono text-xs'
                }
              >
                {model}
              </Badge>
            ))}
          </CardContent>
          {status.checked_at && (
            <CardFooter className="border-t">
              <p className="text-xs text-muted-foreground">
                Last checked {new Date(status.checked_at).toLocaleString()}
              </p>
            </CardFooter>
          )}
        </Card>
      )}
    </div>
  )
}
