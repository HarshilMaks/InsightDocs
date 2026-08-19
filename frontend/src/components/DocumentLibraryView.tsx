import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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

  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    enabled: isAuthenticated,
    staleTime: 30_000,
    // Poll only while something is still being processed.
    refetchInterval: (query) => {
      const docs = query.state.data?.documents ?? []
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

  const documents = documentsQuery.data?.documents ?? []
  const filtered = searchQuery
    ? documents.filter((d) => d.filename.toLowerCase().includes(searchQuery.toLowerCase()))
    : documents

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 p-4 md:p-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Document library</h2>
        <p className="text-sm text-muted-foreground">
          Ask questions and get answers backed by the exact page and region they came from.
        </p>
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
                    className={ready ? 'cursor-pointer' : 'cursor-default'}
                    onClick={() => ready && navigate(`/documents/${doc.id}`)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <FileTypeIcon fileType={doc.file_type} />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{doc.filename}</p>
                          {doc.status === 'failed' && doc.error_message && (
                            <p className="truncate text-xs text-destructive">{doc.error_message}</p>
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
