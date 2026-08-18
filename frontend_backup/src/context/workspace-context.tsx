import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { DocumentResponse, SourceReference } from '@/types'

type PendingIntent =
  | { type: 'upload' }
  | { type: 'ask'; draft: string; documentId?: string }
  | null

interface WorkspaceContextValue {
  /** Currently selected document in the workspace */
  activeDocument: DocumentResponse | null
  setActiveDocument: (doc: DocumentResponse | null) => void

  /** Selected citation source for cross-pane coordination */
  selectedSource: SourceReference | null
  setSelectedSource: (source: SourceReference | null) => void

  /** All sources from the latest answer */
  sources: SourceReference[]
  setSources: (sources: SourceReference[]) => void

  /** Sidebar collapsed state */
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void

  /** Mobile source pane open */
  sourcePaneOpen: boolean
  setSourcePaneOpen: (open: boolean) => void

  /** Auth gate */
  authGateOpen: boolean
  setAuthGateOpen: (open: boolean) => void
  pendingIntent: PendingIntent
  setPendingIntent: (intent: PendingIntent) => void
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined)

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [activeDocument, setActiveDocument] = useState<DocumentResponse | null>(null)
  const [selectedSource, setSelectedSource] = useState<SourceReference | null>(null)
  const [sources, setSources] = useState<SourceReference[]>([])
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sourcePaneOpen, setSourcePaneOpen] = useState(false)
  const [authGateOpen, setAuthGateOpen] = useState(false)
  const [pendingIntent, setPendingIntent] = useState<PendingIntent>(null)

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      activeDocument,
      setActiveDocument,
      selectedSource,
      setSelectedSource,
      sources,
      setSources,
      sidebarCollapsed,
      setSidebarCollapsed,
      sourcePaneOpen,
      setSourcePaneOpen,
      authGateOpen,
      setAuthGateOpen,
      pendingIntent,
      setPendingIntent,
    }),
    [activeDocument, selectedSource, sources, sidebarCollapsed, sourcePaneOpen, authGateOpen, pendingIntent],
  )

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext)
  if (!context) {
    throw new Error('useWorkspace must be used within WorkspaceProvider')
  }
  return context
}
