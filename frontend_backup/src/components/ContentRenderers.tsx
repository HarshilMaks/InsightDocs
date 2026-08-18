import ReactMarkdown from 'react-markdown'

interface MarkdownContentProps {
  content: string
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="prose prose-sm prose-invert max-w-none prose-headings:text-on-surface prose-p:text-on-surface-variant prose-strong:text-on-surface prose-li:text-on-surface-variant prose-a:text-primary">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}

interface QuizViewProps {
  data: unknown
}

export function QuizView({ data }: QuizViewProps) {
  if (!data || typeof data !== 'object') {
    return <p className="text-sm text-on-surface-variant">No quiz data available.</p>
  }

  const questions: Array<{
    question?: string
    options?: string[]
    answer?: string
    explanation?: string
  }> = Array.isArray(data) ? data : (data as Record<string, unknown>).questions as typeof questions ?? []

  if (questions.length === 0) {
    return <p className="text-sm text-on-surface-variant">No questions generated.</p>
  }

  return (
    <div className="space-y-6">
      {questions.map((q, idx) => (
        <div key={idx} className="rounded-2xl border border-outline-variant/15 bg-surface-container p-4">
          <p className="text-sm font-semibold text-on-surface">
            <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
              {idx + 1}
            </span>
            {q.question ?? `Question ${idx + 1}`}
          </p>
          {q.options && q.options.length > 0 && (
            <ul className="mt-3 space-y-2 pl-8">
              {q.options.map((opt, optIdx) => (
                <li
                  key={optIdx}
                  className="flex items-start gap-2 text-sm text-on-surface-variant"
                >
                  <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-outline-variant/20 text-[10px] font-medium">
                    {String.fromCharCode(65 + optIdx)}
                  </span>
                  {opt}
                </li>
              ))}
            </ul>
          )}
          {q.answer && (
            <p className="mt-3 rounded-xl bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
              <span className="font-semibold">Answer:</span> {q.answer}
            </p>
          )}
          {q.explanation && (
            <p className="mt-2 text-xs leading-5 text-on-surface-variant">{q.explanation}</p>
          )}
        </div>
      ))}
    </div>
  )
}

interface MindmapViewProps {
  data: unknown
}

export function MindmapView({ data }: MindmapViewProps) {
  if (!data || typeof data !== 'object') {
    return <p className="text-sm text-on-surface-variant">No mind map data available.</p>
  }

  const obj = data as Record<string, unknown>
  const nodes = (obj.nodes ?? []) as Array<{ id?: string; label?: string; group?: string }>
  const edges = (obj.edges ?? obj.links ?? []) as Array<{ source?: string; target?: string; label?: string }>

  if (nodes.length === 0) {
    // Fallback: if it's just a string or markdown, render as markdown
    if (typeof data === 'string') {
      return <MarkdownContent content={data} />
    }
    return (
      <div className="text-sm text-on-surface-variant">
        <p className="mb-2">Mind map structure:</p>
        <pre className="whitespace-pre-wrap rounded-xl bg-surface-container p-3 text-xs">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    )
  }

  // Group nodes by category
  const groups = new Map<string, typeof nodes>()
  for (const node of nodes) {
    const group = node.group ?? 'General'
    if (!groups.has(group)) groups.set(group, [])
    groups.get(group)!.push(node)
  }

  return (
    <div className="space-y-4">
      {Array.from(groups.entries()).map(([group, groupNodes]) => (
        <div key={group} className="rounded-2xl border border-outline-variant/15 bg-surface-container p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">{group}</p>
          <div className="flex flex-wrap gap-2">
            {groupNodes.map((node, idx) => (
              <span
                key={node.id ?? idx}
                className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-on-surface"
              >
                {node.label ?? node.id ?? `Node ${idx}`}
              </span>
            ))}
          </div>
        </div>
      ))}
      {edges.length > 0 && (
        <div className="rounded-2xl border border-outline-variant/15 bg-surface-container p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
            Relationships ({edges.length})
          </p>
          <div className="space-y-1">
            {edges.slice(0, 20).map((edge, idx) => (
              <p key={idx} className="text-xs text-on-surface-variant">
                <span className="text-on-surface">{edge.source}</span>
                {' → '}
                <span className="italic text-primary/80">{edge.label ?? 'relates to'}</span>
                {' → '}
                <span className="text-on-surface">{edge.target}</span>
              </p>
            ))}
            {edges.length > 20 && (
              <p className="text-xs text-on-surface-variant">...and {edges.length - 20} more</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
