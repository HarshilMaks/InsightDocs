import { LayoutDashboard, LogOut, Settings, UploadCloud } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/auth-context'

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function Navbar() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="fixed inset-x-0 top-0 z-50 h-16 border-b border-outline-variant/15 bg-surface/80 backdrop-blur-xl">
      <div className="flex h-full items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <button
          aria-label="Go to dashboard"
          className="flex items-center gap-3 transition-transform hover:scale-[1.01]"
          onClick={() => navigate('/dashboard')}
          type="button"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-container text-sm font-black text-on-primary shadow-lg shadow-primary/20">
            ID
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-on-surface">InsightDocs</p>
            <p className="text-[11px] uppercase tracking-[0.28em] text-on-surface-variant">
              Threaded Ask Your PDF
            </p>
          </div>
        </button>

        <div className="hidden items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low/80 px-3 py-1.5 text-xs text-on-surface-variant md:flex">
          <LayoutDashboard className="h-4 w-4" />
          <span>Workspace ready</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            className="hidden items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low px-3 py-2 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface sm:flex"
            onClick={() => navigate('/dashboard')}
            type="button"
          >
            <UploadCloud className="h-4 w-4" />
            New upload
          </button>

          <button
            className="flex items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low px-3 py-2 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface"
            onClick={() => navigate('/settings')}
            type="button"
          >
            <Settings className="h-4 w-4" />
            Settings
          </button>

          <div className="flex items-center gap-3 rounded-full border border-outline-variant/15 bg-surface-container-low px-3 py-1.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
              {user ? getInitials(user.name) : 'U'}
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-medium text-on-surface">{user?.name ?? 'Workspace user'}</p>
              <p className="text-[11px] text-on-surface-variant">{user?.email}</p>
            </div>
          </div>

          <button
            className="flex items-center gap-2 rounded-full border border-outline-variant/15 bg-surface-container-low px-3 py-2 text-sm text-on-surface-variant transition hover:bg-surface-container-high hover:text-on-surface"
            onClick={handleLogout}
            type="button"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </div>
    </header>
  )
}
