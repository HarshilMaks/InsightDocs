import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  Check,
  ChevronDown,
  ClipboardCheck,
  ExternalLink,
  FileText,
  Loader2,
  RefreshCw,
  ShieldAlert,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { getApiErrorMessage } from '@/lib/api'
import {
  createReviewDecision,
  getReviewDetail,
  getReviewQueue,
  isStaleReviewConflict,
  type ReviewClaim,
  type ReviewDecision,
  type ReviewSource,
  type ReviewStatus,
} from '@/lib/reviewer-api'

const reviewStatuses: ReviewStatus[] = ['pending', 'accepted', 'rejected']

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'accepted' || status === 'supported') return 'default'
  if (status === 'rejected' || status === 'unsupported') return 'destructive'
  return 'secondary'
}

function readableStatus(status: string) {
  return status.replace(/[_-]/g, ' ')
}

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : '—'
}

function QueueError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 pt-6">
        <AlertCircle className="size-4 shrink-0 text-destructive" />
        <p className="flex-1 text-sm text-muted-foreground">{getApiErrorMessage(error)}</p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="size-3.5" />
          Retry
        </Button>
      </CardContent>
    </Card>
  )
}

export function ReviewerQueueView() {
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>('pending')
  const queueQuery = useQuery({
    queryKey: ['review-queue', reviewStatus],
    queryFn: () => getReviewQueue(reviewStatus),
  })
  const items = queueQuery.data?.items ?? []

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 p-4 md:p-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Evidence reviews</h2>
        <p className="text-sm text-muted-foreground">
          Review evidence-gate runs before relying on their answers.
        </p>
      </div>

      <Tabs value={reviewStatus} onValueChange={(value) => setReviewStatus(value as ReviewStatus)}>
        <TabsList aria-label="Review status filter">
          {reviewStatuses.map((status) => (
            <TabsTrigger key={status} value={status} className="capitalize">
              {status}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {queueQuery.isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((item) => <Skeleton key={item} className="h-28 w-full" />)}
        </div>
      ) : queueQuery.isError ? (
        <QueueError error={queueQuery.error} onRetry={() => void queueQuery.refetch()} />
      ) : items.length === 0 ? (
        <Card>
          <CardHeader className="items-center text-center">
            <div className="mb-1 flex size-11 items-center justify-center rounded-lg border bg-card">
              <ClipboardCheck className="size-5 text-muted-foreground" />
            </div>
            <CardTitle className="text-base">No {reviewStatus} reviews</CardTitle>
            <CardDescription>
              {reviewStatus === 'pending'
                ? 'New evidence-gate runs that require a decision will appear here.'
                : `There are no ${reviewStatus} reviews in this workspace.`}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <Link key={item.id} to={`/review/${encodeURIComponent(item.id)}`} className="block focus:outline-none">
              <Card className="gap-0 py-0 transition-colors hover:bg-muted/40 focus-within:ring-2 focus-within:ring-ring">
                <CardContent className="space-y-3 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="line-clamp-2 font-medium">{item.query_text}</p>
                    <Badge variant={statusVariant(item.review_status)} className="shrink-0 capitalize">
                      {item.review_status}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                    <span>{item.claim_count} claims</span>
                    <span>{item.unsupported_count} unsupported</span>
                    {item.unverified_count > 0 && <span>{item.unverified_count} unverified</span>}
                    <span className="ml-auto">{formatDate(item.created_at)}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

function SourceCard({ source }: { source: ReviewSource }) {
  const navigate = useNavigate()
  const bbox = source.bbox
  const canOpenDocument = Boolean(source.document_id)

  return (
    <details className="rounded-lg border bg-muted/20">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm font-medium marker:hidden">
        <ChevronDown className="size-4 transition-transform [[open]_&]:rotate-180" />
        <span className="truncate">{source.citation_label}: {source.document_name}</span>
        {source.page_number && <Badge variant="outline" className="ml-auto">Page {source.page_number}</Badge>}
      </summary>
      <div className="space-y-3 border-t p-3">
        <blockquote className="border-l-2 border-primary/40 pl-3 text-sm leading-relaxed text-muted-foreground">
          {source.content || 'No source quote was retained for this citation.'}
        </blockquote>
        <dl className="grid grid-cols-1 gap-x-4 gap-y-1 text-xs text-muted-foreground sm:grid-cols-2">
          <div><dt className="inline font-medium text-foreground">Chunk: </dt><dd className="inline font-mono">{source.chunk_id || '—'} · #{source.chunk_index}</dd></div>
          <div><dt className="inline font-medium text-foreground">Type: </dt><dd className="inline capitalize">{source.chunk_type}</dd></div>
          {source.section_title && <div><dt className="inline font-medium text-foreground">Section: </dt><dd className="inline">{source.section_title}</dd></div>}
          <div><dt className="inline font-medium text-foreground">Score: </dt><dd className="inline tabular-nums">{source.similarity_score.toFixed(3)}</dd></div>
          <div className="sm:col-span-2"><dt className="inline font-medium text-foreground">Page / bbox: </dt><dd className="inline font-mono">{source.page_number ?? '—'}{bbox ? ` · (${bbox.x1}, ${bbox.y1})–(${bbox.x2}, ${bbox.y2})${bbox.page_number ? ` page ${bbox.page_number}` : ''}` : ' · no bounding box'}</dd></div>
        </dl>
        {canOpenDocument && (
          <Button variant="outline" size="sm" onClick={() => navigate(`/documents/${encodeURIComponent(source.document_id!)}`)}>
            <ExternalLink className="size-3.5" />
            Open document
          </Button>
        )}
      </div>
    </details>
  )
}

function ClaimCard({ claim }: { claim: ReviewClaim }) {
  return (
    <Card className="gap-0 py-0">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start gap-3">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">{claim.ordinal}</span>
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={statusVariant(claim.verdict)} className="capitalize">{readableStatus(claim.verdict)}</Badge>
              {claim.supporting_source_numbers.length > 0 && (
                <span className="text-xs text-muted-foreground">Sources {claim.supporting_source_numbers.join(', ')}</span>
              )}
            </div>
            <p className="text-sm leading-relaxed">{claim.claim_text}</p>
            {claim.reason && <p className="text-xs leading-relaxed text-muted-foreground">{claim.reason}</p>}
          </div>
        </div>
        {claim.sources.length > 0 ? (
          <div className="space-y-2 pl-9">
            {claim.sources.map((source) => <SourceCard key={`${claim.id}-${source.source_number}`} source={source} />)}
          </div>
        ) : (
          <p className="pl-9 text-xs text-muted-foreground">No accessible source snapshot is available for this claim.</p>
        )}
      </CardContent>
    </Card>
  )
}

export function ReviewerDetailView() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [note, setNote] = useState('')
  const [staleMessage, setStaleMessage] = useState<string | null>(null)
  const detailQuery = useQuery({
    queryKey: ['review-detail', runId],
    queryFn: () => getReviewDetail(runId!),
    enabled: Boolean(runId),
  })

  const decisionMutation = useMutation({
    mutationFn: (decision: ReviewDecision) => createReviewDecision(runId!, {
      decision,
      expected_version: detailQuery.data!.review_version,
      note: note.trim() || undefined,
    }),
    onSuccess: (detail) => {
      queryClient.setQueryData(['review-detail', runId], detail)
      void queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      setNote('')
      setStaleMessage(null)
      toast.success(`Review ${detail.review_status}`, { description: 'The decision was recorded.' })
    },
    onError: async (error) => {
      if (isStaleReviewConflict(error)) {
        const message = 'This review changed before your decision was saved. Its latest state has been loaded.'
        setStaleMessage(message)
        toast.error('Review changed', { description: message })
        await detailQuery.refetch()
        return
      }
      toast.error('Could not save review', { description: getApiErrorMessage(error) })
    },
  })
  const detail = detailQuery.data

  if (detailQuery.isLoading) {
    return <div className="mx-auto w-full max-w-5xl space-y-4 p-4 md:p-6"><Skeleton className="h-8 w-64" /><Skeleton className="h-48 w-full" /><Skeleton className="h-40 w-full" /></div>
  }
  if (detailQuery.isError || !detail) {
    return (
      <div className="mx-auto w-full max-w-5xl space-y-4 p-4 md:p-6">
        <Button variant="ghost" size="sm" onClick={() => navigate('/review')}><ArrowLeft className="size-4" />All reviews</Button>
        <QueueError error={detailQuery.error} onRetry={() => void detailQuery.refetch()} />
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 p-4 md:p-6">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <Button variant="ghost" size="sm" className="-ml-2" onClick={() => navigate('/review')}><ArrowLeft className="size-4" />All reviews</Button>
          <h2 className="text-2xl font-semibold tracking-tight">Evidence review</h2>
          <p className="text-sm text-muted-foreground">Created {formatDate(detail.created_at)} · policy {detail.policy_version}</p>
        </div>
        <Badge variant={statusVariant(detail.review_status)} className="mt-8 shrink-0 capitalize">{detail.review_status}</Badge>
      </div>

      {staleMessage && (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm">
          <ShieldAlert className="mt-0.5 size-4 shrink-0" />
          <span className="flex-1">{staleMessage}</span>
          <Button variant="ghost" size="icon-xs" aria-label="Dismiss conflict message" onClick={() => setStaleMessage(null)}><X /></Button>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Question</CardTitle>
          <CardDescription>Run status: <span className="capitalize">{readableStatus(detail.status)}</span>{detail.action ? ` · ${readableStatus(detail.action)}` : ''}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-relaxed">{detail.query_text}</p>
          <div className="rounded-lg border bg-muted/30 p-3">
            <p className="mb-1 text-xs font-medium text-muted-foreground">Answer</p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{detail.response_text || 'No answer was retained for this run.'}</p>
          </div>
        </CardContent>
      </Card>

      <section className="space-y-3">
        <div className="flex items-center gap-2"><FileText className="size-4 text-primary" /><h3 className="font-medium">Claim verdicts</h3><span className="text-sm text-muted-foreground">{detail.claims.length}</span></div>
        {detail.claims.length > 0 ? detail.claims.map((claim) => <ClaimCard key={claim.id} claim={claim} />) : <Card><CardContent className="pt-6 text-sm text-muted-foreground">This run did not produce claim verdicts.</CardContent></Card>}
      </section>

      <Card>
        <CardHeader><CardTitle className="text-base">Record a decision</CardTitle><CardDescription>Version {detail.review_version}. Add an optional note for the decision history.</CardDescription></CardHeader>
        <CardContent className="space-y-3">
          <Textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2000} placeholder="Optional reviewer note" aria-label="Reviewer note" />
          <div className="flex flex-wrap gap-2">
            <Button disabled={decisionMutation.isPending} onClick={() => decisionMutation.mutate('accepted')}>
              {decisionMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}Accept review
            </Button>
            <Button variant="destructive" disabled={decisionMutation.isPending} onClick={() => decisionMutation.mutate('rejected')}>
              {decisionMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <X className="size-4" />}Reject review
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Decision history</CardTitle><CardDescription>Immutable decisions recorded for this run.</CardDescription></CardHeader>
        <CardContent>
          {detail.decision_history.length === 0 ? <p className="text-sm text-muted-foreground">No decisions have been recorded.</p> : (
            <ol className="space-y-3">
              {detail.decision_history.map((event) => (
                <li key={event.id} className="border-l-2 border-muted pl-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2"><Badge variant={statusVariant(event.decision)} className="capitalize">{event.decision}</Badge><span className="text-xs text-muted-foreground">Version {event.result_version} · {formatDate(event.created_at)}</span></div>
                  {event.note && <p className="mt-1 text-muted-foreground">{event.note}</p>}
                </li>
              ))}
            </ol>
          )}
        </CardContent>
        {detail.reviewed_at && <CardFooter><p className="text-xs text-muted-foreground">Last reviewed {formatDate(detail.reviewed_at)}</p></CardFooter>}
      </Card>
    </div>
  )
}
