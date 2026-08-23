import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import {
  Upload,
  FileText,
  File as FileIcon,
  Presentation,
  Trash2,
  Loader2,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAuth } from '@/context/auth-context'
import {
  listDocuments,
  uploadDocument,
  deleteDocument,
  getApiErrorMessage,
  type DocumentResponse,
} from '@/lib/api'

interface DocumentLibraryViewProps {
  searchQuery: string
  onRequireAuth: () => void
}

const DOCUMENT_PAGE_SIZE = 100

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FileTypeIcon({ fileType }: { fileType: string }) {
  const type = fileType.toLowerCase()
  if (type === '.pdf') return <FileText className="size-4 text-primary" />
  if (type === '.pptx') return <Presentation className="size-4 text-muted-foreground" />
  return <FileIcon className="size-4 text-muted-foreground" />
}

function StatusBadge({ status }: { status: DocumentResponse['status'] }) {
  switch (status) {
    case 'completed':
      return (
        <Badge variant="outline" className="gap-1.5 border-[color:var(--success)]/30 text-[color:var(--success)]">
          <span className="size-1.5 rounded-full bg-[color:var(--success)]" />
          Ready
        </Badge>
      )
    case 'processing':
      return (
        <Badge variant="outline" className="gap-1.5 border-primary/30 text-primary">
          <span className="size-1.5 animate-pulse rounded-full bg-primary" />
          Processing
        </Badge>
      )
    case 'pending':
      return (
        <Badge variant="outline" className="gap-1.5 text-muted-foreground">
          <span className="size-1.5 rounded-full bg-muted-foreground" />
          Queued
        </Badge>
      )
    case 'failed':
      return (
        <Badge variant="outline" className="gap-1.5 border-destructive/30 text-destructive">
          <span className="size-1.5 rounded-full bg-destructive" />
          Failed
        </Badge>
      )
  }
}

export function DocumentLibraryView({ searchQuery, onRequireAuth }: DocumentLibraryViewProps) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { isAuthenticated } = useAuth()
  const queryClient = useQueryClient()
  const [pendingDelete, setPendingDelete] = useState<DocumentResponse | null>(null)

  const documentsQuery = useInfiniteQuery({
    queryKey: ['documents'],
    queryFn: ({ pageParam }) => listDocuments(pageParam, DOCUMENT_PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      const loaded = pages.reduce((count, page) => count + page.documents.length, 0)
      return loaded < lastPage.total ? loaded : undefined
    },
    enabled: isAuthenticated,
    staleTime: 30_000,
    // Poll only while something is still being processed.
    refetchInterval: (query) => {
      const docs = query.state.data?.pages.flatMap((page) => page.documents) ?? []
      return docs.some((d) => d.status === 'pending' || d.status === 'processing') ? 5000 : false
    },
  })

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Upload started', { description: 'Processing has begun.' })
      navigate(`/documents/${response.document_id}?task=${response.task_id}`)
    },
    onError: (error) => toast.error('Upload failed', { description: getApiErrorMessage(error) }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Document deleted')
      setPendingDelete(null)
    },
    onError: (error) => toast.error('Delete failed', { description: getApiErrorMessage(error) }),
  })

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    multiple: false,
    noClick: !isAuthenticated,
    disabled: uploadMutation.isPending,
    onDrop: (files) => {
      if (!isAuthenticated) {
        onRequireAuth()
        return
      }
      const file = files[0]
      if (file) uploadMutation.mutate(file)
    },
  })

  // "New analysis" in the sidebar navigates here with ?upload=true.
  // Honour that intent once by opening the file picker, then clear the flag.
  const openedFromParam = useRef(false)
  useEffect(() => {
    if (searchParams.get('upload') !== 'true') return
    const next = new URLSearchParams(searchParams)
    next.delete('upload')
    setSearchParams(next, { replace: true })
    if (isAuthenticated && !openedFromParam.current) {
      openedFromParam.current = true
      open()
    }
  }, [searchParams, setSearchParams, isAuthenticated, open])

  const documents = documentsQuery.data?.pages.flatMap((page) => page.documents) ?? []
  const filtered = searchQuery
    ? documents.filter((d) => d.filename.toLowerCase().includes(searchQuery.toLowerCase()))
    : documents

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 p-4 md:p-6">
      <section className="overflow-hidden rounded-2xl border bg-card">
        <div className="grid gap-0 md:grid-cols-[minmax(0,0.82fr)_minmax(20rem,1.18fr)]">
          <div className="flex flex-col justify-between gap-7 p-6 md:p-8">
            <div className="space-y-3">
              <Badge variant="outline" className="w-fit gap-1.5 border-primary/35 bg-primary/5 text-primary">
                <ShieldCheck className="size-3.5" />
                Evidence workspace
              </Badge>
              <div className="space-y-2">
                <h2 className="max-w-md text-3xl font-semibold tracking-tight md:text-4xl">Start with a source.</h2>
                <p className="max-w-md text-sm leading-relaxed text-muted-foreground md:text-base">
                  Add one document, let it become ready, then work from evidence you can inspect.
                </p>
              </div>
            </div>
            <div className="rounded-xl border bg-muted/25 p-3.5">
              <div className="flex items-start gap-2.5">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
                <p className="text-sm leading-relaxed text-muted-foreground">
                  <span className="font-medium text-foreground">Evidence Gate.</span> Eligible answers are checked against their retained source snapshot. Human review stays separate and traceable.
                </p>
              </div>
            </div>
          </div>

          <div
            {...getRootProps()}
            role="button"
            tabIndex={0}
            aria-label="Upload a document"
            className={`group relative isolate flex min-h-[22rem] cursor-pointer flex-col items-center justify-center overflow-hidden border-t border-dashed px-6 py-10 text-center outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50 md:border-l md:border-t-0 ${
              isDragActive ? 'border-primary bg-primary/10' : 'hover:border-primary/55 hover:bg-accent/25'
            } ${uploadMutation.isPending ? 'pointer-events-none opacity-70' : ''}`}
          >
            <input {...getInputProps()} />
            <div aria-hidden="true" className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_50%_42%,hsl(var(--primary)/0.16),transparent_38%)] opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
            <div aria-hidden="true" className={`absolute size-52 rounded-full border border-primary/15 transition-transform duration-700 ${isDragActive ? 'scale-110' : 'scale-100 group-hover:scale-110'}`} />
            <div aria-hidden="true" className={`absolute size-36 rounded-full border border-primary/20 transition-transform duration-500 ${isDragActive ? 'scale-90' : 'scale-100 group-hover:scale-95'}`} />

            <div className="relative mb-6 flex size-20 items-center justify-center">
              {!uploadMutation.isPending && <span aria-hidden="true" className="absolute inset-0 rounded-3xl bg-primary/15 motion-safe:animate-ping" />}
              <div className={`relative flex size-16 items-center justify-center rounded-2xl border border-primary/25 bg-card text-primary shadow-sm transition-transform duration-300 ${isDragActive ? '-translate-y-2 scale-110' : 'group-hover:-translate-y-1 group-hover:scale-105'}`}>
                {uploadMutation.isPending ? <Loader2 className="size-7 animate-spin" /> : <Upload className="size-7" />}
              </div>
            </div>

            <div className="relative space-y-2">
              <p className="text-lg font-semibold tracking-tight">
                {uploadMutation.isPending
                  ? 'Adding your source…'
                  : isDragActive
                    ? 'Release to add this source'
                    : 'Drop a source file here'}
              </p>
              <p className="text-sm text-muted-foreground">
                {uploadMutation.isPending ? 'The document will open when processing begins.' : 'or click anywhere in this panel to browse'}
              </p>
            </div>

            <div className="relative mt-7 flex flex-wrap justify-center gap-2 text-xs">
              {['PDF', 'DOCX', 'PPTX', 'TXT'].map((format) => (
                <span key={format} className="rounded-full border bg-card/80 px-2.5 py-1 font-medium text-muted-foreground">{format}</span>
              ))}
              <span className="rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 font-medium text-primary">Up to 50 MB</span>
            </div>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap items-end justify-between gap-2">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold tracking-tight">Evidence library</h3>
          <p className="text-sm text-muted-foreground">Source documents available for evidence-grounded analysis.</p>
        </div>
      </div>

      {/* Upload */}
      <div
        {...getRootProps()}
        role="button"
        tabIndex={0}
        aria-label="Upload a document"
        className={`grid-surface flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 text-center transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 ${
          isDragActive ? 'border-primary bg-primary/5' : 'hover:border-primary/50 hover:bg-accent/30'
        } ${uploadMutation.isPending ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="mb-3 flex size-11 items-center justify-center rounded-lg border bg-card">
          {uploadMutation.isPending ? (
            <Loader2 className="size-5 animate-spin text-primary" />
          ) : (
            <Upload className="size-5 text-muted-foreground" />
          )}
        </div>
        <p className="text-sm font-medium">
          {uploadMutation.isPending
            ? 'Uploading…'
            : isDragActive
              ? 'Drop the file to upload'
              : 'Drop a file here, or click to browse'}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">PDF, DOCX, PPTX or TXT · up to 50 MB</p>
      </div>

      {/* Table / states */}
      {!isAuthenticated ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sign in to see your documents</CardTitle>
            <CardDescription>Your library and conversations are private to your account.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Use the Sign in button in the top bar to continue.</p>
          </CardContent>
        </Card>
      ) : documentsQuery.isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : documentsQuery.isError ? (
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <AlertCircle className="size-4 text-destructive" />
            <div className="flex-1 text-sm">
              <p className="font-medium">Could not load your documents</p>
              <p className="text-muted-foreground">{getApiErrorMessage(documentsQuery.error)}</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => documentsQuery.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {searchQuery ? 'No matches' : 'No documents yet'}
            </CardTitle>
            <CardDescription>
              {searchQuery
                ? `Nothing matched “${searchQuery}”. Try a different search.`
                : 'Upload a document above and it will appear here once processed.'}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border">
            <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Name</TableHead>
                <TableHead className="hidden w-24 sm:table-cell">Size</TableHead>
                <TableHead className="w-32">Status</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((doc) => {
                const ready = doc.status === 'completed'
                return (
                  <TableRow
                    key={doc.id}
                    data-state={ready ? undefined : 'disabled'}
                    className={ready ? 'cursor-pointer' : 'cursor-default opacity-65'}
                    title={ready ? undefined : 'This document is unavailable until processing completes.'}
                    onClick={() => ready && navigate(`/documents/${doc.id}`)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <FileTypeIcon fileType={doc.file_type} />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{doc.filename}</p>
                          {!ready && (
                            <p className={`truncate text-xs ${doc.status === 'failed' ? 'text-destructive' : 'text-muted-foreground'}`}>
                              {doc.status === 'failed'
                                ? doc.error_message || 'Processing failed. This document cannot be used as evidence.'
                                : doc.status === 'processing'
                                  ? 'Processing and indexing — not available as evidence yet.'
                                  : 'Queued for processing — not available as evidence yet.'}
                            </p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="hidden text-xs text-muted-foreground tabular-nums sm:table-cell">
                      {formatBytes(doc.file_size)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={doc.status} />
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete ${doc.filename}`}
                        className="size-8 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation()
                          setPendingDelete(doc)
                        }}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
            </Table>
          </div>
          {documentsQuery.hasNextPage && (
            <div className="flex justify-center pt-1">
              <Button
                variant="outline"
                size="sm"
                disabled={documentsQuery.isFetchingNextPage}
                onClick={() => void documentsQuery.fetchNextPage()}
              >
                {documentsQuery.isFetchingNextPage ? <Loader2 className="size-4 animate-spin" /> : null}
                Load more documents
              </Button>
            </div>
          )}
        </>
      )}

      {/* Delete confirmation */}
      <Dialog open={Boolean(pendingDelete)} onOpenChange={(o) => !o && setPendingDelete(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete this document?</DialogTitle>
            <DialogDescription>
              {pendingDelete?.filename} and all of its indexed content will be removed. This cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
            >
              {deleteMutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
