import { useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import usePolling from './hooks/usePolling'
import { getHealth } from './services/api'
import Dashboard from './pages/Dashboard'
import ProjectDetails from './pages/ProjectDetails'
import WebsiteDetails from './pages/WebsiteDetails'
import Configuration from './pages/Configuration'
import Logs from './pages/Logs'
import ProjectsPage from './pages/ProjectsPage'
import WebsitesPage from './pages/WebsitesPage'
import EmailAlerts from './pages/EmailAlerts'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { data: health } = usePolling(getHealth, 5000)

  return (
    <div className="app-shell">
      <button className="btn mobile-toggle" onClick={() => setSidebarOpen((v) => !v)}>
        Menu
      </button>
      <Sidebar open={sidebarOpen} engineRunning={health?.engine_running} />
      <main className="main" onClick={() => setSidebarOpen(false)}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectDetails />} />
          <Route path="/websites" element={<WebsitesPage />} />
          <Route path="/websites/:id" element={<WebsiteDetails />} />
          <Route path="/configuration" element={<Configuration />} />
          <Route path="/email" element={<EmailAlerts />} />
          <Route path="/logs" element={<Logs />} />
        </Routes>
      </main>
    </div>
  )
}
