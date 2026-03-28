import type { ChatMessage, QueryHistoryItem, QueryResponse, ThreadSummary } from '@/types'

function sortHistory(items: QueryHistoryItem[]): QueryHistoryItem[] {
  return [...items].sort((left, right) => {
    const leftTurn = left.turn_index ?? Number.MAX_SAFE_INTEGER
    const rightTurn = right.turn_index ?? Number.MAX_SAFE_INTEGER

    if (left.conversation_id && right.conversation_id && left.conversation_id === right.conversation_id) {
      if (leftTurn !== rightTurn) {
        return leftTurn - rightTurn
      }
    }

    return new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
  })
}

export function historyToMessages(items: QueryHistoryItem[]): ChatMessage[] {
  const sorted = sortHistory(items)
  const messages: ChatMessage[] = []

  for (const item of sorted) {
    messages.push({
      id: `${item.id}-user`,
      role: 'user',
      content: item.query,
      timestamp: item.created_at,
    })

    if (item.response) {
      messages.push({
        id: `${item.id}-assistant`,
        role: 'assistant',
        content: item.response,
        timestamp: item.created_at,
      })
    }
  }

  return messages
}

export function responseToAssistantMessage(response: QueryResponse): ChatMessage {
  return {
    id: response.query_id,
    role: 'assistant',
    content: response.answer,
    timestamp: new Date().toISOString(),
    sources: response.sources,
  }
}

export function buildThreadSummaries(items: QueryHistoryItem[]): ThreadSummary[] {
  const summaries = new Map<string, ThreadSummary>()

  for (const item of sortHistory(items)) {
    const conversationId = item.conversation_id
    if (!conversationId) {
      continue
    }

    const current = summaries.get(conversationId)

    if (!current) {
      summaries.set(conversationId, {
        conversationId,
        latestQuery: item.query,
        latestResponse: item.response ?? null,
        turnCount: 1,
        updatedAt: item.created_at,
      })
      continue
    }

    summaries.set(conversationId, {
      ...current,
      latestQuery: item.query,
      latestResponse: item.response ?? current.latestResponse ?? null,
      turnCount: current.turnCount + 1,
      updatedAt: item.created_at,
    })
  }

  return Array.from(summaries.values()).sort(
    (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
  )
}

export function conversationTitle(summary: ThreadSummary): string {
  return summary.latestQuery.length > 52
    ? `${summary.latestQuery.slice(0, 52).trimEnd()}…`
    : summary.latestQuery
}
