import { LogOut, PanelLeftClose, PanelLeftOpen, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/auth-context'
import { useWorkspace } from '@/context/workspace-context'
import { cn } from '@/lib/utils'

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function WorkspaceNavbar() {
  const navigate = useNavigate()
  const { user, isAuthenticated, logout } = useAuth()
  const { sidebarCollapsed, setSidebarCollapsed } = useWorkspace()

  return (
    <header className="fixed inset-x-0 top-0 z-50 flex h-12 items-center justify-between border-b border-white/[0.06] bg-[hsl(226,46%,5%)]/90 px-3 backdrop-blur-xl">
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="hidden h-8 w-8 items-center justify-center rounded-lg text-white/50 transition hover:bg-white/[0.06] hover:text-white/80 lg:flex"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </button>

        <button
          type="button"
          className="flex items-center gap-2"
          onClick={() => navigate('/')}
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-sky-400 to-indigo-500 text-[10px] font-black text-white">
            ID
          </div>
          <span className="text-sm font-semibold text-white/90">InsightDocs</span>
        </button>
      </div>

      <div className="flex items-center gap-1">
        {isAuthenticated && (
          <>
            <button
              type="button"
              className="flex h-8 items-center gap-2 rounded-lg px-2.5 text-xs text-white/50 transition hover:bg-white/[0.06] hover:text-white/80"
              onClick={() => navigate('/settings')}
            >
              <Settings className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Settings</span>
            </button>

            <div className="mx-1 h-4 w-px bg-white/[0.08]" />

            <button
              type="button"
              className="flex h-8 items-center gap-2 rounded-lg px-2.5 text-xs text-white/50 transition hover:bg-white/[0.06] hover:text-white/80"
              onClick={() => {
                logout()
                navigate('/')
              }}
            >
              <LogOut className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Sign out</span>
            </button>

            <div
              className={cn(
                'ml-1 flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-semibold',
                'bg-sky-500/20 text-sky-300',
              )}
              title={user?.email}
            >
              {user ? getInitials(user.name) : 'U'}
            </div>
          </>
        )}

        {!isAuthenticated && (
          <button
            type="button"
            className="flex h-8 items-center gap-1.5 rounded-lg bg-sky-500/15 px-3 text-xs font-medium text-sky-300 transition hover:bg-sky-500/25"
            onClick={() => navigate('/login')}
          >
            Sign in
          </button>
        )}
      </div>
    </header>
  )
}
