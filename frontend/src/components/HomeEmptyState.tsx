import { FileText, Sparkles, Upload } from 'lucide-react'

interface HomeEmptyStateProps {
  onUploadClick: () => void
}

export function HomeEmptyState({ onUploadClick }: HomeEmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-lg space-y-8 text-center">
        {/* Icon */}
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-500/10">
          <FileText className="h-6 w-6 text-sky-400" />
        </div>

        {/* Copy */}
        <div className="space-y-3">
          <h1 className="text-2xl font-semibold text-white/90">
            Ask your documents anything
          </h1>
          <p className="mx-auto max-w-md text-sm leading-relaxed text-white/45">
            Upload a PDF, DOCX, or TXT file. Ask questions in plain language.
            Every answer shows the exact page and paragraph it came from.
          </p>
        </div>

        {/* Upload action */}
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-3 text-sm font-medium text-white transition hover:bg-sky-400"
          onClick={onUploadClick}
        >
          <Upload className="h-4 w-4" />
          Upload your first document
        </button>

        {/* Composer hint (disabled preview) */}
        <div className="mx-auto w-full max-w-md">
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3">
            <div className="flex items-center gap-3 text-white/20">
              <Sparkles className="h-4 w-4" />
              <span className="text-sm">Ask anything about your documents...</span>
            </div>
          </div>
          <p className="mt-2 text-[11px] text-white/20">
            Upload a document first, then ask questions here.
          </p>
        </div>
      </div>
    </div>
  )
}
