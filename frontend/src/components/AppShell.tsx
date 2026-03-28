import { useMemo } from 'react'
import { Outlet, matchPath, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getQueryHistory, listDocuments } from '@/lib/api'
import { buildThreadSummaries } from '@/lib/threads'
import type { WorkspaceOutletContext } from '@/types'
import { Navbar } from './Navbar'
import { Sidebar } from './Sidebar'

export function AppShell() {
  const location = useLocation()

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

  return (
    <div className="min-h-screen">
      <Navbar />
      <Sidebar
        activeConversationId={activeConversationId}
        activeDocumentId={activeDocumentId}
        documents={documents}
        documentsLoading={documentsQuery.isLoading}
        threads={threads}
        threadsLoading={historyQuery.isLoading}
      />
      <main className="min-h-screen pt-20 lg:pl-72">
        <div className="px-4 pb-10 sm:px-6 lg:px-8">
          <Outlet context={context} />
        </div>
      </main>
    </div>
  )
}
