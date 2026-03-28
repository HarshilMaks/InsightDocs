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

const keyPattern = /^AIza[A-Za-z0-9_-]{31,41}$/

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

  const canEnableByok = Boolean(statusQuery.data?.has_api_key)

  const statusCards = useMemo(
    () => [
      {
        label: 'BYOK enabled',
        value: statusQuery.data?.byok_enabled ? 'Yes' : 'No',
        tone: statusQuery.data?.byok_enabled ? 'emerald' : 'amber',
      },
      {
        label: 'Saved key',
        value: statusQuery.data?.has_api_key ? 'Present' : 'Missing',
        tone: statusQuery.data?.has_api_key ? 'emerald' : 'amber',
      },
    ],
    [statusQuery.data?.byok_enabled, statusQuery.data?.has_api_key],
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
              key encrypted and the toggle can only be enabled when a saved key exists.
            </p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {statusCards.map((card) => (
              <div
                key={card.label}
                className="rounded-3xl border border-outline-variant/15 bg-surface-container-low px-5 py-5"
              >
                <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                  {card.label}
                </p>
                <p
                  className={cn(
                    'mt-3 text-3xl font-semibold',
                    card.tone === 'emerald' ? 'text-emerald-300' : 'text-amber-300',
                  )}
                >
                  {card.value}
                </p>
              </div>
            ))}
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
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">BYOK toggle</p>
            <h2 className="mt-2 text-xl font-semibold text-on-surface">Use your saved key</h2>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              Enabling BYOK tells the backend to prefer your key for LLM requests.
            </p>

            <div className="mt-5 flex items-center justify-between rounded-3xl border border-outline-variant/15 bg-surface-container-low px-5 py-4">
              <div>
                <p className="font-medium text-on-surface">Enable BYOK</p>
                <p className="text-sm text-on-surface-variant">
                  {canEnableByok
                    ? 'A saved key exists and can be used immediately.'
                    : 'Save a Gemini key first to enable the toggle.'}
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
              Your key never leaves the backend in plain text. The UI only shows whether a key is
              saved and whether BYOK is enabled.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
