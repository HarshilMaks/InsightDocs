import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, FileSpreadsheet, File, Trash2, Loader2 } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { useAuth } from '@/context/auth-context'
import { listDocuments, uploadDocument, deleteDocument, getApiErrorMessage, type DocumentResponse } from '@/lib/api'

interface DocumentLibraryViewProps {
  searchQuery: string
  onRequireAuth: () => void
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getFileIcon(fileType: string) {
  if (fileType === '.pdf') return <FileText className="w-5 h-5 text-[#ffcc00]" />
  if (fileType === '.docx') return <File className="w-5 h-5 text-blue-400" />
  if (fileType === '.xlsx' || fileType === '.csv') return <FileSpreadsheet className="w-5 h-5 text-green-400" />
  return <File className="w-5 h-5 text-zinc-400" />
}

function getStatusBadge(status: DocumentResponse['status']) {
  switch (status) {
    case 'completed':
      return <span className="inline-flex items-center px-2.5 py-1 text-[11px] font-mono font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">● Completed</span>
    case 'processing':
      return <span className="inline-flex items-center px-2.5 py-1 text-[11px] font-mono font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 animate-pulse">● Processing</span>
    case 'pending':
      return <span className="inline-flex items-center px-2.5 py-1 text-[11px] font-mono font-medium bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">● Pending</span>
    case 'failed':
      return <span className="inline-flex items-center px-2.5 py-1 text-[11px] font-mono font-medium bg-red-500/10 text-red-400 border border-red-500/20">● Failed</span>
    default:
      return null
  }
}

export const DocumentLibraryView: React.FC<DocumentLibraryViewProps> = ({ searchQuery, onRequireAuth }) => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const queryClient = useQueryClient()
  const [uploadError, setUploadError] = useState<string | null>(null)

  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    enabled: isAuthenticated,
    refetchInterval: (query) => {
      const docs = query.state.data?.documents ?? []
      return docs.some((d) => d.status === 'pending' || d.status === 'processing') ? 5000 : false
    },
  })

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
      navigate(`/documents/${response.document_id}?task=${response.task_id}`)
    },
    onError: (err) => {
      setUploadError(getApiErrorMessage(err))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    multiple: false,
    disabled: uploadMutation.isPending,
    onDrop: (files) => {
      if (!isAuthenticated) {
        onRequireAuth()
        return
      }
      const file = files[0]
      if (file) {
        setUploadError(null)
        uploadMutation.mutate(file)
      }
    },
  })

  const documents = documentsQuery.data?.documents ?? []
  const filtered = searchQuery
    ? documents.filter((d) => d.filename.toLowerCase().includes(searchQuery.toLowerCase()))
    : documents

  return (
    <div className="flex-1 overflow-y-auto px-6 pb-6 pt-4">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex justify-between items-end">
          <div>
            <h2 className="text-4xl font-bold text-white tracking-tight" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Document Library
            </h2>
            <p className="text-base text-zinc-400 mt-2 max-w-xl">
              Upload documents and ask questions backed by exact, verifiable evidence.
            </p>
          </div>
        </div>

        {/* Upload Dropzone */}
        <div
          {...getRootProps()}
          className={`relative overflow-hidden border-2 border-dashed p-10 flex flex-col items-center justify-center text-center cursor-pointer glass-panel group retro-grid transition-all duration-300 ${
            isDragActive ? 'border-[#ffcc00] bg-[#ffcc00]/5' : 'border-zinc-700 hover:border-[#ffcc00]/50'
          } ${uploadMutation.isPending ? 'opacity-60 pointer-events-none' : ''}`}
        >
          <input {...getInputProps()} />
          <div className="w-16 h-16 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform border-2 border-zinc-700 group-hover:border-[#ffcc00]/50 bg-zinc-900">
            {uploadMutation.isPending ? (
              <Loader2 className="w-8 h-8 text-[#ffcc00] animate-spin" />
            ) : (
              <Upload className="w-8 h-8 text-zinc-400 group-hover:text-[#ffcc00] transition-colors" />
            )}
          </div>
          <h3 className="font-bold text-white text-lg" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            {uploadMutation.isPending ? 'Uploading...' : isDragActive ? 'Drop your file here' : 'Upload Document'}
          </h3>
          <p className="text-sm text-zinc-400 mt-2">
            Drag & drop .pdf, .docx, .pptx, or .txt (Max 50MB)
          </p>
          {uploadError && (
            <p className="text-sm text-red-400 mt-3 border border-red-500/30 bg-red-500/10 px-3 py-1">{uploadError}</p>
          )}
        </div>

        {/* Document Table */}
        {!isAuthenticated ? (
          <div className="glass-panel border border-zinc-800 p-12 text-center">
            <p className="text-zinc-400 text-lg">Sign in to view and manage your documents.</p>
            <button
              onClick={onRequireAuth}
              className="mt-4 bg-[#ffcc00] text-black font-bold uppercase px-6 py-3 border-4 border-black brutal-shadow hover:bg-[#e6b800] transition-all cursor-pointer"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              Sign In
            </button>
          </div>
        ) : documentsQuery.isLoading ? (
          <div className="glass-panel border border-zinc-800 p-12 text-center">
            <Loader2 className="w-8 h-8 text-[#ffcc00] animate-spin mx-auto" />
            <p className="text-zinc-400 mt-4">Loading documents...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="glass-panel border border-zinc-800 p-12 text-center">
            <p className="text-zinc-400 text-lg">
              {searchQuery ? 'No documents match your search.' : 'No documents yet. Upload one above to get started.'}
            </p>
          </div>
        ) : (
          <div className="glass-panel border border-zinc-800 overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-zinc-800 bg-zinc-900/60 text-[11px] font-mono uppercase tracking-wider text-zinc-500">
              <div className="col-span-5">Filename</div>
              <div className="col-span-2">Type</div>
              <div className="col-span-2">Size</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-1 text-right">Actions</div>
            </div>

            {/* Document rows */}
            <div className="divide-y divide-zinc-800/50">
              {filtered.map((doc) => (
                <div
                  key={doc.id}
                  className="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-white/[0.03] transition-all group cursor-pointer"
                  onClick={() => {
                    if (doc.status === 'completed') navigate(`/documents/${doc.id}`)
                  }}
                >
                  <div className="col-span-5 flex items-center gap-3 overflow-hidden">
                    {getFileIcon(doc.file_type)}
                    <span className="font-semibold text-white truncate group-hover:text-[#ffcc00] transition-colors">
                      {doc.filename}
                    </span>
                  </div>
                  <div className="col-span-2 text-sm text-zinc-400">{doc.file_type.replace('.', '').toUpperCase()}</div>
                  <div className="col-span-2 text-xs font-mono text-zinc-500">{formatBytes(doc.file_size)}</div>
                  <div className="col-span-2">{getStatusBadge(doc.status)}</div>
                  <div className="col-span-1 flex justify-end">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (confirm('Delete this document permanently?')) {
                          deleteMutation.mutate(doc.id)
                        }
                      }}
                      className="p-2 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
