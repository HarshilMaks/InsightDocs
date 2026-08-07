import { Navigate, Route, Routes } from 'react-router-dom'
import { WorkspaceProvider } from '@/context/workspace-context'
import { GuestOnly, RequireAuth } from '@/components/route-guards'
import { WorkspaceShell } from '@/components/WorkspaceShell'
import LoginPage from '@/pages/LoginPage'
import NotFoundPage from '@/pages/NotFoundPage'
import RegisterPage from '@/pages/RegisterPage'
import SettingsPage from '@/pages/SettingsPage'

export default function App() {
  return (
    <WorkspaceProvider>
      <Routes>
        {/* Fallback full-page auth routes */}
        <Route element={<GuestOnly />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* Workspace - the product IS the website */}
        <Route path="/" element={<WorkspaceShell />} />
        <Route path="/documents/:documentId" element={<WorkspaceShell />} />

        {/* Authenticated-only routes */}
        <Route element={<RequireAuth />}>
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        {/* Legacy redirects */}
        <Route path="/dashboard" element={<Navigate replace to="/" />} />
        <Route path="/conversations/:conversationId" element={<Navigate replace to="/" />} />

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </WorkspaceProvider>
  )
}
