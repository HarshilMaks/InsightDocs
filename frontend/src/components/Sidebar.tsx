import { useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  FileText,
  History,
  KeyRound,
  Settings,
  HelpCircle,
  LogOut,
  Plus,
  LogIn,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useAuth } from '@/context/auth-context'
import { listDocuments } from '@/lib/api'
import { BrandLogo } from './BrandLogo'

interface AppSidebarProps {
  /** Opens the auth dialog owned by App when a gated action is used. */
  onRequireAuth: () => void
}

const navItems = [
  { label: 'Documents', to: '/', icon: FileText, requiresAuth: false },
  { label: 'History', to: '/history', icon: History, requiresAuth: true },
  { label: 'API key', to: '/byok', icon: KeyRound, requiresAuth: true },
  { label: 'Settings', to: '/settings', icon: Settings, requiresAuth: true },
]

function initials(name: string) {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('') || 'U'
  )
}

export function AppSidebar({ onRequireAuth }: AppSidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, user, logout } = useAuth()

  // Same query key as the library view, so React Query serves this from
  // cache instead of issuing a second request.
  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    enabled: isAuthenticated,
    staleTime: 30_000,
  })
  const documentsCount = documentsQuery.data?.documents.length ?? 0

  const isActive = (to: string) =>
    to === '/' ? location.pathname === '/' || location.pathname.startsWith('/documents/') : location.pathname === to

  const go = (to: string, requiresAuth: boolean) => {
    if (requiresAuth && !isAuthenticated) {
      onRequireAuth()
      return
    }
    navigate(to)
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-1 py-1.5">
          <BrandLogo size={28} />
          <div className="grid flex-1 leading-tight group-data-[collapsible=icon]:hidden">
            <span className="truncate text-sm font-semibold">InsightDocs</span>
            <span className="truncate text-[11px] text-muted-foreground">Provable RAG</span>
          </div>
        </div>

        <Button
          className="w-full justify-start gap-2 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
          onClick={() => (isAuthenticated ? navigate('/?upload=true') : onRequireAuth())}
        >
          <Plus className="size-4 shrink-0" />
          <span className="group-data-[collapsible=icon]:hidden">New analysis</span>
        </Button>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <SidebarMenuButton
                    isActive={isActive(item.to)}
                    tooltip={item.label}
                    onClick={() => go(item.to, item.requiresAuth)}
                  >
                    <item.icon className="size-4" />
                    <span>{item.label}</span>
                  </SidebarMenuButton>
                  {item.to === '/' && documentsCount > 0 && (
                    <SidebarMenuBadge>{documentsCount}</SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarSeparator />
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              isActive={location.pathname === '/help'}
              tooltip="Help"
              onClick={() => navigate('/help')}
            >
              <HelpCircle className="size-4" />
              <span>Help</span>
            </SidebarMenuButton>
          </SidebarMenuItem>

          {isAuthenticated ? (
            <>
              <SidebarMenuItem>
                <SidebarMenuButton tooltip={user?.email ?? ''} className="cursor-default hover:bg-transparent">
                  <Avatar className="size-5">
                    <AvatarFallback className="bg-primary/15 text-[10px] font-semibold text-primary">
                      {initials(user?.name ?? '')}
                    </AvatarFallback>
                  </Avatar>
                  <span className="truncate">{user?.name}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  tooltip="Sign out"
                  onClick={() => {
                    logout()
                    navigate('/')
                  }}
                >
                  <LogOut className="size-4" />
                  <span>Sign out</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </>
          ) : (
            <SidebarMenuItem>
              <SidebarMenuButton tooltip="Sign in" onClick={onRequireAuth}>
                <LogIn className="size-4" />
                <span>Sign in</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
