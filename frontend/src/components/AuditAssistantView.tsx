import { useState, useRef, useEffect, useMemo } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Send, FileText, CheckCircle2, AlertTriangle, Loader2, ExternalLink } from 'lucide-react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import {
  getDocument,
  getDocumentFileUrl,
  getQueryHistory,
  getTaskStatus,
  sendQuery,
  getApiErrorMessage,
  type QueryResponse,
  type SourceReference,
  type ClaimVerification,
} from '@/lib/api'

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

export const AuditAssistantView: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [inputQuery, setInputQuery] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Array<{ id: string; role: 'user' | 'assistant'; content: string; sources?: SourceReference[]; claims?: ClaimVerification[] | null }>>([])
  const [selectedSource, setSelectedSource] = useState<SourceReference | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [numPages, setNumPages] = useState<number | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const pdfContainerRef = useRef<HTMLDivElement>(null)

  // Queries
  const docQuery = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => getDocument(documentId!),
    enabled: !!documentId,
  })

  const taskId = searchParams.get('task')
  const taskQuery = useQuery({
    queryKey: ['task-status', taskId],
    queryFn: () => getTaskStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'processing' ? 4000 : false
    },
  })

  const isPdf = docQuery.data?.file_type?.toLowerCase() === '.pdf'
  const isReady = docQuery.data?.status === 'completed'

  const fileUrlQuery = useQuery({
    queryKey: ['document-file-url', documentId],
    queryFn: () => getDocumentFileUrl(documentId!),
    enabled: !!documentId && isPdf && isReady,
    staleTime: 8 * 60 * 1000,
  })

  // Send query mutation
  const queryMutation = useMutation({
    mutationFn: (text: string) => sendQuery({
      query: text,
      top_k: 5,
      conversation_id: conversationId || undefined,
      document_id: documentId,
    }),
    onSuccess: (response) => {
      setConversationId(response.conversation_id)
      setMessages((prev) => [
        ...prev,
        {
          id: response.query_id,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          claims: response.claim_verifications,
        },
      ])
      if (response.sources.length > 0) {
        setSelectedSource(response.sources[0])
        if (response.sources[0].page_number) {
          setCurrentPage(response.sources[0].page_number)
        }
      }
    },
  })

  const handleSend = () => {
    if (!inputQuery.trim() || queryMutation.isPending) return
    const text = inputQuery.trim()
    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: 'user', content: text }])
    setInputQuery('')
    queryMutation.mutate(text)
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, queryMutation.isPending])

  // Jump to citation page
  const handleCitationClick = (source: SourceReference) => {
    setSelectedSource(source)
    if (source.page_number) setCurrentPage(source.page_number)
  }

  // Bbox highlight style
  const highlightStyle = useMemo(() => {
    if (!selectedSource?.bbox || !pdfContainerRef.current) return null
    const bbox = selectedSource.bbox
    // Will be scaled after PDF renders
    return { x1: bbox.x1, y1: bbox.y1, x2: bbox.x2, y2: bbox.y2 }
  }, [selectedSource])

  const taskProgress = taskQuery.data?.progress ?? 0
  const doc = docQuery.data

  return (
    <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
      {/* Left: Chat + Claims */}
      <div className="flex-1 flex flex-col border-r border-zinc-800 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800 bg-zinc-900/40 backdrop-blur-sm">
          <button onClick={() => navigate('/')} className="p-2 hover:bg-zinc-800 transition-colors text-zinc-400 hover:text-white">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <FileText className="w-4 h-4 text-[#ffcc00]" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-white truncate">{doc?.filename || 'Loading...'}</p>
            <p className="text-[11px] text-zinc-500 font-mono">{doc?.status?.toUpperCase() || ''}</p>
          </div>
        </div>

        {/* Processing banner */}
        {!isReady && taskId && (
          <div className="px-4 py-2 bg-yellow-500/5 border-b border-yellow-500/20">
            <div className="flex justify-between text-xs text-yellow-400">
              <span>Processing...</span>
              <span>{Math.round(taskProgress * 100)}%</span>
            </div>
            <div className="mt-1 h-1 bg-yellow-500/20 overflow-hidden">
              <div className="h-full bg-[#ffcc00] transition-all" style={{ width: `${taskProgress * 100}%` }} />
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-16">
              <p className="text-2xl font-bold text-white mb-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>Ask about this document</p>
              <p className="text-zinc-400 text-sm max-w-md mx-auto">
                Every answer will show the exact page and paragraph it came from, with per-claim verification.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`${msg.role === 'user' ? 'ml-auto max-w-[80%]' : 'max-w-[90%]'}`}>
              <div className={`px-4 py-3 ${msg.role === 'user' ? 'bg-[#ffcc00]/10 border border-[#ffcc00]/30' : 'bg-zinc-900 border border-zinc-800'}`}>
                <p className="text-sm text-white whitespace-pre-wrap">{msg.content}</p>

                {/* Claim verifications */}
                {msg.claims && msg.claims.length > 0 && (
                  <div className="mt-3 space-y-2 border-t border-zinc-700 pt-3">
                    <p className="text-[11px] font-mono uppercase text-zinc-500 tracking-wider">Claim Verification</p>
                    {msg.claims.map((claim, i) => (
                      <div key={i} className={`flex items-start gap-2 px-3 py-2 text-xs ${
                        claim.status === 'supported' ? 'bg-emerald-500/5 border border-emerald-500/20' : 'bg-red-500/5 border border-red-500/20'
                      }`}>
                        {claim.status === 'supported' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        ) : (
                          <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className={claim.status === 'supported' ? 'text-emerald-300' : 'text-red-300'}>{claim.claim}</p>
                          {claim.reason && <p className="text-zinc-500 mt-0.5">{claim.reason}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5 border-t border-zinc-700 pt-3">
                    {msg.sources.map((src) => (
                      <button
                        key={src.chunk_id}
                        onClick={() => handleCitationClick(src)}
                        className={`text-[10px] font-mono px-2 py-1 border transition-colors cursor-pointer ${
                          selectedSource?.chunk_id === src.chunk_id
                            ? 'bg-[#ffcc00]/20 border-[#ffcc00] text-[#ffcc00]'
                            : 'border-zinc-700 text-zinc-400 hover:border-[#ffcc00]/50 hover:text-[#ffcc00]'
                        }`}
                      >
                        {src.citation_label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {queryMutation.isPending && (
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <Loader2 className="w-4 h-4 animate-spin text-[#ffcc00]" />
              Analyzing document...
            </div>
          )}

          {queryMutation.isError && (
            <div className="bg-red-900/20 border border-red-500/30 px-4 py-2 text-sm text-red-300">
              {getApiErrorMessage(queryMutation.error)}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Composer */}
        <div className="px-4 py-3 border-t border-zinc-800 bg-zinc-900/40">
          <div className="flex gap-2">
            <input
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
              placeholder="Ask about this document..."
              className="flex-1 bg-zinc-950 border-2 border-zinc-700 text-white px-4 py-2.5 text-sm focus:border-[#ffcc00] focus:ring-0 placeholder-zinc-500 transition-colors"
              disabled={!isReady}
            />
            <button
              onClick={handleSend}
              disabled={!inputQuery.trim() || queryMutation.isPending || !isReady}
              className="px-4 py-2.5 bg-[#ffcc00] text-black font-bold border-2 border-black hover:bg-[#e6b800] disabled:opacity-40 transition-all cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Right: PDF + Source Detail */}
      <div className="flex-1 flex flex-col bg-zinc-950 min-w-0 hidden lg:flex">
        {/* Source detail header */}
        {selectedSource && (
          <div className="px-4 py-3 border-b border-zinc-800 bg-zinc-900/40">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] font-mono uppercase text-zinc-500 tracking-wider">Source</p>
                <p className="text-sm font-semibold text-white">{selectedSource.citation_label}</p>
              </div>
              <span className="text-[11px] font-mono text-[#ffcc00] bg-[#ffcc00]/10 px-2 py-1 border border-[#ffcc00]/30">
                {(selectedSource.similarity_score * 100).toFixed(0)}% match
              </span>
            </div>
            {selectedSource.section_title && (
              <p className="text-xs text-zinc-400 mt-1">Section: {selectedSource.section_title}</p>
            )}
            {selectedSource.content_preview && (
              <p className="text-xs text-zinc-500 mt-2 line-clamp-3 italic">{selectedSource.content_preview}</p>
            )}
          </div>
        )}

        {/* PDF Viewer */}
        <div ref={pdfContainerRef} className="flex-1 overflow-auto p-4">
          {fileUrlQuery.data?.url ? (
            <div className="relative">
              <Document
                file={fileUrlQuery.data.url}
                onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                loading={<div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 text-[#ffcc00] animate-spin" /></div>}
              >
                <div className="relative inline-block">
                  <Page pageNumber={currentPage} width={600} />
                  {/* Bbox highlight overlay */}
                  {highlightStyle && selectedSource?.page_number === currentPage && (
                    <div
                      className="absolute border-2 border-[#ffcc00] bg-[#ffcc00]/15 pointer-events-none transition-all"
                      style={{
                        left: `${highlightStyle.x1 * (600 / 612)}px`,
                        top: `${highlightStyle.y1 * (600 / 612)}px`,
                        width: `${(highlightStyle.x2 - highlightStyle.x1) * (600 / 612)}px`,
                        height: `${(highlightStyle.y2 - highlightStyle.y1) * (600 / 612)}px`,
                      }}
                    />
                  )}
                </div>
              </Document>

              {/* Page navigation */}
              {numPages && (
                <div className="flex items-center justify-center gap-3 mt-3 text-xs text-zinc-400 font-mono">
                  <button onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage <= 1} className="px-2 py-1 border border-zinc-700 hover:border-[#ffcc00] disabled:opacity-30 cursor-pointer">←</button>
                  <span>Page {currentPage} / {numPages}</span>
                  <button onClick={() => setCurrentPage(Math.min(numPages, currentPage + 1))} disabled={currentPage >= numPages} className="px-2 py-1 border border-zinc-700 hover:border-[#ffcc00] disabled:opacity-30 cursor-pointer">→</button>
                </div>
              )}
            </div>
          ) : isPdf && !isReady ? (
            <div className="flex items-center justify-center h-full text-sm text-zinc-500">
              PDF available after processing completes.
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-zinc-500">
              {isPdf ? <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading PDF...</> : 'Ask a question to see cited evidence here.'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
