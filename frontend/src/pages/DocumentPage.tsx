import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { FileText, RefreshCw } from 'lucide-react'
import { v4 as uuidv4 } from 'uuid'
import {
  generateMindmap,
  generateQuiz,
  getApiErrorMessage,
  getDocument,
  getQueryHistory,
  getTaskStatus,
  sendQuery,
  summarizeDocument,
} from '@/lib/api'
import { historyToMessages, responseToAssistantMessage } from '@/lib/threads'
import { ChatPanel } from '@/components/ChatPanel'
import { CitationsPanel } from '@/components/CitationsPanel'
import { formatBytes, formatStatus } from '@/lib/format'
import type { ChatMessage, SourceReference, WorkspaceTab } from '@/types'
import { cn } from '@/lib/utils'

const STORAGE_PREFIX = 'insightdocs:document-thread:'

function renderContent(value: unknown) {
  if (value == null) {
    return 'No content available yet.'
  }

  if (typeof value === 'string') {
    return value
  }

  return JSON.stringify(value, null, 2)
}

export default function DocumentPage() {
  const { documentId } = useParams<{ documentId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const [conversationId, setConversationId] = useState<string | null>(() => {
    if (!documentId || typeof window === 'undefined') {
      return searchParams.get('conversationId')
    }

    return searchParams.get('conversationId') ?? window.localStorage.getItem(`${STORAGE_PREFIX}${documentId}`)
  })
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sources, setSources] = useState<SourceReference[]>([])
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null)
  const [topK, setTopK] = useState(5)
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('ask')
  const [summary, setSummary] = useState<string | null>(null)
  const [quiz, setQuiz] = useState<unknown>(null)
  const [mindmap, setMindmap] = useState<unknown>(null)
  const [isQuerying, setIsQuerying] = useState(false)

  const documentQuery = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => getDocument(documentId ?? ''),
    enabled: Boolean(documentId),
  })

  const taskId = searchParams.get('task')
  const taskQuery = useQuery({
    queryKey: ['task-status', taskId],
    queryFn: () => getTaskStatus(taskId ?? ''),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'pending' || status === 'processing' ? 4000 : false
    },
  })
  const taskStatus = taskQuery.data?.status
  const taskProgress = taskQuery.data?.progress ?? 0

  const historyQuery = useQuery({
    queryKey: ['conversation-history', conversationId],
    queryFn: () => getQueryHistory(conversationId),
    enabled: Boolean(conversationId),
    staleTime: 0,
  })

  useEffect(() => {
    if (!documentId) {
      return
    }

    const stored = searchParams.get('conversationId') ?? window.localStorage.getItem(`${STORAGE_PREFIX}${documentId}`)
    setConversationId(stored)
  }, [documentId, searchParams])

  useEffect(() => {
    if (!historyQuery.data) {
      return
    }

    setMessages(historyToMessages(historyQuery.data.queries))
  }, [historyQuery.data])

  useEffect(() => {
    if (!documentId || !conversationId) {
      return
    }

    window.localStorage.setItem(`${STORAGE_PREFIX}${documentId}`, conversationId)
  }, [conversationId, documentId])

  useEffect(() => {
    if (!conversationId) {
      return
    }

    if (searchParams.get('conversationId') !== conversationId) {
      const nextParams = new URLSearchParams(searchParams)
      nextParams.set('conversationId', conversationId)
      if (taskId) {
        nextParams.set('task', taskId)
      }
      setSearchParams(nextParams, { replace: true })
    }
  }, [conversationId, searchParams, setSearchParams, taskId])

  const summaryMutation = useMutation({
    mutationFn: () => summarizeDocument(documentId ?? ''),
    onSuccess: (response) => {
      setSummary(response.summary)
      setActiveTab('summary')
    },
  })

  const quizMutation = useMutation({
    mutationFn: () => generateQuiz(documentId ?? ''),
    onSuccess: (response) => {
      setQuiz(response.quiz)
      setActiveTab('quiz')
    },
  })

  const mindmapMutation = useMutation({
    mutationFn: () => generateMindmap(documentId ?? ''),
    onSuccess: (response) => {
      setMindmap(response.mindmap)
      setActiveTab('mindmap')
    },
  })

  const handleSend = async (queryText: string) => {
    if (!documentId) {
      return
    }

    const userMessage: ChatMessage = {
      id: `user-${uuidv4()}`,
      role: 'user',
      content: queryText,
      timestamp: new Date().toISOString(),
    }

    setMessages((current) => [...current, userMessage])
    setIsQuerying(true)

    try {
      const response = await sendQuery({
        query: queryText,
        top_k: topK,
        conversation_id: conversationId ?? undefined,
      })

      setConversationId(response.conversation_id)
      setMessages((current) => [...current.filter((message) => message.id !== userMessage.id), userMessage, responseToAssistantMessage(response)])
      setSources(response.sources)
      setSelectedSourceId(response.sources[0]?.chunk_id ?? null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['query-history'] }),
        queryClient.invalidateQueries({ queryKey: ['conversation-history', response.conversation_id] }),
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `error-${uuidv4()}`,
          role: 'assistant',
          content: getApiErrorMessage(error),
          timestamp: new Date().toISOString(),
        },
      ])
      throw error
    } finally {
      setIsQuerying(false)
    }
  }

  const isReady = documentQuery.data?.status === 'completed'
  const currentDocument = documentQuery.data ?? null
  const title = documentQuery.data?.filename ?? 'Document workspace'

  if (documentQuery.isError) {
    return (
      <div className="rounded-[2rem] border border-rose-500/20 bg-rose-500/10 px-5 py-6 text-sm text-rose-100">
        Unable to load this document. {getApiErrorMessage(documentQuery.error)}
      </div>
    )
  }

  const renderWorkspaceContent = () => {
    if (activeTab === 'ask') {
      return (
        <ChatPanel
          conversationId={conversationId}
          isSending={isQuerying || summaryMutation.isPending || quizMutation.isPending || mindmapMutation.isPending}
          messages={messages}
          onSubmit={handleSend}
          onTopKChange={setTopK}
          placeholder="Ask about the document, a section, a table, or a specific idea..."
          subtitle={
            isReady
              ? 'Use the same conversation id for follow-up questions.'
              : 'The document is still processing, but the chat shell is ready.'
          }
          title={title}
          topK={topK}
        />
      )
    }

    const contentMap: Record<Exclude<WorkspaceTab, 'ask'>, unknown> = {
      summary: summary,
      quiz: quiz,
      mindmap: mindmap,
    }

    const titleMap = {
      summary: 'Generated summary',
      quiz: 'Generated quiz',
      mindmap: 'Generated mind map',
    } as const

    const activeContent = contentMap[activeTab]

    return (
      <div className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-6 shadow-xl shadow-black/10">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
              {titleMap[activeTab]}
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-on-surface">
              {activeTab === 'summary' && 'Concise overview of the current document'}
              {activeTab === 'quiz' && 'Study the document through generated questions'}
              {activeTab === 'mindmap' && 'High-level concept tree for quick scanning'}
            </h2>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-2xl border border-outline-variant/15 bg-surface-container-low px-4 py-3 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface"
            onClick={() => {
              if (activeTab === 'summary') {
                void summaryMutation.mutateAsync()
              }
              if (activeTab === 'quiz') {
                void quizMutation.mutateAsync()
              }
              if (activeTab === 'mindmap') {
                void mindmapMutation.mutateAsync()
              }
            }}
            type="button"
          >
            <RefreshCw className="h-4 w-4" />
            Regenerate
          </button>
        </div>

        <div className="mt-6 rounded-3xl border border-outline-variant/15 bg-surface-container px-5 py-5">
          {summaryMutation.isPending || quizMutation.isPending || mindmapMutation.isPending ? (
            <div className="space-y-3">
              <div className="h-4 w-2/3 animate-pulse rounded-full bg-surface-container-high" />
              <div className="h-4 w-5/6 animate-pulse rounded-full bg-surface-container-high" />
              <div className="h-4 w-1/2 animate-pulse rounded-full bg-surface-container-high" />
            </div>
          ) : (
            <pre className="whitespace-pre-wrap text-sm leading-7 text-on-surface">
              {renderContent(activeContent)}
            </pre>
          )}
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
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                  Document workspace
                </p>
                <h1 className="text-3xl font-semibold text-on-surface">{title}</h1>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-sm text-on-surface-variant">
              <span className="rounded-full border border-outline-variant/15 bg-surface-container px-3 py-1">
                {currentDocument?.file_type?.toUpperCase()}
              </span>
              <span className="rounded-full border border-outline-variant/15 bg-surface-container px-3 py-1">
                {formatBytes(currentDocument?.file_size ?? 0)}
              </span>
              <span className="rounded-full border border-outline-variant/15 bg-surface-container px-3 py-1">
                {currentDocument ? formatStatus(currentDocument.status) : 'Loading'}
              </span>
              {taskId && (
                <span className="rounded-full border border-outline-variant/15 bg-surface-container px-3 py-1">
                  Task {taskId.slice(0, 8)}
                </span>
              )}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                className={cn(
                  'rounded-2xl border px-4 py-3 text-sm font-medium transition',
                  activeTab === tab.key
                    ? 'border-primary/30 bg-primary/10 text-on-surface'
                    : 'border-outline-variant/15 bg-surface-container-low text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface',
                )}
                onClick={() => {
                  setActiveTab(tab.key)

                  if (tab.key === 'summary' && summary == null) {
                    void summaryMutation.mutateAsync()
                  }
                  if (tab.key === 'quiz' && quiz == null) {
                    void quizMutation.mutateAsync()
                  }
                  if (tab.key === 'mindmap' && mindmap == null) {
                    void mindmapMutation.mutateAsync()
                  }
                }}
                type="button"
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {!isReady && (
          <div className="mt-5 rounded-3xl border border-amber-500/20 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
            <div className="flex items-center justify-between gap-4">
              <p>
                This document is still processing. You can keep the chat shell open while the worker
                finishes.
              </p>
              {taskId && taskStatus && (
                <span className="rounded-full border border-amber-500/20 bg-black/10 px-3 py-1 text-[11px] uppercase tracking-[0.22em]">
                  {taskStatus} · {Math.round(taskProgress * 100)}%
                </span>
              )}
            </div>
            {taskId && taskStatus && (
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-amber-500/15">
                <div
                  className="h-full rounded-full bg-amber-300 transition-all"
                  style={{ width: `${Math.max(5, Math.min(100, taskProgress * 100))}%` }}
                />
              </div>
            )}
          </div>
        )}
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          {renderWorkspaceContent()}
        </div>

        <div className="space-y-6">
          <CitationsPanel
            document={currentDocument}
            onSelectSource={(source) => setSelectedSourceId(source.chunk_id)}
            selectedSourceId={selectedSourceId}
            sources={sources}
          />

          <div className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
            <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">Session</p>
            <p className="mt-2 text-lg font-semibold text-on-surface">Threaded Ask Your PDF</p>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              {conversationId
                ? 'This document is tied to a reusable conversation id. Continue the thread or switch to a newer one from the sidebar.'
                : 'Your first answer will create a new conversation id and thread the next follow-up automatically.'}
            </p>
            <button
              className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-outline-variant/15 bg-surface-container-low px-4 py-3 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface"
              onClick={() => navigate('/dashboard')}
              type="button"
            >
              Back to dashboard
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
