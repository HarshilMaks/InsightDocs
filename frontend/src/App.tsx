import { lazy, Suspense, useState, type ReactNode } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import { Skeleton } from '@/components/ui/skeleton'
import { AppSidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { DocumentLibraryView } from './components/DocumentLibraryView'
import { AuthModal } from './components/AuthModal'
import { useAuth } from '@/context/auth-context'

// The workspace pulls in react-pdf and the markdown renderer, so it is loaded
// on demand rather than in the initial bundle.
const AuditAssistantView = lazy(() =>
  import('./components/AuditAssistantView').then((m) => ({ default: m.AuditAssistantView })),
)
const ByokConfigView = lazy(() =>
  import('./components/ByokConfigView').then((m) => ({ default: m.ByokConfigView })),
)
const ChatHistoryView = lazy(() =>
  import('./components/ChatHistoryView').then((m) => ({ default: m.ChatHistoryView })),
)
const EvidenceWorkspaceListView = lazy(() =>
  import('./components/EvidenceWorkspaceViews').then((m) => ({ default: m.EvidenceWorkspaceListView })),
)
const EvidenceWorkspaceDetailView = lazy(() =>
  import('./components/EvidenceWorkspaceViews').then((m) => ({ default: m.EvidenceWorkspaceDetailView })),
)
const ReviewerQueueView = lazy(() =>
  import('./components/ReviewerViews').then((m) => ({ default: m.ReviewerQueueView })),
)
const ReviewerDetailView = lazy(() =>
  import('./components/ReviewerViews').then((m) => ({ default: m.ReviewerDetailView })),
)
const SettingsView = lazy(() =>
  import('./components/SettingsView').then((m) => ({ default: m.SettingsView })),
)
const HelpView = lazy(() => import('./components/HelpView').then((m) => ({ default: m.HelpView })))

/** Scroll container for standard pages. The workspace manages its own panes. */
function Scrollable({ children }: { children: ReactNode }) {
  return <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
}

function RouteFallback() {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 p-4 md:p-6">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-4 w-80" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-32 w-full" />
    </div>
  )
}

export default function App() {
  const { isAuthenticated } = useAuth()
  const [searchQuery, setSearchQuery] = useState('')
  const [isAuthOpen, setIsAuthOpen] = useState(false)

  const openAuth = () => setIsAuthOpen(true)

  /** Signed-out visitors are sent home, where the auth dialog can be opened. */
  const guarded = (element: ReactNode) => (isAuthenticated ? element : <Navigate to="/" replace />)

  return (
    <TooltipProvider>
      <div aria-hidden="true" className="app-animated-backdrop" />
      <SidebarProvider className="relative z-10 h-svh overflow-hidden bg-transparent">
        <AppSidebar onRequireAuth={openAuth} />

        <SidebarInset className="min-w-0 overflow-hidden bg-background/88 backdrop-blur-sm">
          <TopBar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onRequireAuth={openAuth}
          />

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <Suspense fallback={<RouteFallback />}>
              <Routes>
                <Route
                  path="/"
                  element={
                    <Scrollable>
                      <DocumentLibraryView searchQuery={searchQuery} onRequireAuth={openAuth} />
                    </Scrollable>
                  }
                />
                <Route path="/documents/:documentId" element={guarded(<AuditAssistantView />)} />
                <Route
                  path="/byok"
                  element={guarded(
                    <Scrollable>
                      <ByokConfigView />
                    </Scrollable>,
                  )}
                />
                <Route
                  path="/workspaces"
                  element={guarded(
                    <Scrollable>
                      <EvidenceWorkspaceListView />
                    </Scrollable>,
                  )}
                />
                <Route path="/workspaces/:workspaceId" element={guarded(<EvidenceWorkspaceDetailView />)} />
                <Route
                  path="/history"
                  element={guarded(
                    <Scrollable>
                      <ChatHistoryView />
                    </Scrollable>,
                  )}
                />
                <Route
                  path="/review"
                  element={guarded(
                    <Scrollable>
                      <ReviewerQueueView />
                    </Scrollable>,
                  )}
                />
                <Route
                  path="/review/:runId"
                  element={guarded(
                    <Scrollable>
                      <ReviewerDetailView />
                    </Scrollable>,
                  )}
                />
                <Route
                  path="/settings"
                  element={guarded(
                    <Scrollable>
                      <SettingsView />
                    </Scrollable>,
                  )}
                />
                <Route
                  path="/help"
                  element={
                    <Scrollable>
                      <HelpView />
                    </Scrollable>
                  }
                />
                {/* Legacy paths from the previous frontend */}
                <Route path="/dashboard" element={<Navigate to="/" replace />} />
                <Route path="/login" element={<Navigate to="/" replace />} />
                <Route path="/register" element={<Navigate to="/" replace />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </div>
        </SidebarInset>
      </SidebarProvider>

      <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />
      <Toaster position="bottom-right" theme="dark" />
    </TooltipProvider>
  )
}
