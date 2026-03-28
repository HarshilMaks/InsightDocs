import { ArrowUpRight, Crop, FileSearch, Sparkles } from 'lucide-react'
import type { DocumentResponse, SourceReference } from '@/types'
import { cn } from '@/lib/utils'
import { formatScore, truncateText } from '@/lib/format'

interface CitationsPanelProps {
  sources: SourceReference[]
  document?: DocumentResponse | null
  selectedSourceId?: string | null
  onSelectSource?: (source: SourceReference) => void
}

export function CitationsPanel({
  sources,
  document,
  selectedSourceId,
  onSelectSource,
}: CitationsPanelProps) {
  const selectedSource = sources.find((source) => source.chunk_id === selectedSourceId) ?? sources[0]

  return (
    <aside className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 shadow-xl shadow-black/10">
      <div className="border-b border-outline-variant/10 px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">Citations</p>
            <p className="text-sm font-semibold text-on-surface">
              {document ? document.filename : 'Latest answer sources'}
            </p>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <FileSearch className="h-5 w-5" />
          </div>
        </div>
      </div>

      <div className="space-y-4 px-4 py-4">
        {!selectedSource ? (
          <div className="rounded-3xl border border-dashed border-outline-variant/15 bg-surface-container-low px-5 py-8 text-sm text-on-surface-variant">
            Ask a question to see citation-backed passages and exact source metadata here.
          </div>
        ) : (
          <div className="rounded-3xl border border-outline-variant/15 bg-surface-container px-5 py-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-[0.24em] text-on-surface-variant">
                  Selected source
                </p>
                <p className="mt-2 text-sm font-semibold text-on-surface">
                  {selectedSource.citation_label}
                </p>
              </div>
              <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-300">
                {formatScore(selectedSource.similarity_score)}
              </span>
            </div>

            <p className="mt-4 text-sm leading-6 text-on-surface-variant">
              {truncateText(selectedSource.content_preview, 260)}
            </p>

            <div className="mt-4 flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.22em] text-on-surface-variant">
              <span className="rounded-full border border-outline-variant/15 bg-surface-container-high px-3 py-1">
                {selectedSource.document_name}
              </span>
              {selectedSource.page_number != null && (
                <span className="rounded-full border border-outline-variant/15 bg-surface-container-high px-3 py-1">
                  Page {selectedSource.page_number}
                </span>
              )}
              <span className="rounded-full border border-outline-variant/15 bg-surface-container-high px-3 py-1">
                Chunk {selectedSource.chunk_index}
              </span>
            </div>

            {selectedSource.bbox && (
              <div className="mt-4 rounded-2xl border border-outline-variant/15 bg-surface-container-low px-4 py-3 text-xs text-on-surface-variant">
                <div className="mb-2 flex items-center gap-2 uppercase tracking-[0.22em]">
                  <Crop className="h-3.5 w-3.5 text-primary" />
                  Spatial citation
                </div>
                <p>
                  x1 {selectedSource.bbox.x1.toFixed(1)} · y1 {selectedSource.bbox.y1.toFixed(1)} ·
                  x2 {selectedSource.bbox.x2.toFixed(1)} · y2 {selectedSource.bbox.y2.toFixed(1)}
                </p>
              </div>
            )}
          </div>
        )}

        <div className="space-y-2">
          <div className="flex items-center justify-between px-1">
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
              Source list
            </p>
            <Sparkles className="h-4 w-4 text-primary" />
          </div>

          {sources.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-outline-variant/15 bg-surface-container-low px-5 py-8 text-sm text-on-surface-variant">
              No citations yet.
            </div>
          ) : (
            <div className="space-y-2">
              {sources.map((source) => (
                <button
                  key={source.chunk_id}
                  className={cn(
                    'w-full rounded-3xl border p-4 text-left transition',
                    selectedSourceId === source.chunk_id
                      ? 'border-primary/30 bg-primary/10'
                      : 'border-outline-variant/15 bg-surface-container-low hover:border-outline-variant/25 hover:bg-surface-container',
                  )}
                  onClick={() => onSelectSource?.(source)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-on-surface">{source.citation_label}</p>
                      <p className="mt-1 text-xs text-on-surface-variant">
                        {source.document_name}
                        {source.page_number != null ? ` · Page ${source.page_number}` : ''}
                      </p>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-on-surface-variant" />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                    {truncateText(source.content_preview, 140)}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}
