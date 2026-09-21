import { useNavigate, useParams } from 'react-router-dom'
import usePolling from '../hooks/usePolling'
import { getProjectDetails } from '../services/api'
import { StatusBadge, formatMs, formatUptime, timeAgo } from '../components/StatusBadge'

export default function ProjectDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, error, loading } = usePolling(() => getProjectDetails(id), 5000, [id])

  if (loading && !data) return <div className="loading">Loading project…</div>
  if (error && !data) return <div className="error-box">{error}</div>
  if (!data) return null

  const { project } = data

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{project.name}</h1>
          <p>{project.description || 'Project monitoring overview'}</p>
        </div>
        <div className="header-actions">
          <button className="btn" onClick={() => navigate('/')}>Back</button>
        </div>
      </div>

      <div className="stat-row">
        <div className="kpi">
          <div className="kpi-label">Total Websites</div>
          <div className="kpi-value">{data.total_websites}</div>
        </div>
        <div className="kpi up">
          <div className="kpi-label">Up</div>
          <div className="kpi-value">{data.up}</div>
        </div>
        <div className="kpi down">
          <div className="kpi-label">Down</div>
          <div className="kpi-value">{data.down}</div>
        </div>
        <div className="kpi accent">
          <div className="kpi-label">Project Uptime</div>
          <div className="kpi-value" style={{ fontSize: 22 }}>{formatUptime(data.uptime)}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Websites</h2>
          <div className="meta">Avg response: {formatMs(data.average_response_time)}</div>
        </div>
        <div className="table-wrap">
          {data.websites.length === 0 ? (
            <div className="empty"><p>No websites in this project.</p></div>
          ) : (
            <table className="data">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>URL</th>
                  <th>Status</th>
                  <th>HTTP</th>
                  <th>Response</th>
                  <th>Uptime</th>
                  <th>Last Checked</th>
                </tr>
              </thead>
              <tbody>
                {data.websites.map((site) => (
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
                    <td className="mono">{formatUptime(site.uptime)}</td>
                    <td>{timeAgo(site.last_checked)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
