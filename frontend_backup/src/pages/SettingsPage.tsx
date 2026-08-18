import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, KeyRound, ShieldCheck, Trash2 } from 'lucide-react'
import {
  getApiErrorMessage,
  getByokStatus,
  removeApiKey,
  saveApiKey,
  updateByokSettings,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import type { GeminiHealthStatus, GeminiModelStatus } from '@/types'

const keyPattern = /^AIza[A-Za-z0-9_-]{31,41}$/

type Tone = 'emerald' | 'amber' | 'rose' | 'slate'

function toneClass(tone: Tone) {
  switch (tone) {
    case 'emerald':
      return 'text-emerald-300'
    case 'amber':
      return 'text-amber-300'
    case 'rose':
      return 'text-rose-300'
    case 'slate':
    default:
      return 'text-slate-300'
  }
}

function badgeClass(tone: Tone) {
  switch (tone) {
    case 'emerald':
      return 'bg-emerald-500/15 text-emerald-200'
    case 'amber':
      return 'bg-amber-500/15 text-amber-200'
    case 'rose':
      return 'bg-rose-500/15 text-rose-200'
    case 'slate':
    default:
      return 'bg-slate-500/15 text-slate-200'
  }
}

function getHealthTone(status?: GeminiHealthStatus): Tone {
  switch (status) {
    case 'healthy':
    case 'degraded':
      return 'emerald'
    case 'rate_limited':
      return 'amber'
    case 'invalid':
    case 'expired':
    case 'unsupported':
      return 'rose'
    case 'missing':
      return 'slate'
    default:
      return 'amber'
  }
}

function getHealthLabel(status?: GeminiHealthStatus) {
  switch (status) {
    case 'healthy':
      return 'Healthy'
    case 'degraded':
      return 'Fallback active'
    case 'rate_limited':
      return 'Rate limited'
    case 'invalid':
      return 'Invalid'
    case 'expired':
      return 'Expired'
    case 'unsupported':
      return 'Unsupported'
    case 'missing':
      return 'Missing'
    default:
      return 'Checking'
  }
}

function getModelLabel(status?: GeminiModelStatus) {
  switch (status) {
    case 'primary':
      return 'Primary'
    case 'fallback':
      return 'Fallback'
    case 'unavailable':
      return 'Unavailable'
    default:
      return 'Checking'
  }
}

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [apiKey, setApiKey] = useState('')
  const [keyError, setKeyError] = useState<string | null>(null)

  const statusQuery = useQuery({
    queryKey: ['byok-status'],
    queryFn: getByokStatus,
  })

  useEffect(() => {
    if (!statusQuery.data?.has_api_key) {
      return
    }
    setApiKey('')
  }, [statusQuery.data?.has_api_key])

  const saveMutation = useMutation({
    mutationFn: saveApiKey,
    onSuccess: async () => {
      setApiKey('')
      setKeyError(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['byok-status'] }),
        queryClient.invalidateQueries({ queryKey: ['query-history'] }),
      ])
    },
  })

  const deleteMutation = useMutation({
    mutationFn: removeApiKey,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['byok-status'] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: updateByokSettings,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['byok-status'] })
    },
  })

  const canEnableByok = Boolean(
    statusQuery.data?.has_api_key &&
      (statusQuery.data?.status === 'healthy' || statusQuery.data?.status === 'degraded'),
  )

  const statusCards = useMemo(
    () => [
      {
        label: 'BYOK enabled',
        value: statusQuery.data?.byok_enabled ? 'Yes' : 'No',
        tone: statusQuery.data?.byok_enabled ? 'emerald' : 'amber',
      },
      {
        label: 'Key status',
        value: getHealthLabel(statusQuery.data?.status),
        tone: getHealthTone(statusQuery.data?.status),
      },
      {
        label: 'Routing',
        value: getModelLabel(statusQuery.data?.model_status),
        tone:
          statusQuery.data?.model_status === 'primary'
            ? 'emerald'
            : statusQuery.data?.model_status === 'fallback'
              ? 'amber'
              : statusQuery.data?.model_status === 'unavailable'
                ? 'rose'
                : 'slate',
      },
      {
        label: 'Active model',
        value: statusQuery.data?.active_model ?? 'None',
        tone: statusQuery.data?.active_model ? 'emerald' : 'slate',
      },
    ],
    [
      statusQuery.data?.byok_enabled,
      statusQuery.data?.status,
      statusQuery.data?.model_status,
      statusQuery.data?.active_model,
    ],
  )

  const handleSaveKey = async () => {
    if (!keyPattern.test(apiKey.trim())) {
      setKeyError('Gemini keys must start with AIza and be 35-45 characters long.')
      return
    }

    setKeyError(null)

    try {
      await saveMutation.mutateAsync({ api_key: apiKey.trim() })
    } catch (error) {
      setKeyError(getApiErrorMessage(error))
    }
  }

  const healthTone = getHealthTone(statusQuery.data?.status)
  const saveTone = saveMutation.data ? getHealthTone(saveMutation.data.status) : 'amber'

  return (
    <div className="space-y-6">
      {statusQuery.isError && (
        <div className="rounded-[2rem] border border-rose-500/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
          Unable to load BYOK status. {getApiErrorMessage(statusQuery.error)}
        </div>
      )}

      <section className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">Settings</p>
            <h1 className="mt-2 text-3xl font-semibold text-on-surface">Manage BYOK and API keys</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-on-surface-variant">
              Use your own Gemini key when you want private operator control. The backend stores the
              key encrypted, probes model availability, and automatically falls back to the first
              supported Gemini model in your chain.
            </p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {statusCards.map((card) => (
              <div
                key={card.label}
                className="rounded-3xl border border-outline-variant/15 bg-surface-container-low px-5 py-5"
              >
                <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                  {card.label}
                </p>
                <p className={cn('mt-3 text-3xl font-semibold', toneClass(card.tone as Tone))}>
                  {card.value}
                </p>
              </div>
            ))}
          </div>

          <div className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                  Connection health
                </p>
                <h2 className="mt-2 text-xl font-semibold text-on-surface">
                  {getHealthLabel(statusQuery.data?.status)}
                </h2>
              </div>
              <div
                className={cn(
                  'rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em]',
                  badgeClass(healthTone),
                )}
              >
                {statusQuery.data?.status ?? 'checking'}
              </div>
            </div>

            <p className="mt-4 text-sm leading-6 text-on-surface-variant">
              {statusQuery.data?.message ??
                'Saving a Gemini key runs a live capability check so the app can prefer the best available model.'}
            </p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-low px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-on-surface-variant">
                  Fallback order
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {statusQuery.data?.fallback_models?.length ? (
                    statusQuery.data.fallback_models.map((model) => (
                      <span
                        key={model}
                        className="rounded-full border border-outline-variant/15 bg-surface-container-high px-3 py-1 text-xs text-on-surface"
                      >
                        {model}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-on-surface-variant">
                      No fallback models configured.
                    </span>
                  )}
                </div>
              </div>

              <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-low px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-on-surface-variant">
                  Available now
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {statusQuery.data?.available_models?.length ? (
                    statusQuery.data.available_models.map((model) => (
                      <span
                        key={model}
                        className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200"
                      >
                        {model}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-on-surface-variant">
                      {statusQuery.data?.status === 'healthy' || statusQuery.data?.status === 'degraded'
                        ? statusQuery.data.active_model
                        : 'No models are currently reachable.'}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {statusQuery.data?.checked_at && (
              <p className="mt-4 text-xs uppercase tracking-[0.22em] text-on-surface-variant">
                Last checked {new Date(statusQuery.data.checked_at).toLocaleString()}
              </p>
            )}
          </div>

          <div className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                  Gemini key
                </p>
                <h2 className="text-xl font-semibold text-on-surface">Store or update your API key</h2>
              </div>
              <KeyRound className="h-5 w-5 text-primary" />
            </div>

            <div className="mt-5 space-y-4">
              <label className="block space-y-2">
                <span className="text-sm font-medium text-on-surface">API key</span>
                <input
                  className="w-full rounded-2xl border border-outline-variant/15 bg-surface-container px-4 py-3 text-sm text-on-surface outline-none ring-0 transition placeholder:text-on-surface-variant focus:border-primary/40"
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="AIza..."
                  type="password"
                  value={apiKey}
                />
              </label>

              {keyError && (
                <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                  {keyError}
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <button
                  className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-primary to-primary-container px-5 py-3 text-sm font-semibold text-on-primary transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={saveMutation.isPending}
                  onClick={() => void handleSaveKey()}
                  type="button"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Save key
                </button>
                <button
                  className="inline-flex items-center gap-2 rounded-2xl border border-outline-variant/15 bg-surface-container-low px-5 py-3 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={deleteMutation.isPending}
                  onClick={() => void deleteMutation.mutateAsync()}
                  type="button"
                >
                  <Trash2 className="h-4 w-4" />
                  Remove key
                </button>
              </div>

              {saveMutation.data?.message && (
                <div
                  className={cn(
                    'rounded-2xl border px-4 py-3 text-sm',
                    saveTone === 'emerald' && 'border-emerald-500/20 bg-emerald-500/10 text-emerald-100',
                    saveTone === 'amber' && 'border-amber-500/20 bg-amber-500/10 text-amber-100',
                    saveTone === 'rose' && 'border-rose-500/20 bg-rose-500/10 text-rose-100',
                    saveTone === 'slate' && 'border-slate-500/20 bg-slate-500/10 text-slate-100',
                  )}
                >
                  <p className="font-medium">
                    {getHealthLabel(saveMutation.data.status)} · {getModelLabel(saveMutation.data.model_status)}
                  </p>
                  <p className="mt-1 leading-6">{saveMutation.data.message}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">BYOK toggle</p>
            <h2 className="mt-2 text-xl font-semibold text-on-surface">Use your saved key</h2>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              Enabling BYOK tells the backend to prefer your key for LLM requests, but only when the
              key is healthy or can fall back cleanly to another supported Gemini model.
            </p>

            <div className="mt-5 flex items-center justify-between rounded-3xl border border-outline-variant/15 bg-surface-container-low px-5 py-4">
              <div>
                <p className="font-medium text-on-surface">Enable BYOK</p>
                <p className="text-sm text-on-surface-variant">
                  {canEnableByok
                    ? 'The saved key is usable and BYOK can route traffic to it.'
                    : 'Save a healthy Gemini key first to enable the toggle.'}
                </p>
              </div>
              <button
                className={cn(
                  'relative h-8 w-14 rounded-full transition',
                  statusQuery.data?.byok_enabled ? 'bg-primary' : 'bg-surface-container-high',
                )}
                disabled={!canEnableByok || toggleMutation.isPending}
                onClick={() =>
                  void toggleMutation.mutateAsync({
                    enabled: !statusQuery.data?.byok_enabled,
                  })
                }
                type="button"
              >
                <span
                  className={cn(
                    'absolute top-1 h-6 w-6 rounded-full bg-white transition',
                    statusQuery.data?.byok_enabled ? 'left-7' : 'left-1',
                  )}
                />
              </button>
            </div>
          </div>

          <div className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">Status</p>
            <p className="mt-2 text-lg font-semibold text-on-surface">
              {statusQuery.data?.email ?? 'Loading'}
            </p>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              Your key never leaves the backend in plain text. The UI shows whether it is valid,
              which model is active, and when the last probe completed.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
