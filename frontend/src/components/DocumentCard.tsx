import { ArrowRight, FileText, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { DocumentResponse } from '@/types'
import { formatBytes, formatRelativeTime, formatStatus } from '@/lib/format'
import { cn } from '@/lib/utils'

interface DocumentCardProps {
  document: DocumentResponse
  onDelete: (documentId: string) => void
  isDeleting?: boolean
}

const statusClasses: Record<string, string> = {
  pending: 'bg-amber-500/15 text-amber-300',
  processing: 'bg-sky-500/15 text-sky-300',
  completed: 'bg-emerald-500/15 text-emerald-300',
  failed: 'bg-rose-500/15 text-rose-300',
}

export function DocumentCard({ document, onDelete, isDeleting = false }: DocumentCardProps) {
  return (
    <article className="rounded-3xl border border-outline-variant/15 bg-surface-container-low/80 p-5 shadow-lg shadow-black/10 transition hover:-translate-y-0.5 hover:border-outline-variant/25">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-on-surface">{document.filename}</p>
            <p className="mt-1 text-xs text-on-surface-variant">
              {formatBytes(document.file_size)} · {document.file_type.toUpperCase()}
            </p>
          </div>
        </div>

        <span
          className={cn(
            'rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em]',
            statusClasses[document.status] ?? 'bg-surface-container-high text-on-surface-variant',
          )}
        >
          {formatStatus(document.status)}
        </span>
      </div>

      <p className="mt-4 text-sm text-on-surface-variant">
        Uploaded {formatRelativeTime(document.created_at)}
      </p>

      <div className="mt-5 flex items-center gap-2">
        <Link
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-primary to-primary-container px-4 py-3 text-sm font-semibold text-on-primary transition hover:opacity-95"
          to={`/documents/${document.id}`}
        >
          Open workspace
          <ArrowRight className="h-4 w-4" />
        </Link>

        <button
          className="inline-flex items-center justify-center rounded-2xl border border-outline-variant/15 bg-surface-container px-4 py-3 text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isDeleting}
          onClick={() => onDelete(document.id)}
          type="button"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </article>
  )
}
