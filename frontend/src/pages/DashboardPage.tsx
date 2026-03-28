import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { ArchiveRestore, FileStack, Layers3, Upload } from 'lucide-react'
import {
  deleteDocument,
  listTasks,
  uploadDocument,
  getApiErrorMessage,
} from '@/lib/api'
import { formatBytes } from '@/lib/format'
import type { WorkspaceOutletContext } from '@/types'
import { UploadDropzone } from '@/components/UploadDropzone'
import { DocumentCard } from '@/components/DocumentCard'
import { StatCard } from '@/components/StatCard'
import { ConfirmDialog } from '@/components/ConfirmDialog'

function taskIsActive(status: string) {
  return status === 'pending' || status === 'processing'
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { documents, threads } = useOutletContext<WorkspaceOutletContext>()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteErrorMessage, setDeleteErrorMessage] = useState('')
  const [deleteErrorOpen, setDeleteErrorOpen] = useState(false)
  const [uploadErrorMessage, setUploadErrorMessage] = useState('')
  const [uploadErrorOpen, setUploadErrorOpen] = useState(false)
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)

  const tasksQuery = useQuery({
    queryKey: ['tasks'],
    queryFn: () => listTasks(),
    refetchInterval: (query) => {
      const tasks = query.state.data?.tasks ?? []
      return tasks.some((task) => taskIsActive(task.status)) ? 5000 : false
    },
    staleTime: 10_000,
  })

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async (response) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['tasks'] }),
      ])
      navigate(`/documents/${response.document_id}?task=${response.task_id}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['documents'] }),
        queryClient.invalidateQueries({ queryKey: ['tasks'] }),
        queryClient.invalidateQueries({ queryKey: ['query-history'] }),
      ])
    },
  })

  const activeTasks = tasksQuery.data?.tasks.filter((task) => taskIsActive(task.status)) ?? []
  const completedDocuments = documents.filter((document) => document.status === 'completed')
  const totalStorage = documents.reduce((sum, document) => sum + document.file_size, 0)

  const stats = useMemo(
    () => [
      {
        label: 'Documents',
        value: String(documents.length),
        description: 'Files available in the workspace',
        icon: FileStack,
        tone: 'primary' as const,
      },
      {
        label: 'Threads',
        value: String(threads.length),
        description: 'Conversation ids with history',
        icon: Layers3,
        tone: 'sky' as const,
      },
      {
        label: 'Processing',
        value: String(activeTasks.length),
        description: 'Uploads still being processed by the worker',
        icon: Upload,
        tone: 'amber' as const,
      },
      {
        label: 'Ready',
        value: String(completedDocuments.length),
        description: `Completed docs · ${formatBytes(totalStorage)} total`,
        icon: ArchiveRestore,
        tone: 'emerald' as const,
      },
    ],
    [activeTasks.length, completedDocuments.length, documents.length, threads.length, totalStorage],
  )

  const handleDelete = async (documentId: string) => {
    setPendingDeleteId(documentId)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!pendingDeleteId) return
    try {
      await deleteMutation.mutateAsync(pendingDeleteId)
      setPendingDeleteId(null)
    } catch (error) {
      setDeleteErrorMessage(getApiErrorMessage(error))
      setDeleteErrorOpen(true)
    }
  }

  const handleUpload = async (file: File) => {
    try {
      await uploadMutation.mutateAsync(file)
    } catch (error) {
      setUploadErrorMessage(getApiErrorMessage(error))
      setUploadErrorOpen(true)
      throw error
    }
  }

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
              Workspace overview
            </p>
            <h1 className="text-3xl font-semibold text-on-surface sm:text-4xl">
              Upload, analyze, and keep every answer cited.
            </h1>
            <p className="max-w-3xl text-sm leading-6 text-on-surface-variant sm:text-base">
              The dashboard keeps your documents, threads, and processing status together so the
              user can move directly into Ask Your PDF without losing context.
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat) => (
            <StatCard
              key={stat.label}
              description={stat.description}
              icon={stat.icon}
              label={stat.label}
              tone={stat.tone}
              value={stat.value}
            />
          ))}
        </div>
      </section>

      <section id="upload" className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div className="space-y-4 rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                Upload files
              </p>
              <h2 className="text-xl font-semibold text-on-surface">Start a new analysis</h2>
            </div>
            <Upload className="h-5 w-5 text-primary" />
          </div>

          <UploadDropzone isUploading={uploadMutation.isPending} onUpload={handleUpload} />

          <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-low px-5 py-4 text-sm text-on-surface-variant">
            Files enter the worker pipeline immediately, and the document page will show a live
            task status while the upload is being processed.
          </div>
        </div>

        <div className="space-y-4 rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                Worker queue
              </p>
              <h2 className="text-xl font-semibold text-on-surface">Active tasks</h2>
            </div>
            <Layers3 className="h-5 w-5 text-primary" />
          </div>

          {tasksQuery.isLoading ? (
            <div className="space-y-3">
              <div className="h-24 animate-pulse rounded-3xl bg-surface-container-high/80" />
              <div className="h-24 animate-pulse rounded-3xl bg-surface-container-high/80" />
            </div>
          ) : activeTasks.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-outline-variant/15 bg-surface-container-low px-5 py-8 text-sm text-on-surface-variant">
              No active jobs right now. Upload a file to see the pipeline in action.
            </div>
          ) : (
            <div className="space-y-3">
              {activeTasks.map((task) => (
                <div
                  key={task.id}
                  className="rounded-3xl border border-outline-variant/15 bg-surface-container-low px-5 py-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-on-surface">{task.task_type}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.22em] text-on-surface-variant">
                        {task.status}
                      </p>
                    </div>
                    <p className="text-sm font-semibold text-on-surface">
                      {Math.round(task.progress * 100)}%
                    </p>
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-container-high">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-primary to-primary-container transition-all"
                      style={{ width: `${Math.max(5, Math.min(100, task.progress * 100))}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                Library
              </p>
              <h2 className="text-xl font-semibold text-on-surface">Recent documents</h2>
            </div>
          </div>

          {documents.length === 0 ? (
            <div className="rounded-[2rem] border border-dashed border-outline-variant/15 bg-surface-container-low px-5 py-10 text-sm text-on-surface-variant">
              No documents uploaded yet. Drop a file above to populate the library.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
              {documents.map((document) => (
                <DocumentCard
                  key={document.id}
                  document={document}
                  isDeleting={deleteMutation.isPending}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                  Conversation history
                </p>
                <h2 className="text-xl font-semibold text-on-surface">Recent threads</h2>
              </div>
              <Layers3 className="h-5 w-5 text-primary" />
            </div>

            <div className="mt-4 space-y-3">
              {threads.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-outline-variant/15 bg-surface-container-low px-5 py-8 text-sm text-on-surface-variant">
                  Start asking questions and the thread history will appear here.
                </div>
              ) : (
                threads.slice(0, 6).map((thread) => (
                  <button
                    key={thread.conversationId}
                    className="w-full rounded-3xl border border-outline-variant/15 bg-surface-container-low px-5 py-4 text-left transition hover:border-primary/30 hover:bg-surface-container"
                    onClick={() => navigate(`/conversations/${thread.conversationId}`)}
                    type="button"
                  >
                    <p className="text-sm font-semibold text-on-surface">
                      {thread.latestQuery.slice(0, 60)}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                      {thread.latestResponse?.slice(0, 110) ?? 'No assistant response yet.'}
                    </p>
                    <p className="mt-3 text-[11px] uppercase tracking-[0.22em] text-on-surface-variant">
                      {thread.turnCount} turns
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      <ConfirmDialog
        isOpen={deleteDialogOpen}
        title="Delete document?"
        message="This will permanently delete the document and all its indexed chunks. This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        isDangerous
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          setDeleteDialogOpen(false)
          setPendingDeleteId(null)
        }}
      />

      <ConfirmDialog
        isOpen={deleteErrorOpen}
        title="Delete failed"
        message={deleteErrorMessage}
        confirmLabel="OK"
        cancelLabel={undefined as any}
        onConfirm={() => setDeleteErrorOpen(false)}
        onCancel={() => setDeleteErrorOpen(false)}
      />

      <ConfirmDialog
        isOpen={uploadErrorOpen}
        title="Upload failed"
        message={uploadErrorMessage}
        confirmLabel="OK"
        cancelLabel={undefined as any}
        onConfirm={() => setUploadErrorOpen(false)}
        onCancel={() => setUploadErrorOpen(false)}
      />
    </div>
  )
}
