import { useState } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { DocumentLibraryView } from './components/DocumentLibraryView'
import { AuditAssistantView } from './components/AuditAssistantView'
import { ByokConfigView } from './components/ByokConfigView'
import { ChatHistoryView } from './components/ChatHistoryView'
import { SettingsView } from './components/SettingsView'
import { HelpView } from './components/HelpView'
import { AuthModal } from './components/AuthModal'
import { ShaderCanvas } from './components/ShaderCanvas'
import { useAuth } from '@/context/auth-context'
import { listDocuments, getByokStatus } from '@/lib/api'
import type { NavView, ByokConfig } from './types'

export default function App() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [searchQuery, setSearchQuery] = useState('')
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Real document count for sidebar
  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    enabled: isAuthenticated,
    staleTime: 30_000,
  })

  // Real BYOK status for topbar indicator
  const byokQuery = useQuery({
    queryKey: ['byok-status'],
    queryFn: getByokStatus,
    enabled: isAuthenticated,
    staleTime: 60_000,
  })

  const documentsCount = documentsQuery.data?.documents?.length ?? 0
  const byokConfig: ByokConfig = {
    enabled: byokQuery.data?.byok_enabled ?? false,
    apiKey: '',
    selectedModel: byokQuery.data?.active_model ?? '',
    connectionStatus: (byokQuery.data?.status === 'healthy' || byokQuery.data?.status === 'degraded') ? 'healthy' : byokQuery.data?.status === 'missing' ? 'untested' : 'error',
    pingMs: 0,
    temperature: 0.2,
    maxTokens: 4096,
    strictness: 'balanced',
    autoAuditOnUpload: false,
  }

  // Derive current nav view from URL
  const getNavView = (): NavView => {
    if (location.pathname.startsWith('/documents/')) return 'audit'
    if (location.pathname === '/settings') return 'settings'
    if (location.pathname === '/byok') return 'byok'
    if (location.pathname === '/history') return 'chat-history'
    if (location.pathname === '/help') return 'help'
    return 'documents'
  }

  const handleNavigate = (view: NavView) => {
    setIsMobileMenuOpen(false)
    switch (view) {
      case 'documents': navigate('/'); break
      case 'settings': navigate('/settings'); break
      case 'byok': navigate('/byok'); break
      case 'chat-history': navigate('/history'); break
      case 'help': navigate('/help'); break
      default: navigate('/')
    }
  }

  const handleSignOut = () => {
    logout()
    navigate('/')
  }

  // Gate protected actions behind auth
  const requireAuth = (action: () => void) => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true)
      return
    }
    action()
  }

  const userSession = isAuthenticated
    ? { isAuthenticated: true, email: user?.email || '', name: user?.name || '', role: user?.role || '', avatar: '' }
    : { isAuthenticated: false, email: '', name: 'Guest', role: 'Guest', avatar: '' }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#09090b] text-white selection:bg-[#ffcc00] selection:text-black relative font-sans">
      <ShaderCanvas />

      <Sidebar
        currentView={getNavView()}
        onNavigate={handleNavigate}
        onNewAnalysis={() => requireAuth(() => navigate('/'))}
        user={userSession}
        onSignOut={handleSignOut}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        documentsCount={documentsCount}
        isOpenMobile={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      <div className="flex-1 flex flex-col h-screen overflow-hidden min-w-0 md:ml-[280px] relative">
        <TopBar
          currentView={getNavView()}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          byokConfig={byokConfig}
          user={userSession}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        />

        <main className="flex-1 flex overflow-hidden pt-16">
          <Routes>
            <Route path="/" element={<DocumentLibraryView searchQuery={searchQuery} onRequireAuth={() => setIsAuthModalOpen(true)} />} />
            <Route path="/documents/:documentId" element={isAuthenticated ? <AuditAssistantView /> : <Navigate to="/" replace />} />
            <Route path="/settings" element={isAuthenticated ? <SettingsView /> : <Navigate to="/" replace />} />
            <Route path="/byok" element={isAuthenticated ? <ByokConfigView /> : <Navigate to="/" replace />} />
            <Route path="/history" element={isAuthenticated ? <ChatHistoryView /> : <Navigate to="/" replace />} />
            <Route path="/help" element={<HelpView />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </div>
  )
}
