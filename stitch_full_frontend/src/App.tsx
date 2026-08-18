import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { DocumentLibraryView } from './components/DocumentLibraryView';
import { AuditAssistantView } from './components/AuditAssistantView';
import { ByokConfigView } from './components/ByokConfigView';
import { ChatHistoryView } from './components/ChatHistoryView';
import { SettingsView } from './components/SettingsView';
import { HelpView } from './components/HelpView';
import { AuthModal } from './components/AuthModal';
import { UploadModal } from './components/UploadModal';
import { NewAnalysisModal } from './components/NewAnalysisModal';
import { ShaderCanvas } from './components/ShaderCanvas';
import { INITIAL_DOCUMENTS, INITIAL_AUDIT_SESSIONS } from './data/mockDocuments';
import { DocumentItem, NavView, ByokConfig, UserSession, AuditSession } from './types';

export default function App() {
  const [currentView, setCurrentView] = useState<NavView>('documents');
  const [documents, setDocuments] = useState<DocumentItem[]>(() => {
    const saved = localStorage.getItem('insightdocs_documents');
    return saved ? JSON.parse(saved) : INITIAL_DOCUMENTS;
  });
  const [selectedDocument, setSelectedDocument] = useState<DocumentItem>(INITIAL_DOCUMENTS[0]);
  const [auditSessions, setAuditSessions] = useState<AuditSession[]>(() => {
    const saved = localStorage.getItem('insightdocs_sessions');
    return saved ? JSON.parse(saved) : INITIAL_AUDIT_SESSIONS;
  });
  const [searchQuery, setSearchQuery] = useState('');
  
  // BYOK configuration state with persistence
  const [byokConfig, setByokConfig] = useState<ByokConfig>(() => {
    const saved = localStorage.getItem('insightdocs_byok_config');
    return saved
      ? JSON.parse(saved)
      : {
          enabled: false,
          apiKey: '',
          selectedModel: 'gemini-3.7-flash',
          connectionStatus: 'healthy',
          pingMs: 23,
          temperature: 0.2,
          maxTokens: 4096,
          strictness: 'balanced',
          autoAuditOnUpload: true,
        };
  });

  // User session state
  const [userSession, setUserSession] = useState<UserSession>(() => {
    const saved = localStorage.getItem('insightdocs_user');
    return saved
      ? JSON.parse(saved)
      : {
          isAuthenticated: true,
          email: 'alex.vance@insightdocs.ai',
          name: 'Alex Vance',
          role: 'Lead Financial Auditor',
          avatar: '',
        };
  });

  // Modal open states
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isNewAnalysisModalOpen, setIsNewAnalysisModalOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Sync to local storage
  useEffect(() => {
    localStorage.setItem('insightdocs_documents', JSON.stringify(documents));
  }, [documents]);

  useEffect(() => {
    localStorage.setItem('insightdocs_sessions', JSON.stringify(auditSessions));
  }, [auditSessions]);

  useEffect(() => {
    localStorage.setItem('insightdocs_byok_config', JSON.stringify(byokConfig));
  }, [byokConfig]);

  useEffect(() => {
    localStorage.setItem('insightdocs_user', JSON.stringify(userSession));
  }, [userSession]);

  // Handle document upload
  const handleAddNewDocument = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase() || 'pdf';
    let type: DocumentItem['type'] = 'pdf';
    let typeLabel = 'PDF Document';

    if (ext === 'docx') {
      type = 'docx';
      typeLabel = 'Word Document';
    } else if (ext === 'zip') {
      type = 'zip';
      typeLabel = 'Archive';
    } else if (ext === 'txt') {
      type = 'txt';
      typeLabel = 'Text Document';
    } else if (ext === 'xlsx' || ext === 'csv') {
      type = 'xlsx';
      typeLabel = 'Spreadsheet';
    }

    const newDoc: DocumentItem = {
      id: `doc-${Date.now()}`,
      name: file.name,
      type,
      typeLabel,
      size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
      status: 'Completed',
      uploadDate: 'Just now',
      pages: 4,
      claimsCount: 2,
      flaggedCount: 0,
      contentSummary: `Uploaded audit artifact ${file.name}. Parsed with zero-knowledge neural vector indexing.`,
      documentPages: [
        {
          pageNumber: 1,
          title: file.name.toUpperCase(),
          content: `Automated neural extraction for uploaded document: ${file.name}.\n\nContains verified institutional claims, metrics, and audit checkpoints.`,
          highlights: [
            {
              id: `hl-${Date.now()}`,
              label: 'AI EXTRACTED CLAIM',
              text: `Extracted verification checkpoint for ${file.name}. All key figures and citations have been cross-checked.`,
              type: 'claim',
              claimId: '01',
            },
          ],
        },
      ],
    };

    setDocuments((prev) => [newDoc, ...prev]);
    setSelectedDocument(newDoc);
    setIsUploadModalOpen(false);
  };

  const handleDeleteDocument = (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    if (selectedDocument?.id === id) {
      const remaining = documents.filter((d) => d.id !== id);
      if (remaining.length > 0) {
        setSelectedDocument(remaining[0]);
      }
    }
  };

  const handleSelectDocument = (doc: DocumentItem) => {
    setSelectedDocument(doc);
    setCurrentView('audit');
  };

  // Open audit session from chat history
  const handleOpenAuditSession = (session: AuditSession) => {
    const doc = documents.find((d) => d.id === session.documentId) || documents[0];
    setSelectedDocument(doc);
    setCurrentView('audit');
  };

  const handleDeleteAuditSession = (id: string) => {
    setAuditSessions((prev) => prev.filter((s) => s.id !== id));
  };

  const handleUpdateByokConfig = (newConfig: Partial<ByokConfig>) => {
    setByokConfig((prev) => ({ ...prev, ...newConfig }));
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#09090b] text-white selection:bg-[#ffcc00] selection:text-black relative font-sans">
      {/* Dynamic WebGL Shader Background */}
      <ShaderCanvas />

      {/* SideNavBar matching exact reference code */}
      <Sidebar
        currentView={currentView}
        onNavigate={(view) => {
          setCurrentView(view);
          setIsMobileMenuOpen(false);
        }}
        onNewAnalysis={() => setIsNewAnalysisModalOpen(true)}
        user={userSession}
        onSignOut={() => setUserSession({ isAuthenticated: false, email: '', name: 'Guest', role: 'Guest', avatar: '' })}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        documentsCount={documents.length}
        isOpenMobile={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden min-w-0 md:ml-[280px] relative">
        {/* TopNavBar */}
        <TopBar
          currentView={currentView}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          byokConfig={byokConfig}
          user={userSession}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        />

        {/* View Switcher with top padding for fixed header */}
        <main className="flex-1 flex overflow-hidden pt-16">
          {currentView === 'documents' && (
            <DocumentLibraryView
              documents={documents}
              searchQuery={searchQuery}
              onSelectDocument={handleSelectDocument}
              onUploadClick={() => setIsUploadModalOpen(true)}
              onDeleteDocument={handleDeleteDocument}
              onAddNewDocument={handleAddNewDocument}
            />
          )}

          {currentView === 'audit' && (
            <AuditAssistantView
              document={selectedDocument}
              onBack={() => setCurrentView('documents')}
              byokConfig={byokConfig}
            />
          )}

          {currentView === 'byok' && (
            <ByokConfigView
              config={byokConfig}
              onUpdateConfig={handleUpdateByokConfig}
            />
          )}

          {currentView === 'chat-history' && (
            <ChatHistoryView
              sessions={auditSessions}
              onOpenSession={handleOpenAuditSession}
              onDeleteSession={handleDeleteAuditSession}
              onNewAnalysis={() => setIsNewAnalysisModalOpen(true)}
            />
          )}

          {currentView === 'settings' && <SettingsView />}

          {currentView === 'help' && <HelpView />}
        </main>
      </div>

      {/* Modals */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onLoginSuccess={(user) => setUserSession(user)}
      />

      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadFile={handleAddNewDocument}
      />

      <NewAnalysisModal
        isOpen={isNewAnalysisModalOpen}
        onClose={() => setIsNewAnalysisModalOpen(false)}
        documents={documents}
        onSelectAndAudit={handleSelectDocument}
        onOpenUpload={() => setIsUploadModalOpen(true)}
      />
    </div>
  );
}
