import { motion } from 'framer-motion'
import { Bot, CornerDownLeft, Send, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChatMessage } from '@/types'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/format'

interface ChatPanelProps {
  title: string
  subtitle?: string
  conversationId?: string | null
  messages: ChatMessage[]
  isSending?: boolean
  topK: number
  onTopKChange: (value: number) => void
  onSubmit: (query: string) => Promise<void>
  placeholder?: string
}

const starterPrompts = [
  'Summarize the key ideas in this document.',
  'What should I focus on first?',
  'Give me follow-up questions I should ask.',
]

export function ChatPanel({
  title,
  subtitle,
  conversationId,
  messages,
  isSending = false,
  topK,
  onTopKChange,
  onSubmit,
  placeholder = 'Ask a follow-up question...',
}: ChatPanelProps) {
  const [draft, setDraft] = useState('')
  const composerRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    composerRef.current?.focus()
  }, [])

  const canSubmit = draft.trim().length > 0 && !isSending

  const handleSubmit = async () => {
    if (!canSubmit) {
      return
    }

    await onSubmit(draft.trim())
    setDraft('')
    composerRef.current?.focus()
  }

  const conversationLabel = useMemo(
    () => (conversationId ? conversationId.slice(0, 8) : 'new thread'),
    [conversationId],
  )

  return (
    <section className="flex min-h-[calc(100vh-7rem)] flex-col rounded-[2rem] border border-outline-variant/15 bg-surface-container-low/70 shadow-xl shadow-black/10">
      <div className="border-b border-outline-variant/10 px-5 py-4 sm:px-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="text-lg font-semibold text-on-surface">{title}</p>
                <p className="text-sm text-on-surface-variant">{subtitle}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-on-surface-variant">
              <span className="rounded-full border border-outline-variant/15 bg-surface-container px-3 py-1">
                Thread {conversationLabel}
              </span>
              <span className="rounded-full border border-outline-variant/15 bg-surface-container px-3 py-1">
                Top K {topK}
              </span>
            </div>
          </div>

          <div className="rounded-2xl border border-outline-variant/15 bg-surface-container px-4 py-3 text-right">
            <p className="text-[11px] uppercase tracking-[0.24em] text-on-surface-variant">
              Conversation
            </p>
            <p className="mt-1 text-sm font-semibold text-on-surface">
              {conversationId ?? 'New thread'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-4 py-5 sm:px-6">
        {messages.length === 0 ? (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
            <div className="rounded-[1.75rem] border border-outline-variant/15 bg-surface-container-low px-6 py-8">
              <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                Start the conversation
              </p>
              <h2 className="mt-3 text-2xl font-semibold text-on-surface">
                Ask in plain language and follow the thread.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">
                The assistant will pull citations from your uploaded documents, keep the
                conversation thread alive, and reuse the same conversation id for follow-up
                questions.
              </p>
            </div>
            <div className="space-y-3 rounded-[1.75rem] border border-outline-variant/15 bg-surface-container-low px-5 py-6">
              <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                Suggested prompts
              </p>
              <div className="space-y-2">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    className="w-full rounded-2xl border border-outline-variant/10 bg-surface-container px-4 py-3 text-left text-sm text-on-surface-variant transition hover:border-primary/30 hover:bg-surface-container-high hover:text-on-surface"
                    onClick={() => setDraft(prompt)}
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <motion.article
                key={message.id}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  'max-w-[85%] rounded-[1.6rem] border px-5 py-4 shadow-lg shadow-black/10',
                  message.role === 'user'
                    ? 'ml-auto border-outline-variant/10 bg-surface-container-high'
                    : 'border-outline-variant/15 bg-surface-container-low',
                )}
                initial={{ opacity: 0, y: 12 }}
              >
                <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-on-surface-variant">
                  {message.role === 'assistant' ? (
                    <>
                      <Bot className="h-3.5 w-3.5 text-primary" />
                      Insight engine
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5 text-sky-300" />
                      You
                    </>
                  )}
                  <span className="normal-case tracking-normal">{formatRelativeTime(message.timestamp)}</span>
                </div>
                <div className="whitespace-pre-wrap text-sm leading-6 text-on-surface">
                  {message.content}
                </div>
                {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {message.sources.slice(0, 4).map((source) => (
                      <span
                        key={source.chunk_id}
                        className="rounded-full border border-outline-variant/15 bg-surface-container-high px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-on-surface-variant"
                      >
                        {source.citation_label}
                      </span>
                    ))}
                  </div>
                )}
              </motion.article>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-outline-variant/10 p-4 sm:p-5">
        <div className="rounded-[1.6rem] border border-outline-variant/15 bg-surface-container-low px-4 py-4 shadow-2xl shadow-black/10">
          <textarea
            ref={composerRef}
            aria-label="Ask a question about your document"
            className="min-h-[110px] w-full resize-none border-0 bg-transparent text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-0"
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void handleSubmit()
              }
            }}
            placeholder={placeholder}
            value={draft}
          />

          <div className="mt-4 flex flex-col gap-3 border-t border-outline-variant/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <label className="text-xs uppercase tracking-[0.24em] text-on-surface-variant">
                Top K
              </label>
              <input
                className="w-40 accent-primary"
                max={10}
                min={1}
                onChange={(event) => onTopKChange(Number(event.target.value))}
                type="range"
                value={topK}
              />
              <span className="rounded-full border border-outline-variant/15 bg-surface-container px-3 py-1 text-xs text-on-surface-variant">
                {topK} results
              </span>
            </div>

            <button
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-primary to-primary-container px-5 py-3 text-sm font-semibold text-on-primary transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canSubmit}
              onClick={() => void handleSubmit()}
              type="button"
            >
              <CornerDownLeft className="h-4 w-4" />
              {isSending ? 'Thinking…' : 'Send'}
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
