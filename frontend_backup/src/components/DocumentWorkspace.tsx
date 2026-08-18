import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { ArrowLeft, FileText, Loader2 } from 'lucide-react'
import { v4 as uuidv4 } from 'uuid'
import {
  generateMindmap,
  generateQuiz,
  getApiErrorMessage,
  getDocument,
  getDocumentFileUrl,
  getQueryHistory,
  getTaskStatus,
  sendQuery,
  summarizeDocument,
} from '@/lib/api'
import { historyToMessages, responseToAssistantMessage } from '@/lib/threads'
import { useWorkspace } from '@/context/workspace-context'
import { ChatPanel } from '@/components/ChatPanel'
import { PdfViewer } from '@/components/PdfViewer'
import { MarkdownContent, QuizView, MindmapView } from '@/components/ContentRenderers'
import { formatBytes, formatStatus } from '@/lib/format'
import type { ChatMessage, WorkspaceTab } from '@/types'
import { cn } from '@/lib/utils'

const STORAGE_PREFIX = 'insightdocs:document-thread:'

interface DocumentWorkspaceProps {
  documentId: string
  onDelete?: (documentId: string) => void
}

export function DocumentWorkspace({ documentId, onDelete }: DocumentWorkspaceProps) {
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { setActiveDocument, selectedSource, setSelectedSource, sources, setSources, sourcePaneOpen, setSourcePaneOpen } = useWorkspace()

  const [conversationId, setConversationId] = useState<string | null>(() => {
    return searchParams.get('conversationId') ?? window.localStorage.getItem(`${STORAGE_PREFIX}${documentId}`) ?? null
  })
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [topK, setTopK] = useState(5)
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('ask')
  const [summary, setSummary] = useState<string | null>(null)
  const [quiz, setQuiz] = useState<unknown>(null)
  const [mindmap, setMindmap] = useState<unknown>(null)
  const [isQuerying, setIsQuerying] = useState(false)

  // Document query
  const documentQuery = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => getDocument(documentId),
    enabled: Boolean(documentId),
  })

  // Task status (processing)
  const taskId = searchParams.get('task')
  const taskQuery = useQuery({
    queryKey: ['task-status', taskId],
    queryFn: () => getTaskStatus(taskId!),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'pending' || status === 'processing' ? 4000 : false
    },
  })

  // Conversation history
  const historyQuery = useQuery({
    queryKey: ['conversation-history', conversationId],
    queryFn: () => getQueryHistory(conversationId),
    enabled: Boolean(conversationId),
    staleTime: 0,
  })

  // PDF
  const isPdf = documentQuery.data?.file_type?.toLowerCase() === '.pdf'
  const isReady = documentQuery.data?.status === 'completed'
  const fileUrlQuery = useQuery({
    queryKey: ['document-file-url', documentId],
    queryFn: () => getDocumentFileUrl(documentId),
    enabled: Boolean(documentId) && isPdf && isReady,
    staleTime: 8 * 60 * 1000,
  })

  // Sync active document to workspace context
  useEffect(() => {
    if (documentQuery.data) {
      setActiveDocument(documentQuery.data)
    }
    return () => setActiveDocument(null)
  }, [documentQuery.data, setActiveDocument])

  // Sync history to messages
  useEffect(() => {
    if (historyQuery.data) {
      setMessages(historyToMessages(historyQuery.data.queries))
    }
  }, [historyQuery.data])

  // Persist conversation mapping
  useEffect(() => {
    if (conversationId) {
      window.localStorage.setItem(`${STORAGE_PREFIX}${documentId}`, conversationId)
    }
  }, [conversationId, documentId])

  // Mutations
  const summaryMutation = useMutation({
    mutationFn: () => summarizeDocument(documentId),
    onSuccess: (r) => { setSummary(r.summary); setActiveTab('summary') },
  })
  const quizMutation = useMutation({
    mutationFn: () => generateQuiz(documentId),
    onSuccess: (r) => { setQuiz(r.quiz); setActiveTab('quiz') },
  })
  const mindmapMutation = useMutation({
    mutationFn: () => generateMindmap(documentId),
    onSuccess: (r) => { setMindmap(r.mindmap); setActiveTab('mindmap') },
  })

  const handleSend = async (queryText: string) => {
    const userMessage: ChatMessage = {
      id: `user-${uuidv4()}`,
      role: 'user',
      content: queryText,
      timestamp: new Date().toISOString(),
    }
    setMessages((m) => [...m, userMessage])
    setIsQuerying(true)

    try {
      const response = await sendQuery({
        query: queryText,
        top_k: topK,
        conversation_id: conversationId ?? undefined,
        document_id: documentId,
      })
      setConversationId(response.conversation_id)
      setMessages((m) => [...m.filter((msg) => msg.id !== userMessage.id), userMessage, responseToAssistantMessage(response)])
      setSources(response.sources)
      setSelectedSource(response.sources[0] ?? null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['query-history'] }),
        queryClient.invalidateQueries({ queryKey: ['conversation-history', response.conversation_id] }),
      ])
    } catch (error) {
      setMessages((m) => [
        ...m,
        { id: `error-${uuidv4()}`, role: 'assistant', content: getApiErrorMessage(error), timestamp: new Date().toISOString() },
      ])
    } finally {
      setIsQuerying(false)
    }
  }

  const currentDoc = documentQuery.data ?? null
  const taskProgress = taskQuery.data?.progress ?? 0

  if (documentQuery.isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-300">
          Unable to load document. {getApiErrorMessage(documentQuery.error)}
        </div>
      </div>
    )
  }

  const tabs: Array<{ key: WorkspaceTab; label: string }> = [
    { key: 'ask', label: 'Ask' },
    { key: 'summary', label: 'Summary' },
    { key: 'quiz', label: 'Quiz' },
    { key: 'mindmap', label: 'Mind map' },
  ]

  return (
    <div className="flex h-full flex-col lg:flex-row">
      {/* Left pane: Answer / Chat / Tools */}
      <div className={cn('flex flex-1 flex-col overflow-hidden border-r border-white/[0.06]', sourcePaneOpen && 'hidden lg:flex')}>
        {/* Document header */}
        <div className="flex items-center gap-3 border-b border-white/[0.06] px-4 py-2.5">
          <FileText className="h-4 w-4 text-white/30" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white/80">
              {currentDoc?.filename ?? 'Loading...'}
            </p>
            <div className="flex items-center gap-2 text-[11px] text-white/30">
              {currentDoc && (
                <>
                  <span>{formatStatus(currentDoc.status)}</span>
                  <span>·</span>
                  <span>{formatBytes(currentDoc.file_size)}</span>
                </>
              )}
            </div>
          </div>

          {/* Tabs - visible at all sizes, scrollable on mobile */}
          <div className="flex items-center gap-1 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={cn(
                  'shrink-0 rounded-md px-2.5 py-1 text-xs transition',
                  activeTab === tab.key
                    ? 'bg-sky-500/15 text-sky-300'
                    : 'text-white/40 hover:bg-white/[0.04] hover:text-white/60',
                )}
                onClick={() => {
                  setActiveTab(tab.key)
                  if (tab.key === 'summary' && !summary) void summaryMutation.mutateAsync()
                  if (tab.key === 'quiz' && !quiz) void quizMutation.mutateAsync()
                  if (tab.key === 'mindmap' && !mindmap) void mindmapMutation.mutateAsync()
                }}
              >
                {tab.label}
              </button>
            ))}
            {onDelete && (
              <button
                type="button"
                className="ml-auto shrink-0 rounded-md px-2 py-1 text-xs text-rose-400/60 transition hover:bg-rose-500/10 hover:text-rose-300"
                onClick={() => onDelete(documentId)}
              >
                Delete
              </button>
            )}
          </div>
        </div>

        {/* Processing banner */}
        {!isReady && taskId && (
          <div className="border-b border-amber-500/20 bg-amber-500/5 px-4 py-2">
            <div className="flex items-center justify-between text-xs text-amber-300">
              <span>Processing document...</span>
              <span>{Math.round(taskProgress * 100)}%</span>
            </div>
            <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-amber-500/15">
              <div
                className="h-full rounded-full bg-amber-400 transition-all"
                style={{ width: `${Math.max(3, taskProgress * 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Mobile: show sources button when sources exist */}
        {selectedSource && !sourcePaneOpen && (
          <div className="flex items-center justify-end border-b border-white/[0.06] px-4 py-1.5 lg:hidden">
            <button
              type="button"
              className="rounded-md bg-sky-500/10 px-2.5 py-1 text-[11px] font-medium text-sky-300 transition hover:bg-sky-500/20"
              onClick={() => setSourcePaneOpen(true)}
            >
              View sources ({sources.length})
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'ask' ? (
            <ChatPanel
              conversationId={conversationId}
              isSending={isQuerying}
              messages={messages}
              onSubmit={handleSend}
              onTopKChange={setTopK}
              placeholder="Ask about this document..."
              subtitle={isReady ? undefined : 'Document is still processing.'}
              title={currentDoc?.filename ?? 'Document'}
              topK={topK}
            />
          ) : (
            <div className="h-full overflow-y-auto p-5">
              {(summaryMutation.isPending || quizMutation.isPending || mindmapMutation.isPending) ? (
                <div className="flex items-center gap-2 text-sm text-white/40">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </div>
              ) : (
                <div className="prose-invert max-w-none">
                  {activeTab === 'summary' && summary && <MarkdownContent content={summary} />}
                  {activeTab === 'quiz' && quiz != null && <QuizView data={quiz} />}
                  {activeTab === 'mindmap' && mindmap != null && <MindmapView data={mindmap} />}
                  {activeTab === 'summary' && !summary && <p className="text-sm text-white/40">Click Summary to generate.</p>}
                  {activeTab === 'quiz' && !quiz && <p className="text-sm text-white/40">Click Quiz to generate.</p>}
                  {activeTab === 'mindmap' && !mindmap && <p className="text-sm text-white/40">Click Mind map to generate.</p>}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right pane: Evidence / PDF */}
      <div className={cn('flex flex-1 flex-col overflow-hidden bg-[hsl(227,22%,6%)]', !sourcePaneOpen && 'hidden lg:flex')}>
        {/* Mobile back button */}
        <div className="flex items-center gap-2 border-b border-white/[0.06] px-3 py-2 lg:hidden">
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-white/50 transition hover:bg-white/[0.06] hover:text-white/70"
            onClick={() => setSourcePaneOpen(false)}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to answer
          </button>
        </div>

        {/* Source detail */}
        {selectedSource && (
          <div className="border-b border-white/[0.06] px-4 py-2.5">
            <p className="text-[11px] font-medium text-white/30">Source</p>
            <p className="mt-0.5 text-sm text-white/70">{selectedSource.citation_label}</p>
            <div className="mt-1 flex items-center gap-2 text-[11px] text-white/30">
              <span>Page {selectedSource.page_number ?? '-'}</span>
              <span>·</span>
              <span>Score {(selectedSource.similarity_score * 100).toFixed(0)}%</span>
            </div>
          </div>
        )}

        {/* PDF viewer */}
        <div className="flex-1 overflow-auto p-3">
          {fileUrlQuery.data?.url ? (
            <PdfViewer
              fileUrl={fileUrlQuery.data.url}
              pageNumber={selectedSource?.page_number ?? undefined}
              highlightBbox={selectedSource?.bbox ?? null}
            />
          ) : isPdf && !isReady ? (
            <div className="flex h-full items-center justify-center text-sm text-white/30">
              PDF will be available after processing completes.
            </div>
          ) : isPdf ? (
            <div className="flex h-full items-center justify-center text-sm text-white/30">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading document...
            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-white/30">
              Preview is available for PDF documents. Ask a question to see cited evidence.
            </div>
          )}
        </div>

        {/* Source list */}
        {selectedSource && (
          <SourceList />
        )}
      </div>
    </div>
  )
}

function SourceList() {
  const { sources, selectedSource, setSelectedSource, setSourcePaneOpen } = useWorkspace()

  if (sources.length === 0) return null

  return (
    <div className="border-t border-white/[0.06] overflow-y-auto max-h-60 px-3 py-2">
      <p className="px-1 text-[11px] font-medium text-white/30">
        All sources ({sources.length})
      </p>
      <div className="mt-1.5 space-y-1.5">
        {sources.map((source) => (
          <button
            key={source.chunk_id}
            type="button"
            className={cn(
              'w-full rounded-lg border p-2.5 text-left transition',
              selectedSource?.chunk_id === source.chunk_id
                ? 'border-sky-500/30 bg-sky-500/10'
                : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]',
            )}
            onClick={() => {
              setSelectedSource(source)
              setSourcePaneOpen(true)
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <p className={cn(
                'text-xs font-medium',
                selectedSource?.chunk_id === source.chunk_id ? 'text-sky-300' : 'text-white/60',
              )}>
                {source.citation_label}
              </p>
              <span className="shrink-0 rounded bg-white/[0.06] px-1.5 py-0.5 text-[10px] text-white/30">
                {(source.similarity_score * 100).toFixed(0)}%
              </span>
            </div>
            {source.section_title && (
              <p className="mt-0.5 text-[10px] text-white/25">Section: {source.section_title}</p>
            )}
            <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-white/40">
              {source.content_preview}
            </p>
          </button>
        ))}
      </div>
    </div>
  )
}
