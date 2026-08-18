import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Key, CheckCircle2, AlertCircle, Eye, EyeOff, Loader2, ShieldCheck } from 'lucide-react'
import { getByokStatus, saveApiKey, removeApiKey, updateByokSettings, getApiErrorMessage } from '@/lib/api'

export const ByokConfigView: React.FC = () => {
  const queryClient = useQueryClient()
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const statusQuery = useQuery({
    queryKey: ['byok-status'],
    queryFn: getByokStatus,
  })

  const saveMutation = useMutation({
    mutationFn: (key: string) => saveApiKey(key),
    onSuccess: (data) => {
      setApiKeyInput('')
      setSuccess(`Key saved. Model: ${data.active_model || 'checking...'}`)
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['byok-status'] })
      setTimeout(() => setSuccess(null), 4000)
    },
    onError: (err) => setError(getApiErrorMessage(err)),
  })

  const removeMutation = useMutation({
    mutationFn: removeApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['byok-status'] })
      setSuccess('API key removed.')
      setTimeout(() => setSuccess(null), 3000)
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (enabled: boolean) => updateByokSettings(enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['byok-status'] }),
  })

  const status = statusQuery.data
  const isHealthy = status?.status === 'healthy' || status?.status === 'degraded'

  return (
    <div className="flex-1 overflow-y-auto px-6 pb-6 pt-4">
      <div className="max-w-3xl mx-auto space-y-8">
        <div>
          <h2 className="text-4xl font-bold text-white tracking-tight" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            BYOK Configuration
          </h2>
          <p className="text-base text-zinc-400 mt-2">
            Bring your own Gemini API key. Encrypted at rest, never stored in plain text.
          </p>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'BYOK', value: status?.byok_enabled ? 'Enabled' : 'Disabled', color: status?.byok_enabled ? 'text-emerald-400' : 'text-zinc-400' },
            { label: 'Key Status', value: status?.status || 'Unknown', color: isHealthy ? 'text-emerald-400' : 'text-yellow-400' },
            { label: 'Model', value: status?.active_model || 'None', color: status?.active_model ? 'text-[#ffcc00]' : 'text-zinc-500' },
            { label: 'Routing', value: status?.model_status || 'Unknown', color: 'text-zinc-300' },
          ].map((card) => (
            <div key={card.label} className="glass-panel border border-zinc-800 p-4">
              <p className="text-[11px] font-mono uppercase text-zinc-500 tracking-wider">{card.label}</p>
              <p className={`text-lg font-bold mt-1 truncate ${card.color}`} style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{card.value}</p>
            </div>
          ))}
        </div>

        {/* API Key Input */}
        <div className="glass-panel border border-zinc-800 p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Key className="w-5 h-5 text-[#ffcc00]" />
            <h3 className="font-bold text-white text-lg" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>Gemini API Key</h3>
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="AIza..."
                className="w-full bg-zinc-950 border-2 border-zinc-700 text-white px-4 py-2.5 pr-10 text-sm focus:border-[#ffcc00] focus:ring-0 placeholder-zinc-600 font-mono"
              />
              <button onClick={() => setShowKey(!showKey)} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white cursor-pointer">
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <button
              onClick={() => { setError(null); saveMutation.mutate(apiKeyInput) }}
              disabled={!apiKeyInput.trim() || saveMutation.isPending}
              className="px-5 py-2.5 bg-[#ffcc00] text-black font-bold border-2 border-black hover:bg-[#e6b800] disabled:opacity-40 transition-all text-sm cursor-pointer"
            >
              {saveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save'}
            </button>
          </div>

          {status?.has_api_key && (
            <button
              onClick={() => removeMutation.mutate()}
              className="text-xs text-red-400 hover:text-red-300 underline cursor-pointer"
            >
              Remove saved key
            </button>
          )}

          {error && <p className="text-sm text-red-400 border border-red-500/30 bg-red-500/10 px-3 py-2">{error}</p>}
          {success && <p className="text-sm text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 flex items-center gap-2"><CheckCircle2 className="w-4 h-4" />{success}</p>}
        </div>

        {/* Toggle */}
        <div className="glass-panel border border-zinc-800 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-[#ffcc00]" />
              <div>
                <p className="font-bold text-white">Enable BYOK routing</p>
                <p className="text-xs text-zinc-400 mt-0.5">Use your saved key for all LLM requests</p>
              </div>
            </div>
            <button
              onClick={() => toggleMutation.mutate(!status?.byok_enabled)}
              disabled={!status?.has_api_key || !isHealthy}
              className={`w-12 h-6 rounded-full relative transition-colors cursor-pointer disabled:opacity-40 ${status?.byok_enabled ? 'bg-[#ffcc00]' : 'bg-zinc-700'}`}
            >
              <span className={`absolute top-1 w-4 h-4 rounded-full bg-black transition-all ${status?.byok_enabled ? 'left-7' : 'left-1'}`} />
            </button>
          </div>
        </div>

        {/* Available models */}
        {status?.available_models && status.available_models.length > 0 && (
          <div className="glass-panel border border-zinc-800 p-6">
            <p className="text-[11px] font-mono uppercase text-zinc-500 tracking-wider mb-3">Available Models</p>
            <div className="flex flex-wrap gap-2">
              {status.available_models.map((model) => (
                <span key={model} className="text-xs font-mono px-3 py-1.5 border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                  {model}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
