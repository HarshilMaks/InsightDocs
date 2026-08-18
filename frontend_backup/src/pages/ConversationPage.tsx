import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageSquareQuote } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { v4 as uuidv4 } from 'uuid'
import { getApiErrorMessage, getQueryHistory, sendQuery } from '@/lib/api'
import { historyToMessages, responseToAssistantMessage } from '@/lib/threads'
import { ChatPanel } from '@/components/ChatPanel'
import { CitationsPanel } from '@/components/CitationsPanel'
import type { ChatMessage, SourceReference } from '@/types'

export default function ConversationPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const activeConversationId = conversationId === 'new' ? null : conversationId
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sources, setSources] = useState<SourceReference[]>([])
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null)
  const [topK, setTopK] = useState(5)

  const historyQuery = useQuery({
    queryKey: ['conversation-history', activeConversationId],
    queryFn: () => getQueryHistory(activeConversationId),
    enabled: Boolean(activeConversationId),
  })

  useEffect(() => {
    setMessages(historyToMessages(historyQuery.data?.queries ?? []))
  }, [historyQuery.data])

  const sendMutation = useMutation({
    mutationFn: (queryText: string) =>
      sendQuery({
        query: queryText,
        top_k: topK,
        conversation_id: activeConversationId ?? undefined,
      }),
  })

  const handleSend = async (queryText: string) => {
    if (!conversationId) {
      throw new Error('Conversation id is missing.')
    }

    const optimisticMessage: ChatMessage = {
      id: `user-${uuidv4()}`,
      role: 'user',
      content: queryText,
      timestamp: new Date().toISOString(),
    }

    setMessages((current) => [...current, optimisticMessage])

    try {
      const response = await sendMutation.mutateAsync(queryText)
      if (response.conversation_id !== activeConversationId) {
        navigate(`/conversations/${response.conversation_id}`, { replace: true })
      }
      setMessages((current) => [
        ...current.filter((message) => message.id !== optimisticMessage.id),
        optimisticMessage,
        responseToAssistantMessage(response),
      ])
      setSources(response.sources)
      setSelectedSourceId(response.sources[0]?.chunk_id ?? null)
      await queryClient.invalidateQueries({ queryKey: ['query-history'] })
      await queryClient.invalidateQueries({ queryKey: ['conversation-history', response.conversation_id] })
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
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="space-y-6">
        {historyQuery.isError && (
          <div className="rounded-[2rem] border border-rose-500/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
            Conversation history could not be loaded. {getApiErrorMessage(historyQuery.error)}
          </div>
        )}

        <section className="rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 p-5 shadow-xl shadow-black/10">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                Conversation thread
              </p>
              <h1 className="mt-2 text-3xl font-semibold text-on-surface">Ask follow-up questions</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-on-surface-variant">
                This route reuses the current conversation id, so every new answer stays threaded and
                easy to review later.
              </p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <MessageSquareQuote className="h-5 w-5" />
            </div>
          </div>
        </section>

        <ChatPanel
          conversationId={activeConversationId}
          isSending={sendMutation.isPending}
          messages={messages}
          onSubmit={handleSend}
          onTopKChange={setTopK}
          placeholder="Ask the thread a follow-up question..."
          subtitle="This conversation is independent of a single document and can span your whole library."
          title="Conversation workspace"
          topK={topK}
        />
      </div>

      <CitationsPanel
        onSelectSource={(source) => setSelectedSourceId(source.chunk_id)}
        selectedSourceId={selectedSourceId}
        sources={sources}
      />
    </div>
  )
}
