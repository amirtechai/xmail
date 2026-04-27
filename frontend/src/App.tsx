import { type ReactNode, useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth'
import Layout from './components/Layout'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import BotControlPage from './pages/BotControlPage'
import ContactsPage from './pages/ContactsPage'
import ReportsPage from './pages/ReportsPage'
import SuppressionPage from './pages/SuppressionPage'
import CampaignDetailPage from './pages/CampaignDetailPage'
import CampaignsPage from './pages/CampaignsPage'
import ComposePage from './pages/ComposePage'
import LogsPage from './pages/LogsPage'
import SettingsPage from './pages/SettingsPage'
import UsersPage from './pages/UsersPage'
import CampaignStatsPage from './pages/CampaignStatsPage'

function RequireAuth({ children }: { children: ReactNode }) {
  const user = useAuth((s) => s.user)
  const loading = useAuth((s) => s.loading)
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen text-text-secondary text-sm">
        Loading…
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const loadUser = useAuth((s) => s.loadUser)

  useEffect(() => {
    void loadUser()
  }, [loadUser])

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes — pathless layout wrapper */}
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/bot" element={<BotControlPage />} />
          <Route path="/contacts" element={<ContactsPage />} />
          <Route path="/campaigns" element={<CampaignsPage />} />
          <Route path="/campaigns/:id" element={<CampaignDetailPage />} />
          <Route path="/campaign-stats" element={<CampaignStatsPage />} />
          <Route path="/compose" element={<ComposePage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/suppression" element={<SuppressionPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/admin/users" element={<UsersPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
