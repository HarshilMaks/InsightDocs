import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  ArrowLeft,
  ArrowRight,
  FileText,
  FolderPlus,
  Loader2,
  MessageSquareText,
  Plus,
  Send,
  Square,
  Trash2,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import {
  addWorkspaceDocument,
  createWorkspace,
  deleteWorkspace,
  getApiErrorMessage,
  getQueryHistory,
  isRequestCancelled,
  getWorkspace,
  listDocuments,
  listWorkspaces,
  removeWorkspaceDocument,
  sendQuery,
  type DocumentResponse,
  type EvidenceWorkspace,
  type EvidenceWorkspaceListItem,
  type QueryResponse,
} from '@/lib/api'

const workspaceKeys = {
  all: ['evidence-workspaces'] as const,
  detail: (id: string) => ['evidence-workspaces', id] as const,
}

function documentStatus(document: DocumentResponse) {
  if (document.status === 'completed') return <Badge className="bg-[color:var(--success)]/15 text-[color:var(--success)] hover:bg-[color:var(--success)]/15">Ready</Badge>
  if (document.status === 'failed') return <Badge variant="destructive">Failed</Badge>
  return <Badge variant="outline">{document.status === 'processing' ? 'Processing' : 'Queued'}</Badge>
}


function WorkspaceDocumentName({ document }: { document: DocumentResponse }) {
  const content = <span className="flex items-center gap-2"><FileText className="size-4 shrink-0" /><span className="truncate">{document.filename}</span></span>
  if (document.status !== 'completed') {
    return <div className="min-w-0 text-sm font-medium text-muted-foreground" title="This document is not ready for evidence review.">{content}</div>
  }
  return <Link to={`/documents/${document.id}`} className="min-w-0 text-sm font-medium hover:text-primary">{content}</Link>
}
function WorkspaceCard({ workspace }: { workspace: EvidenceWorkspaceListItem }) {
  return (
    <Link to={`/workspaces/${workspace.id}`} className="block">
      <Card className="h-full transition-colors hover:border-primary/50 hover:bg-accent/20">
        <CardHeader className="space-y-2 pb-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="truncate text-base">{workspace.name}</CardTitle>
              <CardDescription className="mt-1 line-clamp-2 min-h-10">
                {workspace.description || 'A selected corpus for evidence-grounded review.'}
              </CardDescription>
            </div>
            <Badge variant="outline" className="shrink-0">{workspace.document_count} docs</Badge>
          </div>
        </CardHeader>
        <CardContent className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Updated {new Date(workspace.updated_at).toLocaleDateString()}</span>
          <span className="inline-flex items-center gap-1 text-primary">Open <ArrowRight className="size-3" /></span>
        </CardContent>
      </Card>
    </Link>
  )
}

export function EvidenceWorkspaceListView() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([])
  const workspacesQuery = useQuery({ queryKey: workspaceKeys.all, queryFn: listWorkspaces })
  const documentsQuery = useQuery({ queryKey: ['documents', 'workspace-picker'], queryFn: () => listDocuments(0, 100) })
  const createMutation = useMutation({
    mutationFn: createWorkspace,
    onSuccess: async (workspace) => {
      await queryClient.invalidateQueries({ queryKey: workspaceKeys.all })
      toast.success('Evidence Workspace created')
      setCreateOpen(false)
      setName('')
      setDescription('')
      setSelectedDocuments([])
      navigate(`/workspaces/${workspace.id}`)
    },
    onError: (error) => toast.error('Could not create workspace', { description: getApiErrorMessage(error) }),
  })

  const documents = documentsQuery.data?.documents ?? []
  const readyDocuments = documents.filter((document) => document.status === 'completed')
  const unavailableDocuments = documents.filter((document) => document.status !== 'completed')
  const toggleDocument = (documentId: string) => {
    setSelectedDocuments((current) => current.includes(documentId)
      ? current.filter((id) => id !== documentId)
      : [...current, documentId])
  }
  const submit = () => {
    const trimmedName = name.trim()
    if (!trimmedName) {
      toast.error('Name your Evidence Workspace')
      return
    }
    createMutation.mutate({ name: trimmedName, description: description.trim() || undefined, document_ids: selectedDocuments })
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 p-4 md:p-6">
      <section className="rounded-2xl border bg-card p-5 md:p-7">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div className="space-y-3">
            <Badge variant="outline" className="gap-1.5 border-primary/35 bg-primary/5 text-primary"><MessageSquareText className="size-3.5" /> Multi-document evidence</Badge>
            <div className="space-y-1">
              <h1 className="text-3xl font-semibold tracking-tight">Evidence Workspaces</h1>
              <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">Select an explicit corpus, ask across its ready documents, and keep citations tied to the evidence you chose.</p>
            </div>
          </div>
          <Button onClick={() => setCreateOpen(true)}><FolderPlus className="size-4" /> New workspace</Button>
        </div>
      </section>

      {workspacesQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><Skeleton className="h-40" /><Skeleton className="h-40" /><Skeleton className="h-40" /></div>
      ) : workspacesQuery.isError ? (
        <Card><CardContent className="p-6 text-sm text-destructive">Could not load Evidence Workspaces. {getApiErrorMessage(workspacesQuery.error)}</CardContent></Card>
      ) : (workspacesQuery.data?.workspaces.length ?? 0) === 0 ? (
        <Card className="border-dashed"><CardContent className="flex flex-col items-center gap-3 p-10 text-center"><FolderPlus className="size-8 text-muted-foreground" /><div><p className="font-medium">Create your first selected corpus</p><p className="mt-1 text-sm text-muted-foreground">A workspace never searches your whole library by accident.</p></div><Button variant="outline" onClick={() => setCreateOpen(true)}>Create workspace</Button></CardContent></Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{workspacesQuery.data?.workspaces.map((workspace) => <WorkspaceCard key={workspace.id} workspace={workspace} />)}</div>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader><DialogTitle>Create Evidence Workspace</DialogTitle><DialogDescription>Only the documents selected here will be searched. You can add or remove documents later.</DialogDescription></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2"><Label htmlFor="workspace-name">Name</Label><Input id="workspace-name" value={name} onChange={(event) => setName(event.target.value)} maxLength={120} placeholder="e.g. Vendor security review" /></div>
            <div className="space-y-2"><Label htmlFor="workspace-description">Description <span className="text-muted-foreground">(optional)</span></Label><Textarea id="workspace-description" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} placeholder="What decision or question is this corpus for?" /></div>
            <div className="space-y-2"><Label>Selected documents <span className="text-muted-foreground">({selectedDocuments.length})</span></Label>
              <div className="max-h-52 space-y-1 overflow-y-auto rounded-md border p-2">
                {documentsQuery.isLoading ? <div className="p-2 text-sm text-muted-foreground">Loading documents…</div> : documents.length === 0 ? <div className="p-2 text-sm text-muted-foreground">Upload documents before adding them to a workspace.</div> : <><p className="px-2 py-1 text-xs text-muted-foreground">Only ready documents can be selected and searched.</p>{readyDocuments.map((document) => <button key={document.id} type="button" onClick={() => toggleDocument(document.id)} className={`flex w-full items-center justify-between gap-3 rounded px-2 py-2 text-left text-sm ${selectedDocuments.includes(document.id) ? 'bg-primary/10 text-primary' : 'hover:bg-accent'}`}><span className="truncate">{document.filename}</span>{documentStatus(document)}</button>)}{readyDocuments.length === 0 && <p className="p-2 text-sm text-muted-foreground">No documents are ready yet.</p>}{unavailableDocuments.length > 0 && <div className="mt-2 border-t pt-2"><p className="px-2 py-1 text-xs text-muted-foreground">Unavailable until processing completes</p>{unavailableDocuments.map((document) => <div key={document.id} className="flex items-center justify-between gap-3 rounded px-2 py-2 text-sm opacity-60"><span className="truncate">{document.filename}</span>{documentStatus(document)}</div>)}</div>}</>}
              </div>
            </div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button><Button onClick={submit} disabled={createMutation.isPending}>{createMutation.isPending && <Loader2 className="size-4 animate-spin" />} Create workspace</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

type ChatTurn = { id: string; query: string; result: Pick<QueryResponse, 'answer' | 'sources'> }

function WorkspaceChat({ workspace, conversationId }: { workspace: EvidenceWorkspace; conversationId: string }) {
  const queryClient = useQueryClient()
  const [question, setQuestion] = useState('')
  const queryAbortControllerRef = useRef<AbortController | null>(null)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [pendingQuestion, setPendingQuestion] = useState<{ text: string; failed: boolean } | null>(null)
  const readyCount = workspace.documents.filter((document) => document.status === 'completed').length
  const historyQuery = useQuery({
    queryKey: ['conversation-history', 'workspace', conversationId],
    queryFn: () => getQueryHistory(conversationId),
  })
  useEffect(() => {
    if (!historyQuery.data) return
    const restored = historyQuery.data.queries
      .filter((item) => item.response)
      .map((item) => ({
        id: item.id,
        query: item.query,
        result: { answer: item.response ?? '', sources: [] },
      }))
    setTurns((current) => current.length === 0 ? restored : current)
  }, [historyQuery.data])
  const queryMutation = useMutation({
    mutationFn: (query: string) => {
      const controller = new AbortController()
      queryAbortControllerRef.current = controller
      return sendQuery({
        query,
        workspace_id: workspace.id,
        conversation_id: conversationId,
        top_k: 5,
        signal: controller.signal,
      })
    },
    onSuccess: (result, query) => {
      queryAbortControllerRef.current = null
      setTurns((current) => [...current, { id: result.query_id, query, result }])
      setPendingQuestion(null)
      void queryClient.invalidateQueries({ queryKey: ['query-history'] })
    },
    onError: (error) => {
      queryAbortControllerRef.current = null
      setPendingQuestion((current) => current ? { ...current, failed: true } : current)
      if (isRequestCancelled(error)) return
      toast.error('Workspace query failed', { description: getApiErrorMessage(error) })
    },
  })
  const ask = () => {
    const query = question.trim()
    if (!query || queryMutation.isPending || readyCount === 0) return
    setQuestion('')
    setPendingQuestion({ text: query, failed: false })
    queryMutation.mutate(query)
  }

  const stop = () => {
    queryAbortControllerRef.current?.abort()
    queryAbortControllerRef.current = null
  }

  return <Card className="min-h-[32rem]"><CardHeader className="border-b pb-4"><CardTitle className="flex items-center gap-2 text-base"><MessageSquareText className="size-4 text-primary" /> Ask this selected corpus</CardTitle><CardDescription>{readyCount > 0 ? `${readyCount} ready document${readyCount === 1 ? '' : 's'} will be searched. Documents outside this workspace are excluded.` : 'Add at least one ready document before querying.'}</CardDescription></CardHeader><CardContent className="flex min-h-[27rem] flex-col p-0"><div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">{pendingQuestion && <div className="space-y-3"><div className="ml-auto max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">{pendingQuestion.text}</div><div className="flex items-center gap-2 text-sm text-muted-foreground">{pendingQuestion.failed ? 'No response was saved. You can submit the question again.' : <><Loader2 className="size-4 animate-spin" /> Answering from the selected corpus…</>}</div></div>}{turns.length === 0 && !pendingQuestion ? <div className="flex h-full min-h-48 items-center justify-center text-center text-sm text-muted-foreground">Ask a question across the selected evidence. Every source remains linked to its original document.</div> : turns.map((turn) => <div key={turn.id} className="space-y-3"><div className="ml-auto max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">{turn.query}</div><div className="max-w-[92%] rounded-lg border bg-muted/25 p-3"><p className="whitespace-pre-wrap text-sm leading-relaxed">{turn.result.answer}</p>{turn.result.sources.length > 0 && <div className="mt-4 space-y-2 border-t pt-3"><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Evidence sources</p>{turn.result.sources.map((source) => <Link key={`${turn.id}-${source.source_number}`} to={`/documents/${source.document_id}`} className="block rounded-md border bg-card p-2 text-xs transition-colors hover:border-primary/50"><div className="flex items-center justify-between gap-2"><span className="truncate font-medium">{source.document_name}</span><span className="shrink-0 text-muted-foreground">{source.page_number ? `Page ${source.page_number}` : 'Source'}</span></div><p className="mt-1 line-clamp-2 text-muted-foreground">{source.content_preview}</p></Link>)}</div>}</div></div>)}</div><div className="border-t p-3"><div className="flex gap-2"><Textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); ask() } }} disabled={readyCount === 0 || queryMutation.isPending} placeholder={readyCount === 0 ? 'This workspace has no ready documents.' : 'Ask a question about the selected evidence…'} className="min-h-11 resize-none" />{queryMutation.isPending ? <Button size="icon" variant="destructive" onClick={stop} aria-label="Stop generating" title="Stop generating"><Square className="size-3.5 fill-current" /></Button> : <Button size="icon" onClick={ask} disabled={!question.trim() || readyCount === 0} aria-label="Send workspace question"><Send className="size-4" /></Button>}</div></div></CardContent></Card>
}

export function EvidenceWorkspaceDetailView() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const [searchParams] = useSearchParams()
  const [newConversationId] = useState(() => crypto.randomUUID())
  const conversationId = searchParams.get('conversation') ?? newConversationId
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const workspaceQuery = useQuery({ queryKey: workspaceKeys.detail(workspaceId ?? ''), queryFn: () => getWorkspace(workspaceId ?? ''), enabled: Boolean(workspaceId) })
  const documentsQuery = useQuery({ queryKey: ['documents', 'workspace-picker'], queryFn: () => listDocuments(0, 100) })
  const addMutation = useMutation({ mutationFn: (documentId: string) => addWorkspaceDocument(workspaceId!, documentId), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: workspaceKeys.detail(workspaceId!) }); await queryClient.invalidateQueries({ queryKey: workspaceKeys.all }) }, onError: (error) => toast.error('Could not add document', { description: getApiErrorMessage(error) }) })
  const removeMutation = useMutation({ mutationFn: (documentId: string) => removeWorkspaceDocument(workspaceId!, documentId), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: workspaceKeys.detail(workspaceId!) }); await queryClient.invalidateQueries({ queryKey: workspaceKeys.all }) }, onError: (error) => toast.error('Could not remove document', { description: getApiErrorMessage(error) }) })
  const deleteMutation = useMutation({ mutationFn: () => deleteWorkspace(workspaceId!), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: workspaceKeys.all }); toast.success('Evidence Workspace deleted'); navigate('/workspaces') }, onError: (error) => toast.error('Could not delete workspace', { description: getApiErrorMessage(error) }) })

  const availableDocuments = useMemo(() => {
    const included = new Set(workspaceQuery.data?.documents.map((document) => document.id) ?? [])
    return (documentsQuery.data?.documents ?? []).filter(
      (document) => !included.has(document.id) && document.status === 'completed',
    )
  }, [documentsQuery.data?.documents, workspaceQuery.data?.documents])

  if (workspaceQuery.isLoading) return <div className="space-y-4 p-4 md:p-6"><Skeleton className="h-24" /><Skeleton className="h-96" /></div>
  if (workspaceQuery.isError || !workspaceQuery.data) return <div className="p-4 md:p-6"><Card><CardContent className="space-y-3 p-6"><p className="text-sm text-destructive">Could not load this Evidence Workspace. {workspaceQuery.isError ? getApiErrorMessage(workspaceQuery.error) : ''}</p><Button variant="outline" onClick={() => navigate('/workspaces')}><ArrowLeft className="size-4" /> Back to workspaces</Button></CardContent></Card></div>
  const workspace = workspaceQuery.data

  return <div className="mx-auto w-full max-w-7xl space-y-5 p-4 md:p-6"><div className="flex flex-wrap items-start justify-between gap-3"><div><Button variant="ghost" size="sm" className="-ml-2 mb-2" onClick={() => navigate('/workspaces')}><ArrowLeft className="size-4" /> Workspaces</Button><h1 className="text-2xl font-semibold tracking-tight">{workspace.name}</h1>{workspace.description && <p className="mt-1 text-sm text-muted-foreground">{workspace.description}</p>}</div><Button variant="outline" className="text-destructive hover:text-destructive" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}><Trash2 className="size-4" /> Delete</Button></div><div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_21rem]"><WorkspaceChat workspace={workspace} conversationId={conversationId} /><Card><CardHeader><CardTitle className="text-base">Selected documents</CardTitle><CardDescription>Only ready documents are eligible for workspace retrieval.</CardDescription></CardHeader><CardContent className="space-y-3">{workspace.documents.length === 0 ? <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">No documents selected. Add at least one completed document to ask questions.</p> : workspace.documents.map((document) => <div key={document.id} className="rounded-md border p-3"><div className="flex items-start justify-between gap-2"><WorkspaceDocumentName document={document} /><Button size="icon" variant="ghost" className="size-7 text-muted-foreground hover:text-destructive" onClick={() => removeMutation.mutate(document.id)} disabled={removeMutation.isPending} aria-label={`Remove ${document.filename}`}><X className="size-4" /></Button></div><div className="mt-2">{documentStatus(document)}</div></div>)}{availableDocuments.length > 0 && <div className="space-y-2 border-t pt-3"><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Add from library</p>{availableDocuments.map((document) => <button type="button" key={document.id} onClick={() => addMutation.mutate(document.id)} disabled={addMutation.isPending} className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent disabled:opacity-50"><span className="truncate">{document.filename}</span><Plus className="size-4 shrink-0 text-primary" /></button>)}</div>}</CardContent></Card></div></div>
}
