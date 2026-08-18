import { FileText, Plus, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/auth-context'
import { useWorkspace } from '@/context/workspace-context'
import { formatBytes, formatStatus } from '@/lib/format'
import type { DocumentResponse } from '@/types'
import { cn } from '@/lib/utils'

interface DocumentSidebarProps {
  documents: DocumentResponse[]
  isLoading: boolean
  onUploadClick: () => void
}

const statusDot: Record<string, string> = {
  pending: 'bg-amber-400',
  processing: 'bg-sky-400',
  completed: 'bg-emerald-400',
  failed: 'bg-rose-400',
}

export function DocumentSidebar({ documents, isLoading, onUploadClick }: DocumentSidebarProps) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { activeDocument, sidebarCollapsed } = useWorkspace()

  if (sidebarCollapsed) {
    return null
  }

  return (
    <aside className="flex h-full w-60 flex-col border-r border-white/[0.06] bg-[hsl(227,28%,7%)]">
      {/* Upload button */}
      <div className="p-3">
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white/70 transition hover:border-white/[0.12] hover:bg-white/[0.06] hover:text-white/90"
          onClick={onUploadClick}
        >
          <Plus className="h-4 w-4" />
          Upload document
        </button>
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        <p className="px-2 py-2 text-[11px] font-medium uppercase tracking-wider text-white/30">
          Documents
        </p>

        {isLoading && (
          <div className="space-y-2 px-1">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-white/[0.04]" />
            ))}
          </div>
        )}

        {!isLoading && documents.length === 0 && (
          <div className="px-2 py-6 text-center text-xs text-white/30">
            {isAuthenticated
              ? 'No documents yet. Upload one to get started.'
              : 'Sign in to see your documents.'}
          </div>
        )}

        {!isLoading && documents.length > 0 && (
          <div className="space-y-0.5">
            {documents.map((doc) => (
              <button
                key={doc.id}
                type="button"
                className={cn(
                  'group flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition',
                  activeDocument?.id === doc.id
                    ? 'bg-sky-500/10 text-white/90'
                    : 'text-white/60 hover:bg-white/[0.04] hover:text-white/80',
                )}
                onClick={() => navigate(`/documents/${doc.id}`)}
              >
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-white/30" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm leading-tight">{doc.filename}</p>
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-white/30">
                    <span
                      className={cn('h-1.5 w-1.5 rounded-full', statusDot[doc.status] ?? 'bg-white/30')}
                    />
                    <span>{formatStatus(doc.status)}</span>
                    <span>·</span>
                    <span>{formatBytes(doc.file_size)}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Bottom settings link */}
      {isAuthenticated && (
        <div className="border-t border-white/[0.06] p-2">
          <button
            type="button"
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-white/40 transition hover:bg-white/[0.04] hover:text-white/60"
            onClick={() => navigate('/settings')}
          >
            <Settings className="h-3.5 w-3.5" />
            Settings
          </button>
        </div>
      )}
    </aside>
  )
}
