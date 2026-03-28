import { UploadCloud } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { cn } from '@/lib/utils'

interface UploadDropzoneProps {
  isUploading?: boolean
  onUpload: (file: File) => Promise<void>
}

export function UploadDropzone({ isUploading = false, onUpload }: UploadDropzoneProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: undefined,
    disabled: isUploading,
    maxFiles: 1,
    multiple: false,
    onDrop: async (files) => {
      const file = files[0]
      if (file) {
        await onUpload(file)
      }
    },
  })

  return (
    <div
      {...getRootProps()}
      className={cn(
        'group cursor-pointer rounded-3xl border border-dashed p-6 transition',
        isDragActive
          ? 'border-primary/50 bg-primary/10'
          : 'border-outline-variant/20 bg-surface-container-low/80 hover:border-primary/30 hover:bg-surface-container',
        isUploading && 'cursor-wait opacity-70',
      )}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <UploadCloud className="h-6 w-6" />
          </div>
          <div>
            <p className="text-base font-semibold text-on-surface">
              {isDragActive ? 'Drop your file here' : 'Drag and drop a document'}
            </p>
            <p className="mt-1 text-sm text-on-surface-variant">
              PDF, DOCX, XLSX, CSV, images, and text files are supported.
            </p>
          </div>
        </div>
        <div className="rounded-full border border-outline-variant/15 bg-surface-container-high px-4 py-2 text-xs uppercase tracking-[0.22em] text-on-surface-variant">
          {isUploading ? 'Uploading' : 'Click or drop to upload'}
        </div>
      </div>
    </div>
  )
}
