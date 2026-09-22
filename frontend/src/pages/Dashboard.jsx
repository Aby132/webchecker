import { useNavigate } from 'react-router-dom'
import usePolling from '../hooks/usePolling'
import { getDashboard } from '../services/api'
import { StatusBadge, formatMs, formatUptime, timeAgo } from '../components/StatusBadge'

export default function Dashboard() {
  const navigate = useNavigate()
  const { data, error, loading } = usePolling(getDashboard, 5000)

  if (loading && !data) return <div className="loading">Loading dashboard…</div>
  if (error && !data) return <div className="error-box">{error}</div>

  const summary = data?.summary || {}
  const projects = data?.projects || []

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Live overview of all monitored projects, websites, and APIs</p>
        </div>
      </div>

      <div className="kpi-grid">
        <div className="kpi">
          <div className="kpi-label">Total Projects</div>
          <div className="kpi-value">{summary.total_projects ?? 0}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Total Websites</div>
          <div className="kpi-value">{summary.total_websites ?? 0}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Total APIs</div>
          <div className="kpi-value">{summary.total_apis ?? 0}</div>
        </div>
        <div className="kpi up">
          <div className="kpi-label">Up</div>
          <div className="kpi-value">{summary.up ?? 0}</div>
        </div>
        <div className="kpi down">
          <div className="kpi-label">Down</div>
          <div className="kpi-value">{summary.down ?? 0}</div>
        </div>
        <div className="kpi accent">
          <div className="kpi-label">Uptime</div>
          <div className="kpi-value" style={{ fontSize: 22 }}>
            {formatUptime(summary.overall_uptime)}
          </div>
        </div>
        <div className="kpi down">
          <div className="kpi-label">Incidents</div>
          <div className="kpi-value">{summary.active_incidents ?? 0}</div>
        </div>
      </div>

      {projects.length === 0 ? (
        <div className="panel">
          <div className="empty">
            <h3>No monitors configured yet.</h3>
            <p>Add your first project, website, or API to start monitoring.</p>
            <button className="btn btn-primary" onClick={() => navigate('/configuration')}>
              Open Configuration
            </button>
          </div>
        </div>
      ) : (
        projects.map((section) => (
          <div className="panel" key={section.project.id}>
            <div className="panel-header">
              <div>
                <h2
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/projects/${section.project.id}`)}
                >
                  {section.project.name}
                  {!section.project.enabled ? ' (Disabled)' : ''}
                </h2>
              </div>
              <div className="meta">
                {section.operational} / {section.total} websites · {section.operational_apis ?? 0} / {section.total_apis ?? 0} APIs operational
              </div>
            </div>
            <div className="table-wrap">
              {section.websites.length === 0 ? (
                <div className="empty">
                  <p>No websites in this project.</p>
                </div>
              ) : (
                <table className="data">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>URL</th>
                      <th>Status</th>
                      <th>HTTP</th>
                      <th>Response</th>
                      <th>Last Checked</th>
                      <th>Uptime</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {section.websites.map((site) => (
                      <tr
                        key={site.id}
                        className="clickable"
                        onClick={() => navigate(`/websites/${site.id}`)}
                      >
                        <td>{site.name}</td>
                        <td className="url-cell mono">{site.url}</td>
                        <td><StatusBadge status={site.enabled ? site.status : 'DISABLED'} /></td>
                        <td className="mono">{site.last_status_code ?? '—'}</td>
                        <td className="mono">{formatMs(site.last_response_time)}</td>
                        <td>{timeAgo(site.last_checked)}</td>
                        <td className="mono">{formatUptime(site.uptime)}</td>
                        <td>
                          <button
                            className="btn btn-sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/websites/${site.id}`)
                            }}
                          >
                            Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="panel-header" style={{ borderTop: '1px solid var(--border)' }}>
              <h2 style={{ fontSize: 15 }}>APIs</h2>
            </div>
            <div className="table-wrap">
              {(section.apis || []).length === 0 ? (
                <div className="empty">
                  <p>No APIs in this project.</p>
                </div>
              ) : (
                <table className="data">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Method</th>
                      <th>URL</th>
                      <th>Status</th>
                      <th>HTTP</th>
                      <th>Response</th>
                      <th>Last Checked</th>
                      <th>Uptime</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {section.apis.map((api) => (
                      <tr
                        key={api.id}
                        className="clickable"
                        onClick={() => navigate(`/apis/${api.id}`)}
                      >
                        <td>{api.name}</td>
                        <td className="mono">{api.method}</td>
                        <td className="url-cell mono">{api.url}</td>
                        <td><StatusBadge status={api.enabled ? api.status : 'DISABLED'} /></td>
                        <td className="mono">{api.last_status_code ?? '—'}</td>
                        <td className="mono">{formatMs(api.last_response_time)}</td>
                        <td>{timeAgo(api.last_checked)}</td>
                        <td className="mono">{formatUptime(api.uptime)}</td>
                        <td>
                          <button
                            className="btn btn-sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/apis/${api.id}`)
                            }}
                          >
                            Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
