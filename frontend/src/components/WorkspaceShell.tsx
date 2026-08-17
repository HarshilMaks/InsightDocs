import { useCallback, useEffect } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/context/auth-context'
import { useWorkspace } from '@/context/workspace-context'
import { deleteDocument, listDocuments, uploadDocument, getApiErrorMessage } from '@/lib/api'
import { WorkspaceNavbar } from '@/components/WorkspaceNavbar'
import { DocumentSidebar } from '@/components/DocumentSidebar'
import { AuthGateModal } from '@/components/AuthGateModal'
import { HomeEmptyState } from '@/components/HomeEmptyState'
import { DocumentWorkspace } from '@/components/DocumentWorkspace'
import { UploadDropzone } from '@/components/UploadDropzone'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { cn } from '@/lib/utils'
import { useState } from 'react'

export function WorkspaceShell() {
  const navigate = useNavigate()
  const { documentId } = useParams<{ documentId: string }>()
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useAuth()
  const queryClient = useQueryClient()
  const { sidebarCollapsed, setAuthGateOpen, pendingIntent, setPendingIntent } = useWorkspace()

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)

  // Only fetch documents when authenticated
  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    enabled: isAuthenticated,
    staleTime: 30_000,
  })

  const documents = documentsQuery.data?.documents ?? []

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
      navigate(`/documents/${response.document_id}?task=${response.task_id}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
      // If the deleted document is currently open, go home
      if (pendingDeleteId === documentId) {
        navigate('/')
      }
      setPendingDeleteId(null)
    },
  })

  // Handle upload click - gate behind auth if not authenticated
  const handleUploadClick = useCallback(() => {
    if (!isAuthenticated) {
      setPendingIntent({ type: 'upload' })
      setAuthGateOpen(true)
      return
    }
    navigate('/?upload=true')
  }, [isAuthenticated, setPendingIntent, setAuthGateOpen, navigate])

  // Handle document delete
  const handleDeleteDocument = useCallback((docId: string) => {
    setPendingDeleteId(docId)
    setDeleteDialogOpen(true)
  }, [])

  const handleConfirmDelete = async () => {
    if (!pendingDeleteId) return
    try {
      await deleteMutation.mutateAsync(pendingDeleteId)
    } catch {
      // Error handled by mutation state
    }
    setDeleteDialogOpen(false)
  }

  // Resume intent after auth
  useEffect(() => {
    if (isAuthenticated && pendingIntent && !searchParams.has('upload')) {
      if (pendingIntent.type === 'upload') {
        navigate('/?upload=true')
      } else if (pendingIntent.type === 'ask' && pendingIntent.documentId) {
        navigate(`/documents/${pendingIntent.documentId}`)
      }
      setPendingIntent(null)
    }
  }, [isAuthenticated, pendingIntent, navigate, setPendingIntent, searchParams])

  const handleUpload = async (file: File) => {
    await uploadMutation.mutateAsync(file)
  }

  // Determine what content to render using reactive searchParams
  const showUploadOverlay = !documentId && isAuthenticated && searchParams.get('upload') === 'true'

  return (
    <div className="flex h-screen flex-col bg-[hsl(226,46%,5%)]">
      <WorkspaceNavbar />

      <div className="flex flex-1 overflow-hidden pt-12">
        {/* Sidebar */}
        <div className={cn('hidden lg:block', sidebarCollapsed && 'lg:hidden')}>
          <DocumentSidebar
            documents={documents}
            isLoading={documentsQuery.isLoading}
            onUploadClick={handleUploadClick}
          />
        </div>

        {/* Main content */}
        <main className="flex flex-1 flex-col overflow-hidden">
          {documentId ? (
            <DocumentWorkspace
              documentId={documentId}
              onDelete={handleDeleteDocument}
            />
          ) : showUploadOverlay ? (
            <div className="flex h-full flex-col items-center justify-center px-6">
              <div className="w-full max-w-lg space-y-4">
                <h2 className="text-lg font-semibold text-white/80">Upload a document</h2>
                <UploadDropzone isUploading={uploadMutation.isPending} onUpload={handleUpload} />
                {uploadMutation.isError && (
                  <p className="text-sm text-rose-300">{getApiErrorMessage(uploadMutation.error)}</p>
                )}
                <button
                  type="button"
                  className="text-xs text-white/40 transition hover:text-white/60"
                  onClick={() => navigate('/')}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <HomeEmptyState onUploadClick={handleUploadClick} />
          )}
        </main>
      </div>

      <AuthGateModal />

      <ConfirmDialog
        isOpen={deleteDialogOpen}
        title="Delete document?"
        message="This will permanently delete the document and all its indexed chunks. This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        isDangerous
        onConfirm={() => void handleConfirmDelete()}
        onCancel={() => {
          setDeleteDialogOpen(false)
          setPendingDeleteId(null)
        }}
      />
    </div>
  )
}
