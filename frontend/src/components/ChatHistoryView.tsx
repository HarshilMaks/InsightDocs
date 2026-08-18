import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, Loader2 } from 'lucide-react'
import { getQueryHistory } from '@/lib/api'

export const ChatHistoryView: React.FC = () => {
  const navigate = useNavigate()

  const historyQuery = useQuery({
    queryKey: ['query-history'],
    queryFn: () => getQueryHistory(),
  })

  const queries = historyQuery.data?.queries ?? []

  return (
    <div className="flex-1 overflow-y-auto px-6 pb-6 pt-4">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h2 className="text-4xl font-bold text-white tracking-tight" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Chat History
          </h2>
          <p className="text-base text-zinc-400 mt-2">Your past questions and AI-generated answers.</p>
        </div>

        {historyQuery.isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-[#ffcc00] animate-spin" />
          </div>
        ) : queries.length === 0 ? (
          <div className="glass-panel border border-zinc-800 p-12 text-center">
            <MessageSquare className="w-10 h-10 text-zinc-600 mx-auto mb-4" />
            <p className="text-zinc-400">No queries yet. Open a document and ask a question.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {queries.map((q) => (
              <div
                key={q.id}
                className="glass-panel border border-zinc-800 p-4 hover:border-[#ffcc00]/30 transition-colors cursor-pointer group"
                onClick={() => {
                  // Navigate to the document if we can infer it from context
                  // For now just show the history item
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-white group-hover:text-[#ffcc00] transition-colors truncate">{q.query}</p>
                    {q.response && (
                      <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{q.response}</p>
                    )}
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500 shrink-0">
                    {new Date(q.created_at).toLocaleDateString()}
                  </span>
                </div>
                {q.response_time && (
                  <p className="text-[10px] font-mono text-zinc-600 mt-2">{q.response_time.toFixed(1)}s response time</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
