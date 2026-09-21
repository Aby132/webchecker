import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard', icon: '▣' },
  { to: '/configuration', label: 'Configuration', icon: '⚙' },
  { to: '/projects', label: 'Projects', icon: '◫' },
  { to: '/websites', label: 'Websites', icon: '◎' },
  { to: '/email', label: 'Email Alerts', icon: '✉' },
  { to: '/logs', label: 'Logs', icon: '☰' },
]

export default function Sidebar({ open, engineRunning }) {
  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="brand">
        <div className="brand-mark">W</div>
        <div className="brand-text">
          <strong>Web Monitor</strong>
          <span>Self-hosted uptime</span>
        </div>
      </div>

      <nav className="nav">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/'}
            className={({ isActive }) => (isActive ? 'active' : undefined)}
          >
            <span className="nav-icon">{link.icon}</span>
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="engine-status">
          <div className="label">System Status</div>
          <div className="value">
            <span className={`dot ${engineRunning ? 'running' : 'stopped'}`} />
            Monitoring Engine: {engineRunning ? 'Running' : 'Stopped'}
          </div>
        </div>
      </div>
    </aside>
  )
}
