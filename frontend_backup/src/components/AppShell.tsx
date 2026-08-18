import { useMemo, useState } from 'react'
import { Outlet, matchPath, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Menu, X } from 'lucide-react'
import { getQueryHistory, listDocuments } from '@/lib/api'
import { buildThreadSummaries } from '@/lib/threads'
import type { WorkspaceOutletContext } from '@/types'
import { Navbar } from './Navbar'
import { Sidebar } from './Sidebar'

export function AppShell() {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    staleTime: 30_000,
  })

  const historyQuery = useQuery({
    queryKey: ['query-history'],
    queryFn: () => getQueryHistory(),
    staleTime: 30_000,
  })

  const documents = documentsQuery.data?.documents ?? []
  const threads = useMemo(
    () => buildThreadSummaries(historyQuery.data?.queries ?? []),
    [historyQuery.data],
  )

  const activeDocumentId = matchPath('/documents/:documentId', location.pathname)?.params
    .documentId
  const activeConversationId = matchPath('/conversations/:conversationId', location.pathname)?.params
    .conversationId

  const context: WorkspaceOutletContext = {
    documents,
    threads,
    documentsLoading: documentsQuery.isLoading,
    threadsLoading: historyQuery.isLoading,
  }

  const isLoading = documentsQuery.isLoading && historyQuery.isLoading

  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Mobile menu button */}
      <button
        className="fixed left-4 top-[4.5rem] z-50 flex h-10 w-10 items-center justify-center rounded-xl border border-outline-variant/15 bg-surface-container-low shadow-lg lg:hidden"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        type="button"
        aria-label="Toggle navigation"
      >
        {mobileMenuOpen ? <X className="h-5 w-5 text-on-surface" /> : <Menu className="h-5 w-5 text-on-surface" />}
      </button>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar — mobile: overlay drawer, desktop: static */}
      <div className={`fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] w-72 transform transition-transform duration-200 lg:translate-x-0 ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <Sidebar
          activeConversationId={activeConversationId}
          activeDocumentId={activeDocumentId}
          documents={documents}
          documentsLoading={documentsQuery.isLoading}
          threads={threads}
          threadsLoading={historyQuery.isLoading}
        />
      </div>

      <main className="min-h-screen pt-20 lg:pl-72">
        <div className="px-4 pb-10 sm:px-6 lg:px-8">
          {isLoading ? (
            <div className="space-y-6">
              <div className="h-32 animate-pulse rounded-[2rem] bg-surface-container-high/30" />
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-28 animate-pulse rounded-3xl bg-surface-container-high/30" />
                ))}
              </div>
              <div className="h-64 animate-pulse rounded-[2rem] bg-surface-container-high/30" />
            </div>
          ) : (
            <Outlet context={context} />
          )}
        </div>
      </main>
    </div>
  )
}
