import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import ReactMarkdown from 'react-markdown'
import { toast } from 'sonner'
import {
  ArrowLeft,
  Send,
  Square,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  KeyRound,
  Loader2,
  ChevronLeft,
  ChevronRight,
  FileText,
  Sparkles,
  PanelRightOpen,
  RefreshCw,
  ClipboardCheck,
  ShieldCheck,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  getDocument,
  getDocumentFileUrl,
  getQueryHistory,
  getTaskStatus,
  sendQuery,
  summarizeDocument,
  generateQuiz,
  generateMindmap,
  getApiErrorMessage,
  isRequestCancelled,
  type SourceReference,
  type ClaimVerification,
  type EvidenceGateSummary,
} from '@/lib/api'

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

const THREAD_KEY = 'insightdocs:thread:'
type Tool = 'ask' | 'summary' | 'quiz' | 'mindmap'

interface ChatTurn {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceReference[]
  claims?: ClaimVerification[] | null
  evidenceGate?: EvidenceGateSummary | null
  /** True only for a newly delivered response whose audit persistence was attempted. */
  auditAttempted?: boolean
}

function gateStatusLabel(status: EvidenceGateSummary['status']) {
  if (status === 'passed') return 'Evidence checks passed'
  if (status === 'failed') return 'Needs evidence review'
  if (status === 'abstained') return 'Answer abstained'
  return 'Evidence check degraded'
}

function gateStatusClass(status: EvidenceGateSummary['status']) {
  if (status === 'passed') return 'border-[color:var(--success)]/30 bg-[color:var(--success)]/5'
  if (status === 'failed') return 'border-destructive/30 bg-destructive/5'
  return 'border-warning/30 bg-warning/5'
}

function AuditUnavailableCard() {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
      <div>
        <p className="font-medium">Evidence Gate audit was unavailable</p>
        <p className="mt-0.5 leading-relaxed text-muted-foreground">
          The answer is shown, but no review record was created. Inspect the retrieved sources directly before relying on it.
        </p>
      </div>
    </div>
  )
}

function isMissingGeminiApiKeyError(error: unknown) {
  return getApiErrorMessage(error).trim().toLowerCase() === 'no gemini api key is configured.'
}

function GeminiKeyRequiredCard({ onConfigure }: { onConfigure: () => void }) {
  return (
    <Card role="alert" className="border-warning/35 bg-warning/5">
      <CardContent className="flex items-start gap-3 p-4">
        <KeyRound className="mt-0.5 size-5 shrink-0 text-warning" />
        <div className="min-w-0 flex-1 space-y-2">
          <div>
            <p className="text-sm font-medium">A Gemini API key is required to answer this question</p>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              This service has no platform Gemini key and your account has no usable key. Add your own key to generate document-grounded answers.
            </p>
          </div>
          <Button size="sm" onClick={onConfigure}>
            <KeyRound className="size-4" />
            Configure API key
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function EvidenceGateRunCard({ gate, onOpenReview }: { gate: EvidenceGateSummary; onOpenReview: () => void }) {
  return (
    <div className={`rounded-lg border p-3 ${gateStatusClass(gate.status)}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
          <div className="min-w-0">
            <p className="text-xs font-medium">{gateStatusLabel(gate.status)}</p>
            <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
              Evidence Gate · {gate.mode} mode · {gate.supported_count} supported, {gate.unsupported_count} not supported, {gate.unverified_count} unverified
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" className="h-7 shrink-0 text-xs" onClick={onOpenReview}>
          <ClipboardCheck className="size-3.5" />
          Review audit
        </Button>
      </div>
    </div>
  )
}

/** Human wording for verification states. "Unsupported" must never read as "false". */
function claimLabel(status: ClaimVerification['status']) {
  if (status === 'supported') return 'Supported'
  if (status === 'unsupported') return 'Not supported by retrieved evidence'
  return 'Verification unavailable'
}

export function AuditAssistantView() {
  const { documentId } = useParams<{ documentId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()

  const [tool, setTool] = useState<Tool>('ask')
  const [showSecondaryTools, setShowSecondaryTools] = useState(false)
  const [draft, setDraft] = useState('')
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [conversationId, setConversationId] = useState<string | null>(
    () => searchParams.get('conversation') ?? window.localStorage.getItem(`${THREAD_KEY}${documentId}`) ?? null,
  )
  const [selectedSource, setSelectedSource] = useState<SourceReference | null>(null)
  const [page, setPage] = useState(1)
  const [numPages, setNumPages] = useState<number | null>(null)
  const [mobilePane, setMobilePane] = useState<'answer' | 'source'>('answer')

  // Measured page geometry, needed to place the bbox overlay correctly.
  // PyMuPDF reports boxes in PDF point space; react-pdf renders at a chosen
  // pixel width, so the overlay must be scaled by rendered/native.
  const [nativeSize, setNativeSize] = useState<{ w: number; h: number } | null>(null)
  const [renderedSize, setRenderedSize] = useState<{ w: number; h: number } | null>(null)
  const [pageWidth, setPageWidth] = useState(560)

  const endRef = useRef<HTMLDivElement>(null)
  const pdfPaneRef = useRef<HTMLDivElement>(null)
  const queryAbortControllerRef = useRef<AbortController | null>(null)

  const docQuery = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => getDocument(documentId!),
    enabled: Boolean(documentId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'pending' || status === 'processing' ? 4000 : false
    },
  })

  const taskId = searchParams.get('task')
  const taskQuery = useQuery({
    queryKey: ['task-status', taskId],
    queryFn: () => getTaskStatus(taskId!),
    enabled: Boolean(taskId),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'processing' ? 4000 : false
    },
  })

  const doc = docQuery.data
  const isPdf = doc?.file_type?.toLowerCase() === '.pdf'
  const isReady = doc?.status === 'completed'
  const workspaceStatus = doc?.status ?? taskQuery.data?.status ?? 'pending'
  const isFailed = workspaceStatus === 'failed'
  const taskProgress = taskQuery.data?.progress ?? 0
  const taskProgressPercent = Math.round(taskProgress * 100)
  const processingTitle = isFailed
    ? 'Document processing failed'
    : workspaceStatus === 'pending'
      ? 'Document is queued for processing'
      : 'Processing document'
  const processingDescription = isFailed
    ? doc?.error_message || 'The document could not be processed. Return to Documents to review it or upload another file.'
    : workspaceStatus === 'pending'
      ? 'Your document is waiting for the processing worker. This page will unlock automatically when it is ready.'
      : 'Extracting text, building citations, and indexing the document. This page will unlock automatically when it is ready.'


  const fileUrlQuery = useQuery({
    queryKey: ['document-file-url', documentId],
    queryFn: () => getDocumentFileUrl(documentId!),
    enabled: Boolean(documentId) && isPdf && isReady,
    staleTime: 8 * 60 * 1000,
  })

  const historyQuery = useQuery({
    queryKey: ['conversation-history', conversationId],
    queryFn: () => getQueryHistory(conversationId),
    enabled: Boolean(conversationId),
  })

  // Seed the transcript from server history once, so a refresh keeps context.
  useEffect(() => {
    if (!historyQuery.data) return
    const restored: ChatTurn[] = []
    for (const item of historyQuery.data.queries) {
      restored.push({ id: `${item.id}-u`, role: 'user', content: item.query })
      if (item.response) restored.push({ id: `${item.id}-a`, role: 'assistant', content: item.response })
    }
    setTurns((current) => (current.length === 0 ? restored : current))
  }, [historyQuery.data])

  useEffect(() => {
    if (conversationId && documentId) {
      window.localStorage.setItem(`${THREAD_KEY}${documentId}`, conversationId)
    }
  }, [conversationId, documentId])

  // Review detail passes a normalized, owner-scoped source in route state so the
  // workspace opens the exact cited page and bbox rather than a blank document view.
  useEffect(() => {
    const handoff = (location.state as { evidenceSource?: SourceReference } | null)?.evidenceSource
    if (!handoff || handoff.document_id !== documentId) return
    setSelectedSource(handoff)
    if (handoff.page_number) setPage(handoff.page_number)
    setMobilePane('source')
  }, [documentId, location.state])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  // Keep the PDF page width in step with its pane so nothing overflows.
  useLayoutEffect(() => {
    const el = pdfPaneRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      const available = entry.contentRect.width - 32
      setPageWidth(Math.max(280, Math.min(760, available)))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const askMutation = useMutation({
    mutationFn: (text: string) => {
      const controller = new AbortController()
      queryAbortControllerRef.current = controller
      return sendQuery({
        query: text,
        top_k: 5,
        conversation_id: conversationId ?? undefined,
        document_id: documentId,
        signal: controller.signal,
      })
    },
    onSuccess: (response) => {
      queryAbortControllerRef.current = null
      setConversationId(response.conversation_id)
      setTurns((current) => [
        ...current,
        {
          id: response.query_id,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          claims: response.claim_verifications,
          evidenceGate: response.evidence_gate,
          auditAttempted: true,
        },
      ])
      const first = response.sources[0]
      if (first) {
        setSelectedSource(first)
        if (first.page_number) setPage(first.page_number)
      }
      void queryClient.invalidateQueries({ queryKey: ['query-history'] })
    },
    onError: (error) => {
      queryAbortControllerRef.current = null
      if (isRequestCancelled(error)) return
      if (isMissingGeminiApiKeyError(error)) {
        toast.error('Gemini API key required', { description: 'Configure an API key to ask questions about this document.' })
        return
      }
      toast.error('Query failed', { description: getApiErrorMessage(error) })
    },
  })

  const requiresGeminiApiKey = askMutation.isError && isMissingGeminiApiKeyError(askMutation.error)

  const summaryMutation = useMutation({ mutationFn: () => summarizeDocument(documentId!) })
  const quizMutation = useMutation({ mutationFn: () => generateQuiz(documentId!) })
  const mindmapMutation = useMutation({ mutationFn: () => generateMindmap(documentId!) })

  const submit = () => {
    const text = draft.trim()
    if (!text || askMutation.isPending || !isReady) return
    setTurns((current) => [...current, { id: `u-${Date.now()}`, role: 'user', content: text }])
    setDraft('')
    askMutation.mutate(text)
  }

  const stop = () => {
    queryAbortControllerRef.current?.abort()
    queryAbortControllerRef.current = null
  }

  const selectSource = (source: SourceReference) => {
    setSelectedSource(source)
    if (source.page_number) setPage(source.page_number)
    setMobilePane('source')
  }

  const switchTool = (next: Tool) => {
    setTool(next)
    if (next !== 'ask') setShowSecondaryTools(true)
    if (next === 'summary' && !summaryMutation.data && !summaryMutation.isPending) summaryMutation.mutate()
    if (next === 'quiz' && !quizMutation.data && !quizMutation.isPending) quizMutation.mutate()
    if (next === 'mindmap' && !mindmapMutation.data && !mindmapMutation.isPending) mindmapMutation.mutate()
  }

  // Scale the stored bbox into rendered pixel space.
  const highlights = useMemo(() => {
    const bboxes = selectedSource?.bboxes?.length ? selectedSource.bboxes : selectedSource?.bbox ? [selectedSource.bbox] : []
    if (!nativeSize || !renderedSize || (selectedSource?.page_number && selectedSource.page_number !== page)) return []
    const sx = renderedSize.w / nativeSize.w
    const sy = renderedSize.h / nativeSize.h
    return bboxes.map((bbox) => ({ left: bbox.x1 * sx, top: bbox.y1 * sy, width: Math.max(2, (bbox.x2 - bbox.x1) * sx), height: Math.max(2, (bbox.y2 - bbox.y1) * sy) }))
  }, [selectedSource, nativeSize, renderedSize, page])

  const allSources = useMemo(
    () => [...turns].reverse().find((t) => t.sources?.length)?.sources ?? [],
    [turns],
  )

  if (docQuery.isError) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-base">Could not open this document</CardTitle>
            <CardDescription>{getApiErrorMessage(docQuery.error)}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => navigate('/')}>
              <ArrowLeft className="size-4" />
              Back to library
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden lg:flex-row">
      {/* ---------------- Answer pane ---------------- */}
      <section
        className={`flex min-w-0 flex-1 flex-col overflow-hidden border-b lg:border-b-0 lg:border-r ${
          mobilePane === 'source' ? 'hidden lg:flex' : 'flex'
        }`}
      >
        <div className="flex items-center gap-2 border-b px-3 py-2.5">
          <Button variant="ghost" size="icon" className="size-8" aria-label="Back to library" onClick={() => navigate('/')}>
            <ArrowLeft className="size-4" />
          </Button>
          <FileText className="size-4 shrink-0 text-primary" />
          <div className="min-w-0 flex-1">
            {docQuery.isLoading ? (
              <Skeleton className="h-4 w-40" />
            ) : (
              <p className="truncate text-sm font-medium">{doc?.filename}</p>
            )}
          </div>
          <Badge variant="outline" className="hidden gap-1 border-primary/30 bg-primary/5 text-[10px] text-primary sm:inline-flex">
            <ShieldCheck className="size-3" /> Evidence Gate
          </Badge>
          {selectedSource && (
            <Button variant="outline" size="sm" className="lg:hidden" onClick={() => setMobilePane('source')}>
              <PanelRightOpen className="size-4" />
              Evidence
            </Button>
          )}
        </div>

        {!isReady && taskId && (
          <div className="space-y-1.5 border-b px-4 py-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Processing document…</span>
              <span className="tabular-nums text-primary">{Math.round(taskProgress * 100)}%</span>
            </div>
            <Progress value={taskProgress * 100} className="h-1" />
          </div>
        )}

        {isReady && (
          <div className="flex items-center gap-2 border-b px-3 py-2">
            <Tabs value={tool} onValueChange={(v) => switchTool(v as Tool)} className="min-w-0 flex-1">
              <TabsList className="max-w-full justify-start overflow-x-auto">
                <TabsTrigger value="ask">Evidence chat</TabsTrigger>
                {showSecondaryTools && (
                  <>
                    <TabsTrigger value="summary">Summary</TabsTrigger>
                    <TabsTrigger value="quiz">Quiz</TabsTrigger>
                    <TabsTrigger value="mindmap">Mind map</TabsTrigger>
                  </>
                )}
              </TabsList>
            </Tabs>
            <Button
              variant="ghost"
              size="sm"
              className="shrink-0 text-xs text-muted-foreground"
              onClick={() => setShowSecondaryTools((visible) => !visible)}
            >
              {showSecondaryTools ? 'Hide tools' : 'Other tools'}
            </Button>
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {!isReady ? (
            <div className="flex min-h-full items-center justify-center py-10">
              <Card className="w-full max-w-md text-center">
                <CardHeader className="items-center">
                  <div className="mb-1 flex size-11 items-center justify-center rounded-lg border bg-card">
                    {isFailed ? (
                      <AlertTriangle className="size-5 text-destructive" />
                    ) : (
                      <Loader2 className="size-5 animate-spin text-primary" />
                    )}
                  </div>
                  <CardTitle className="text-base">{processingTitle}</CardTitle>
                  <CardDescription className="max-w-sm">{processingDescription}</CardDescription>
                </CardHeader>
                {!isFailed && (
                  <CardContent className="space-y-2 pb-6">
                    <Progress value={taskProgressPercent} className="h-2" />
                    <p className="text-xs text-muted-foreground">
                      {workspaceStatus === 'pending' ? 'Waiting for a worker to start' : `${taskProgressPercent}% complete`}
                    </p>
                  </CardContent>
                )}
              </Card>
            </div>
          ) : tool === 'ask' ? (
            <div className="space-y-4">
              {turns.length === 0 && (
                <div className="py-12 text-center">
                  <div className="mx-auto mb-3 flex size-11 items-center justify-center rounded-lg border bg-card">
                    <Sparkles className="size-5 text-primary" />
                  </div>
                  <p className="text-base font-medium">Interrogate the evidence</p>
                  <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
                    Ask a question, inspect the exact source region, then open the Evidence Gate audit to review each claim.
                  </p>
                </div>
              )}

              {turns.map((turn) =>
                turn.role === 'user' ? (
                  <div key={turn.id} className="ml-auto max-w-[85%] rounded-lg bg-secondary px-3.5 py-2.5">
                    <p className="text-sm whitespace-pre-wrap">{turn.content}</p>
                  </div>
                ) : (
                  <Card key={turn.id} className="max-w-none gap-0 py-0">
                    <CardContent className="space-y-3 p-4">
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">{turn.content}</div>

                      {turn.auditAttempted && (
                        turn.evidenceGate ? (
                          <EvidenceGateRunCard
                            gate={turn.evidenceGate}
                            onOpenReview={() => navigate(`/review/${encodeURIComponent(turn.evidenceGate!.id)}`)}
                          />
                        ) : (
                          <AuditUnavailableCard />
                        )
                      )}

                      {turn.claims && turn.claims.length > 0 && (
                        <>
                          <Separator />
                          <div className="space-y-1.5">
                            <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                              Claim verification
                            </p>
                            {turn.claims.map((claim, i) => {
                              const supported = claim.status === 'supported'
                              const unsupported = claim.status === 'unsupported'
                              const claimSources = claim.supporting_sources
                                .map((sourceNumber) => turn.sources?.find((source) => source.source_number === sourceNumber))
                                .filter((source): source is SourceReference => Boolean(source))
                              const Icon = supported ? CheckCircle2 : unsupported ? AlertTriangle : HelpCircle
                              return (
                                <div
                                  key={i}
                                  className={`flex items-start gap-2 rounded-md border px-3 py-2 text-xs ${
                                    supported
                                      ? 'border-[color:var(--success)]/25 bg-[color:var(--success)]/5'
                                      : unsupported
                                        ? 'border-destructive/25 bg-destructive/5'
                                        : 'bg-muted/40'
                                  }`}
                                >
                                  <Icon
                                    className={`mt-0.5 size-3.5 shrink-0 ${
                                      supported
                                        ? 'text-[color:var(--success)]'
                                        : unsupported
                                          ? 'text-destructive'
                                          : 'text-muted-foreground'
                                    }`}
                                  />
                                  <div className="min-w-0 space-y-0.5">
                                    <p className="leading-relaxed">{claim.claim}</p>
                                    <p className="text-muted-foreground">
                                      {claimLabel(claim.status)}
                                      {claim.reason ? ` · ${claim.reason}` : ''}
                                    </p>
                                    {claimSources.length > 0 && (
                                      <div className="flex flex-wrap gap-1 pt-1">
                                        {claimSources.map((source) => (
                                          <Button
                                            key={`${claim.claim}-${source.chunk_id}`}
                                            variant="outline"
                                            size="sm"
                                            className="h-6 px-1.5 text-[10px]"
                                            onClick={() => selectSource(source)}
                                          >
                                            View {source.citation_label}
                                          </Button>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </>
                      )}

                      {turn.sources && turn.sources.length > 0 && (
                        <>
                          <Separator />
                          <div className="flex flex-wrap gap-1.5">
                            {turn.sources.map((source) => (
                              <Button
                                key={source.chunk_id}
                                variant={selectedSource?.chunk_id === source.chunk_id ? 'default' : 'outline'}
                                size="sm"
                                className="h-7 px-2 text-xs font-normal"
                                onClick={() => selectSource(source)}
                              >
                                {source.citation_label}
                              </Button>
                            ))}
                          </div>
                        </>
                      )}
                    </CardContent>
                  </Card>
                ),
              )}

              {requiresGeminiApiKey && (
                <GeminiKeyRequiredCard onConfigure={() => navigate('/byok')} />
              )}

              {askMutation.isPending && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin text-primary" />
                  Retrieving evidence and verifying claims…
                </div>
              )}
              <div ref={endRef} />
            </div>
          ) : (
            <ToolPanel
              tool={tool}
              summary={summaryMutation.data?.summary}
              quiz={quizMutation.data?.quiz}
              mindmap={mindmapMutation.data?.mindmap}
              isPending={
                (tool === 'summary' && summaryMutation.isPending) ||
                (tool === 'quiz' && quizMutation.isPending) ||
                (tool === 'mindmap' && mindmapMutation.isPending)
              }
              error={
                tool === 'summary'
                  ? summaryMutation.error
                  : tool === 'quiz'
                    ? quizMutation.error
                    : mindmapMutation.error
              }
              onRegenerate={() => {
                if (tool === 'summary') summaryMutation.mutate()
                if (tool === 'quiz') quizMutation.mutate()
                if (tool === 'mindmap') mindmapMutation.mutate()
              }}
            />
          )}
        </div>

        {tool === 'ask' && (
          <div className="border-t p-3">
            <div className="flex items-end gap-2">
              <Textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    submit()
                  }
                }}
                rows={1}
                disabled={!isReady}
                aria-label="Ask a question about this document"
                placeholder={isReady ? 'Ask a question to inspect its evidence…' : 'Available once processing finishes'}
                className="max-h-32 min-h-10 resize-none"
              />
              {askMutation.isPending ? (
                <Button size="icon" variant="destructive" aria-label="Stop generating" title="Stop generating" onClick={stop}>
                  <Square className="size-3.5 fill-current" />
                </Button>
              ) : (
                <Button
                  size="icon"
                  aria-label="Send question"
                  disabled={!draft.trim() || !isReady}
                  onClick={submit}
                >
                  <Send className="size-4" />
                </Button>
              )}
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground">
              Enter to send · Eligible answers are audited when the Evidence Gate is available
            </p>
          </div>
        )}
      </section>

      {/* ---------------- Evidence pane ---------------- */}
      <section
        className={`min-w-0 flex-1 flex-col overflow-hidden bg-muted/20 ${
          mobilePane === 'source' ? 'flex' : 'hidden lg:flex'
        }`}
      >
        <div className="flex items-center gap-2 border-b px-3 py-2.5">
          <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setMobilePane('answer')}>
            <ArrowLeft className="size-4" />
            Answer
          </Button>
          <p className="text-sm font-medium">Evidence</p>
          {selectedSource && (
            <Badge variant="outline" className="ml-auto font-normal tabular-nums">
              {(selectedSource.similarity_score * 100).toFixed(0)}% match
            </Badge>
          )}
        </div>

        {selectedSource && (
          <div className="space-y-1 border-b px-4 py-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-sm font-medium">{selectedSource.citation_label}</span>
              {selectedSource.chunk_type === 'table' && (
                <Badge variant="secondary" className="font-normal">Table</Badge>
              )}
            </div>
            {selectedSource.section_title && (
              <p className="text-xs text-muted-foreground">Section: {selectedSource.section_title}</p>
            )}
            {selectedSource.content_preview && (
              <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground italic">
                “{selectedSource.content_preview}”
              </p>
            )}
            {!selectedSource.bbox && (
              <p className="text-xs text-muted-foreground">
                No pixel region stored for this passage. Page and quoted text are shown instead.
              </p>
            )}
          </div>
        )}

        <div ref={pdfPaneRef} className="min-h-0 flex-1 overflow-auto p-4">
          {fileUrlQuery.data?.url ? (
            <div className="flex flex-col items-center gap-3">
              <Document
                file={fileUrlQuery.data.url}
                onLoadSuccess={({ numPages: total }) => setNumPages(total)}
                onLoadError={(error) =>
                  toast.error('Could not load the PDF', { description: error.message })
                }
                loading={<Skeleton className="h-[600px] w-full max-w-[560px]" />}
              >
                <div className="relative inline-block overflow-hidden rounded-md border bg-white">
                  <Page
                    pageNumber={page}
                    width={pageWidth}
                    onLoadSuccess={(p) => {
                      setNativeSize({ w: p.originalWidth, h: p.originalHeight })
                      setRenderedSize({ w: p.width, h: p.height })
                    }}
                  />
                  {highlights.map((highlight, index) => (
                    <div
                      key={index}
                      className="evidence-highlight pointer-events-none absolute z-20 rounded-sm transition-all"
                      style={{ left: `${highlight.left}px`, top: `${highlight.top}px`, width: `${highlight.width}px`, height: `${highlight.height}px` }}
                    />
                  ))}
                </div>
              </Document>

              {numPages && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Button
                    variant="outline"
                    size="icon"
                    className="size-7"
                    aria-label="Previous page"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    <ChevronLeft className="size-4" />
                  </Button>
                  <span className="tabular-nums">
                    Page {page} of {numPages}
                  </span>
                  <Button
                    variant="outline"
                    size="icon"
                    className="size-7"
                    aria-label="Next page"
                    disabled={page >= numPages}
                    onClick={() => setPage((p) => Math.min(numPages, p + 1))}
                  >
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted-foreground">
              {!isPdf
                ? 'Inline preview is available for PDFs. Citations for this file show page and quoted text.'
                : !isReady
                  ? 'The source preview opens once processing finishes.'
                  : fileUrlQuery.isLoading
                    ? 'Loading source document…'
                    : 'Ask a question to see the cited evidence here.'}
            </div>
          )}
        </div>

        {allSources.length > 1 && (
          <div className="max-h-56 shrink-0 overflow-y-auto border-t p-3">
            <p className="mb-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
              All sources ({allSources.length})
            </p>
            <div className="space-y-1.5">
              {allSources.map((source) => (
                <button
                  key={source.chunk_id}
                  type="button"
                  onClick={() => selectSource(source)}
                  className={`w-full rounded-md border p-2.5 text-left transition-colors ${
                    selectedSource?.chunk_id === source.chunk_id
                      ? 'border-primary/40 bg-primary/5'
                      : 'hover:bg-accent/40'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-medium">{source.citation_label}</span>
                    <span className="shrink-0 text-[10px] text-muted-foreground tabular-nums">
                      {(source.similarity_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
                    {source.content_preview}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Summary / Quiz / Mind map                                          */
/* ------------------------------------------------------------------ */

interface ToolPanelProps {
  tool: Exclude<Tool, 'ask'>
  summary?: string
  quiz?: unknown
  mindmap?: unknown
  isPending: boolean
  error: unknown
  onRegenerate: () => void
}

function ToolPanel({ tool, summary, quiz, mindmap, isPending, error, onRegenerate }: ToolPanelProps) {
  if (isPending) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 pt-6">
          <AlertTriangle className="size-4 text-destructive" />
          <p className="flex-1 text-sm text-muted-foreground">{getApiErrorMessage(error)}</p>
          <Button variant="outline" size="sm" onClick={onRegenerate}>
            <RefreshCw className="size-4" />
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  const header = (
    <div className="mb-3 flex items-center justify-between">
      <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
        {tool === 'summary' ? 'Summary' : tool === 'quiz' ? 'Quiz' : 'Mind map'}
      </p>
      <Button variant="ghost" size="sm" onClick={onRegenerate}>
        <RefreshCw className="size-3.5" />
        Regenerate
      </Button>
    </div>
  )

  if (tool === 'summary') {
    return (
      <div>
        {header}
        {summary ? (
          <div className="prose prose-sm prose-invert max-w-none prose-headings:font-semibold prose-p:leading-relaxed">
            <ReactMarkdown>{summary}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No summary yet.</p>
        )}
      </div>
    )
  }

  if (tool === 'quiz') {
    const items = Array.isArray(quiz) ? (quiz as Array<Record<string, unknown>>) : []
    return (
      <div>
        {header}
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No quiz questions were generated.</p>
        ) : (
          <div className="space-y-3">
            {items.map((item, i) => (
              <Card key={i}>
                <CardContent className="space-y-2 p-4">
                  <p className="text-sm font-medium">
                    {i + 1}. {String(item.question ?? '')}
                  </p>
                  {Array.isArray(item.options) && (
                    <ul className="space-y-1">
                      {(item.options as unknown[]).map((option, oi) => (
                        <li key={oi} className="text-sm text-muted-foreground">
                          {String(option)}
                        </li>
                      ))}
                    </ul>
                  )}
                  {item.correct_answer != null && String(item.correct_answer) !== '' && (
                    <p className="text-xs text-[color:var(--success)]">
                      Answer: {String(item.correct_answer)}
                    </p>
                  )}
                  {item.explanation != null && String(item.explanation) !== '' && (
                    <p className="text-xs text-muted-foreground">{String(item.explanation)}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    )
  }

  const map = (mindmap ?? {}) as { central_topic?: unknown; nodes?: unknown; edges?: unknown }
  const nodes = Array.isArray(map.nodes) ? (map.nodes as Array<Record<string, unknown>>) : []
  const edges = Array.isArray(map.edges) ? (map.edges as Array<Record<string, unknown>>) : []
  const nodeLabels = new Map(
    nodes
      .filter((node) => typeof node.id === 'string' && typeof node.label === 'string' && node.label.trim())
      .map((node) => [String(node.id), String(node.label).trim()]),
  )
  const labelFor = (nodeId: unknown) => nodeLabels.get(String(nodeId)) ?? 'Related concept'
  const conceptGroups = nodes.reduce<Record<string, Array<{ id: string; label: string }>>>((groups, node) => {
    const group = typeof node.group === 'string' && node.group.trim() ? node.group.trim() : 'Key concepts'
    const label = typeof node.label === 'string' && node.label.trim() ? node.label.trim() : 'Untitled concept'
    const id = typeof node.id === 'string' ? node.id : label
    groups[group] ??= []
    groups[group].push({ id, label })
    return groups
  }, {})

  return (
    <div>
      {header}
      {map.central_topic ? (
        <Card className="mb-4 border-primary/30 bg-primary/5">
          <CardContent className="p-4 text-center">
            <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Central topic</p>
            <p className="mt-1 text-sm font-semibold">{String(map.central_topic)}</p>
          </CardContent>
        </Card>
      ) : null}
      {nodes.length === 0 ? (
        <p className="text-sm text-muted-foreground">No concepts were extracted.</p>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {Object.entries(conceptGroups).map(([group, concepts]) => (
              <Card key={group}>
                <CardContent className="p-3">
                  <p className="mb-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{group}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {concepts.map((concept) => (
                      <Badge key={concept.id} variant="secondary" className="font-normal">
                        {concept.label}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          {edges.length > 0 && (
            <div className="space-y-2">
              <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Connections</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {edges.map((edge, i) => (
                  <Card key={i} className="bg-muted/30">
                    <CardContent className="space-y-1.5 p-3 text-xs">
                      <p className="font-medium text-foreground">{labelFor(edge.source)}</p>
                      <p className="text-muted-foreground">{String(edge.label ?? 'relates to')}</p>
                      <p className="font-medium text-foreground">{labelFor(edge.target)}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
