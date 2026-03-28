import { useEffect, useState } from 'react'

interface ConfirmDialogProps {
  isOpen: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  isDangerous?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDangerous = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const [isVisible, setIsVisible] = useState(isOpen)

  useEffect(() => {
    setIsVisible(isOpen)
  }, [isOpen])

  if (!isVisible) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-outline-variant/15 bg-surface-container px-6 py-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-on-surface">{title}</h2>
        <p className="mt-2 text-sm text-on-surface-variant">{message}</p>

        <div className="mt-6 flex gap-3">
          <button
            className="flex-1 rounded-lg border border-outline-variant/15 bg-surface-container-low px-4 py-2.5 text-sm font-medium text-on-surface transition hover:bg-surface-container-high"
            onClick={() => {
              setIsVisible(false)
              onCancel()
            }}
            type="button"
          >
            {cancelLabel}
          </button>
          <button
            className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-medium text-white transition ${
              isDangerous
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-primary hover:bg-primary/90'
            }`}
            onClick={() => {
              setIsVisible(false)
              onConfirm()
            }}
            type="button"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
