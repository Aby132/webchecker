import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import usePolling from '../hooks/usePolling'
import { getProjectDetails } from '../services/api'
import { StatusBadge, formatMs, formatUptime, timeAgo } from '../components/StatusBadge'

export default function ProjectDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, error, loading } = usePolling(() => getProjectDetails(id), 5000, [id])
  const [tab, setTab] = useState('overview')

  if (loading && !data) return <div className="loading">Loading project…</div>
  if (error && !data) return <div className="error-box">{error}</div>
  if (!data) return null

  const { project } = data
  const websites = data.websites || []
  const apis = data.apis || []

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
          <div className="kpi-label">Websites</div>
          <div className="kpi-value">{data.total_websites}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">APIs</div>
          <div className="kpi-value">{data.total_apis ?? apis.length}</div>
        </div>
        <div className="kpi up">
          <div className="kpi-label">Up</div>
          <div className="kpi-value">{data.up}</div>
        </div>
        <div className="kpi down">
          <div className="kpi-label">Down</div>
          <div className="kpi-value">{data.down}</div>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>
          Overview
        </button>
        <button className={`tab ${tab === 'websites' ? 'active' : ''}`} onClick={() => setTab('websites')}>
          Websites
        </button>
        <button className={`tab ${tab === 'apis' ? 'active' : ''}`} onClick={() => setTab('apis')}>
          APIs
        </button>
      </div>

      {(tab === 'overview' || tab === 'websites') && (
        <div className="panel">
          <div className="panel-header">
            <h2>Websites</h2>
            <div className="meta">Avg response: {formatMs(data.average_response_time)}</div>
          </div>
          <div className="table-wrap">
            {websites.length === 0 ? (
              <div className="empty">
                <p>No websites in this project.</p>
                <button className="btn btn-primary" onClick={() => navigate('/websites')}>Add website</button>
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
                    <th>Uptime</th>
                    <th>Last Checked</th>
                  </tr>
                </thead>
                <tbody>
                  {websites.map((site) => (
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
      )}

      {(tab === 'overview' || tab === 'apis') && (
        <div className="panel">
          <div className="panel-header">
            <h2>APIs</h2>
            <div className="meta">{data.apis_up ?? 0} / {apis.length} operational</div>
          </div>
          <div className="table-wrap">
            {apis.length === 0 ? (
              <div className="empty">
                <p>No APIs in this project.</p>
                <button className="btn btn-primary" onClick={() => navigate('/apis')}>Add API</button>
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
                    <th>Uptime</th>
                    <th>Last Checked</th>
                  </tr>
                </thead>
                <tbody>
                  {apis.map((api) => (
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
                      <td className="mono">{formatUptime(api.uptime)}</td>
                      <td>{timeAgo(api.last_checked)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
