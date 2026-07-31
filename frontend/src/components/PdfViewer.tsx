import { useEffect, useMemo, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import type { BoundingBox } from '@/types'
import { cn } from '@/lib/utils'

// The PDF.js worker must be configured once, in the same module where
// react-pdf components are rendered (setting it elsewhere can be silently
// overwritten due to module execution order — see react-pdf's docs).
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface PdfViewerProps {
  /** Presigned (or otherwise directly fetchable) URL to the source PDF. */
  fileUrl: string
  /** 1-indexed page to display and to jump to when it changes. */
  pageNumber?: number | null
  /**
   * Bounding box to highlight on the current page, in PDF point-space
   * (the same coordinate system PyMuPDF's page.get_text("dict") reports:
   * origin at the top-left of the page, in points). When present, an
   * overlay is drawn scaled to the rendered page size.
   */
  highlightBbox?: BoundingBox | null
  className?: string
}

/**
 * Renders a PDF page with an optional highlighted region, used to give the
 * user a precise, visual answer to "where did this citation come from."
 *
 * Coordinate handling: PyMuPDF reports bounding boxes in PDF point-space
 * (72 points = 1 inch, origin top-left of the *unrotated* page at its
 * native size). react-pdf renders the page at a caller-chosen pixel width
 * and exposes that rendered size via onLoadSuccess, so the highlight is
 * scaled by (renderedWidth / nativePageWidth) rather than assumed to match
 * 1:1 — those two coordinate spaces are not the same unless the page is
 * rendered at exactly 72 DPI.
 */
export function PdfViewer({ fileUrl, pageNumber, highlightBbox, className }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null)
  const [currentPage, setCurrentPage] = useState(pageNumber ?? 1)
  const [nativePageSize, setNativePageSize] = useState<{ width: number; height: number } | null>(null)
  const [renderedPageSize, setRenderedPageSize] = useState<{ width: number; height: number } | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (pageNumber && pageNumber !== currentPage) {
      setCurrentPage(pageNumber)
    }
    // Only react to explicit page changes requested by the caller (e.g. a
    // citation click), not to the user's own manual navigation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageNumber])

  useEffect(() => {
    if (highlightBbox && containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [highlightBbox, currentPage])

  const highlightStyle = useMemo(() => {
    if (!highlightBbox || !nativePageSize || !renderedPageSize) {
      return null
    }
    const scaleX = renderedPageSize.width / nativePageSize.width
    const scaleY = renderedPageSize.height / nativePageSize.height
    return {
      left: highlightBbox.x1 * scaleX,
      top: highlightBbox.y1 * scaleY,
      width: Math.max(2, (highlightBbox.x2 - highlightBbox.x1) * scaleX),
      height: Math.max(2, (highlightBbox.y2 - highlightBbox.y1) * scaleY),
    }
  }, [highlightBbox, nativePageSize, renderedPageSize])

  const goToPage = (delta: number) => {
    if (!numPages) return
    setCurrentPage((p) => Math.min(numPages, Math.max(1, p + delta)))
  }

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.22em] text-on-surface-variant">
        <div className="flex items-center gap-2">
          <button
            className="rounded-full border border-outline-variant/15 bg-surface-container p-2 transition hover:bg-surface-container-high disabled:opacity-40"
            disabled={currentPage <= 1}
            onClick={() => goToPage(-1)}
            type="button"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span>
            Page {currentPage}
            {numPages ? ` of ${numPages}` : ''}
          </span>
          <button
            className="rounded-full border border-outline-variant/15 bg-surface-container p-2 transition hover:bg-surface-container-high disabled:opacity-40"
            disabled={!numPages || currentPage >= numPages}
            onClick={() => goToPage(1)}
            type="button"
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="relative overflow-auto rounded-2xl border border-outline-variant/15 bg-surface-container-low p-4"
      >
        {loadError ? (
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-6 text-sm text-rose-100">
            Unable to load this document for preview. {loadError}
          </div>
        ) : (
          <Document
            file={fileUrl}
            loading={
              <div className="flex items-center justify-center gap-2 py-12 text-sm text-on-surface-variant">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading document preview...
              </div>
            }
            onLoadError={(error) => setLoadError(error.message)}
            onLoadSuccess={({ numPages: total }) => setNumPages(total)}
          >
            <div className="relative inline-block">
              <Page
                pageNumber={currentPage}
                width={Math.min(760, containerRef.current?.clientWidth ?? 760)}
                onLoadSuccess={(page) => {
                  setNativePageSize({ width: page.originalWidth, height: page.originalHeight })
                  setRenderedPageSize({ width: page.width, height: page.height })
                }}
                onRenderError={(error) => setLoadError(error.message)}
              />
              {highlightStyle && (
                <div
                  className="pointer-events-none absolute rounded-sm border-2 border-amber-400 bg-amber-300/25 shadow-[0_0_0_2px_rgba(251,191,36,0.35)] transition-all"
                  style={{
                    left: `${highlightStyle.left}px`,
                    top: `${highlightStyle.top}px`,
                    width: `${highlightStyle.width}px`,
                    height: `${highlightStyle.height}px`,
                  }}
                />
              )}
            </div>
          </Document>
        )}
      </div>
    </div>
  )
}
