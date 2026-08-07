import { useCallback, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/context/auth-context'
import { useWorkspace } from '@/context/workspace-context'
import { listDocuments, uploadDocument, getApiErrorMessage } from '@/lib/api'
import { WorkspaceNavbar } from '@/components/WorkspaceNavbar'
import { DocumentSidebar } from '@/components/DocumentSidebar'
import { AuthGateModal } from '@/components/AuthGateModal'
import { HomeEmptyState } from '@/components/HomeEmptyState'
import { DocumentWorkspace } from '@/components/DocumentWorkspace'
import { UploadDropzone } from '@/components/UploadDropzone'
import { cn } from '@/lib/utils'

export function WorkspaceShell() {
  const navigate = useNavigate()
  const { documentId } = useParams<{ documentId: string }>()
  const { isAuthenticated } = useAuth()
  const queryClient = useQueryClient()
  const { sidebarCollapsed, authGateOpen, setAuthGateOpen, pendingIntent, setPendingIntent } = useWorkspace()

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

  // Handle upload click - gate behind auth if not authenticated
  const handleUploadClick = useCallback(() => {
    if (!isAuthenticated) {
      setPendingIntent({ type: 'upload' })
      setAuthGateOpen(true)
      return
    }
    // If authenticated, trigger file input (handled by dropzone in the content area)
    // Navigate to home with upload=true param to show dropzone
    navigate('/?upload=true')
  }, [isAuthenticated, setPendingIntent, setAuthGateOpen, navigate])

  // Resume intent after auth
  useEffect(() => {
    if (isAuthenticated && pendingIntent && !authGateOpen) {
      if (pendingIntent.type === 'upload') {
        navigate('/?upload=true')
      }
      setPendingIntent(null)
    }
  }, [isAuthenticated, pendingIntent, authGateOpen, navigate, setPendingIntent])

  const handleUpload = async (file: File) => {
    try {
      await uploadMutation.mutateAsync(file)
    } catch (error) {
      // Let it throw so UploadDropzone shows error state
      throw error
    }
  }

  // Determine what content to render
  const showUploadOverlay = !documentId && isAuthenticated && (new URLSearchParams(window.location.search).get('upload') === 'true')

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
            <DocumentWorkspace documentId={documentId} />
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
    </div>
  )
}
