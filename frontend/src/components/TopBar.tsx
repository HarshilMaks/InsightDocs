import { useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, KeyRound, LogOut, Settings, User as UserIcon } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/context/auth-context'
import { getByokStatus } from '@/lib/api'

interface TopBarProps {
  searchQuery: string
  onSearchChange: (value: string) => void
  onRequireAuth: () => void
}

const titles: Record<string, string> = {
  '/': 'Documents',
  '/history': 'History',
  '/byok': 'API key',
  '/settings': 'Settings',
  '/help': 'Help',
}

function initials(name: string) {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() ?? '')
      .join('') || 'U'
  )
}

export function TopBar({ searchQuery, onSearchChange, onRequireAuth }: TopBarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, user, logout } = useAuth()

  const byokQuery = useQuery({
    queryKey: ['byok-status'],
    queryFn: getByokStatus,
    enabled: isAuthenticated,
    staleTime: 60_000,
  })

  const title = location.pathname.startsWith('/documents/')
    ? 'Workspace'
    : titles[location.pathname] ?? 'InsightDocs'

  const byok = byokQuery.data
  const byokActive = Boolean(byok?.byok_enabled && byok?.has_api_key)

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-3 backdrop-blur-xl md:px-4">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-1 !h-4" />

      <h1 className="text-sm font-medium">{title}</h1>

      {/* Search only applies to the document library */}
      {location.pathname === '/' && (
        <div className="relative ml-auto w-full max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search documents"
            aria-label="Search documents"
            className="h-9 pl-8"
          />
        </div>
      )}

      <div className={location.pathname === '/' ? 'flex items-center gap-2' : 'ml-auto flex items-center gap-2'}>
        {isAuthenticated && (
          <Badge
            variant="outline"
            className="hidden gap-1.5 font-normal sm:inline-flex"
            title={byok?.message ?? 'Using the platform key'}
          >
            <KeyRound className="size-3" />
            {byokActive ? byok?.active_model || 'Your key' : 'Platform key'}
          </Badge>
        )}

        {isAuthenticated ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="size-8 rounded-full" aria-label="Account menu">
                <Avatar className="size-8">
                  <AvatarFallback className="bg-primary/15 text-xs font-semibold text-primary">
                    {initials(user?.name ?? '')}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <div className="grid gap-0.5">
                  <span className="truncate text-sm font-medium">{user?.name}</span>
                  <span className="truncate text-xs text-muted-foreground">{user?.email}</span>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/byok')}>
                <KeyRound className="size-4" />
                API key
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/settings')}>
                <Settings className="size-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onClick={() => {
                  logout()
                  navigate('/')
                }}
              >
                <LogOut className="size-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Button size="sm" onClick={onRequireAuth}>
            <UserIcon className="size-4" />
            Sign in
          </Button>
        )}
      </div>
    </header>
  )
}
