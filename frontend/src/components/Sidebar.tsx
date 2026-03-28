import {
  Clock3,
  FileText,
  Files,
  FolderKanban,
  MessageSquareText,
  Plus,
  Settings,
} from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import { conversationTitle } from '@/lib/threads'
import { formatBytes, formatRelativeTime, formatStatus, truncateText } from '@/lib/format'
import type { DocumentResponse, ThreadSummary } from '@/types'
import { cn } from '@/lib/utils'

interface SidebarProps {
  documents: DocumentResponse[]
  threads: ThreadSummary[]
  documentsLoading: boolean
  threadsLoading: boolean
  activeDocumentId?: string
  activeConversationId?: string
}

const navItems = [
  {
    icon: FolderKanban,
    label: 'Dashboard',
    to: '/dashboard',
  },
  {
    icon: Files,
    label: 'Library',
    to: '/dashboard#library',
  },
  {
    icon: Settings,
    label: 'Settings',
    to: '/settings',
  },
]

const statusClasses: Record<string, string> = {
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/20',
  processing: 'bg-sky-500/15 text-sky-300 border-sky-500/20',
  completed: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/20',
  failed: 'bg-rose-500/15 text-rose-300 border-rose-500/20',
}

export function Sidebar({
  documents,
  threads,
  documentsLoading,
  threadsLoading,
  activeDocumentId,
  activeConversationId,
}: SidebarProps) {
  const displayedThreads = threads.slice(0, 8)

  return (
    <aside className="fixed left-0 top-16 z-40 hidden h-[calc(100vh-4rem)] w-72 flex-col border-r border-outline-variant/15 bg-surface-container-low/90 backdrop-blur-xl lg:flex">
      <div className="flex items-center justify-between border-b border-outline-variant/10 px-5 py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">Workspace</p>
          <p className="text-sm font-semibold text-on-surface">Navigate documents and threads</p>
        </div>
        <Link
          className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-outline-variant/15 bg-surface-container-high text-on-surface-variant transition hover:bg-surface-container"
          to="/dashboard"
        >
          <Plus className="h-4 w-4" />
        </Link>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
        <nav className="space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.label}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition',
                  isActive
                    ? 'border-primary/30 bg-primary/10 text-on-surface'
                    : 'border-transparent bg-surface-container-low text-on-surface-variant hover:border-outline-variant/15 hover:bg-surface-container-high hover:text-on-surface',
                )
              }
              to={item.to}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <section id="library" className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">Library</p>
              <p className="text-sm font-semibold text-on-surface">{documents.length} documents</p>
            </div>
            <FileText className="h-4 w-4 text-primary" />
          </div>

          <div className="space-y-2">
            {documentsLoading && (
              <div className="space-y-2">
                <div className="h-20 animate-pulse rounded-2xl bg-surface-container-high/80" />
                <div className="h-20 animate-pulse rounded-2xl bg-surface-container-high/80" />
              </div>
            )}

            {!documentsLoading && documents.length === 0 && (
              <div className="rounded-2xl border border-dashed border-outline-variant/15 bg-surface-container-low px-4 py-5 text-sm text-on-surface-variant">
                Upload a document to start asking questions.
              </div>
            )}

            {!documentsLoading &&
              documents.map((document) => (
                <Link
                  key={document.id}
                  className={cn(
                    'block rounded-2xl border p-3 transition',
                    activeDocumentId === document.id
                      ? 'border-primary/30 bg-primary/10'
                      : 'border-outline-variant/10 bg-surface-container-low hover:border-outline-variant/20 hover:bg-surface-container-high',
                  )}
                  to={`/documents/${document.id}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-on-surface">{document.filename}</p>
                      <p className="text-xs text-on-surface-variant">{formatBytes(document.file_size)}</p>
                    </div>
                    <span
                      className={cn(
                        'rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.22em]',
                        statusClasses[document.status] ?? 'bg-surface-container-high text-on-surface-variant',
                      )}
                    >
                      {formatStatus(document.status)}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-on-surface-variant">
                    Updated {formatRelativeTime(document.updated_at)}
                  </p>
                </Link>
              ))}
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">Threads</p>
              <p className="text-sm font-semibold text-on-surface">{displayedThreads.length} recent chats</p>
            </div>
            <MessageSquareText className="h-4 w-4 text-primary" />
          </div>

          <div className="space-y-2">
            {threadsLoading && (
              <div className="space-y-2">
                <div className="h-16 animate-pulse rounded-2xl bg-surface-container-high/80" />
                <div className="h-16 animate-pulse rounded-2xl bg-surface-container-high/80" />
              </div>
            )}

            {!threadsLoading && displayedThreads.length === 0 && (
              <div className="rounded-2xl border border-dashed border-outline-variant/15 bg-surface-container-low px-4 py-5 text-sm text-on-surface-variant">
                Your threaded conversations will appear here.
              </div>
            )}

            {!threadsLoading &&
              displayedThreads.map((thread) => (
                <Link
                  key={thread.conversationId}
                  className={cn(
                    'block rounded-2xl border p-3 transition',
                    activeConversationId === thread.conversationId
                      ? 'border-primary/30 bg-primary/10'
                      : 'border-outline-variant/10 bg-surface-container-low hover:border-outline-variant/20 hover:bg-surface-container-high',
                  )}
                  to={`/conversations/${thread.conversationId}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-on-surface">
                      {truncateText(conversationTitle(thread), 50)}
                    </p>
                    <Clock3 className="h-3.5 w-3.5 text-on-surface-variant" />
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs text-on-surface-variant">
                    {truncateText(thread.latestResponse ?? thread.latestQuery, 110)}
                  </p>
                  <p className="mt-3 text-[11px] uppercase tracking-[0.22em] text-on-surface-variant">
                    {thread.turnCount} turns · {formatRelativeTime(thread.updatedAt)}
                  </p>
                </Link>
              ))}
          </div>
        </section>
      </div>

      <div className="border-t border-outline-variant/10 px-4 py-4">
        <Link
          className="flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-primary to-primary-container px-4 py-3 text-sm font-semibold text-on-primary shadow-lg shadow-primary/15 transition hover:opacity-95"
          to="/conversations/new"
        >
          <Plus className="h-4 w-4" />
          New conversation
        </Link>
      </div>
    </aside>
  )
}
