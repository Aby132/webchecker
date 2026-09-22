import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import usePolling from '../hooks/usePolling'
import { getWebsiteDetails } from '../services/api'
import { StatusBadge, formatMs, formatUptime, formatDateTime, timeAgo } from '../components/StatusBadge'
import {
  ResponseTimeChart,
  StatusCodeChart,
  StatusTimeline,
  UptimeBars,
} from '../charts/MonitoringCharts'

const RANGES = [
  { id: '1h', label: 'Last 1 hour' },
  { id: '6h', label: 'Last 6 hours' },
  { id: '24h', label: 'Last 24 hours' },
  { id: '7d', label: 'Last 7 days' },
  { id: '30d', label: 'Last 30 days' },
]

export default function WebsiteDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [range, setRange] = useState('24h')
  const { data, error, loading } = usePolling(() => getWebsiteDetails(id, range), 5000, [id, range])

  if (loading && !data) return <div className="loading">Loading website…</div>
  if (error && !data) return <div className="error-box">{error}</div>
  if (!data) return null

  const site = data.website
  const project = data.project

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{site.name}</h1>
          <p>
            {project?.name || 'Unknown project'} · <span className="mono">{site.url}</span>
          </p>
        </div>
        <div className="header-actions">
          <button className="btn" onClick={() => navigate(project ? `/projects/${project.id}` : '/')}>
            Back
          </button>
        </div>
      </div>

      <div className="stat-row">
        <div className="kpi">
          <div className="kpi-label">Status</div>
          <div style={{ marginTop: 10 }}><StatusBadge status={site.enabled ? site.status : 'DISABLED'} /></div>
        </div>
        <div className="kpi">
          <div className="kpi-label">HTTP Status</div>
          <div className="kpi-value" style={{ fontSize: 24 }}>{site.last_status_code ?? '—'}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Response Time</div>
          <div className="kpi-value" style={{ fontSize: 22 }}>{formatMs(site.last_response_time)}</div>
        </div>
        <div className="kpi accent">
          <div className="kpi-label">Uptime ({range})</div>
          <div className="kpi-value" style={{ fontSize: 22 }}>{formatUptime(data.uptime)}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-body">
          <div className="form-grid">
            <div><strong>Last checked:</strong> {timeAgo(site.last_checked)}</div>
            <div><strong>Check interval:</strong> {site.check_interval}s</div>
            <div><strong>Timeout:</strong> {site.timeout}s</div>
            <div><strong>Expected status:</strong> {site.expected_status_code}</div>
            <div><strong>Current incident:</strong> {data.incident_duration || 'None'}</div>
            <div><strong>Last error:</strong> {site.last_error || '—'}</div>
          </div>
        </div>
      </div>

      <div className="tabs">
        {RANGES.map((r) => (
          <button
            key={r.id}
            className={`tab ${range === r.id ? 'active' : ''}`}
            onClick={() => setRange(r.id)}
          >
            {r.label}
          </button>
        ))}
      </div>

      <div className="charts-grid">
        <div className="panel chart-panel">
          <div className="panel-header"><h2>Response Time</h2></div>
          <div className="panel-body">
            <ResponseTimeChart data={data.response_time_series} />
          </div>
        </div>
        <div className="panel chart-panel">
          <div className="panel-header"><h2>Uptime</h2></div>
          <div className="panel-body">
            <UptimeBars windows={data.uptime_windows} />
          </div>
        </div>
        <div className="panel chart-panel">
          <div className="panel-header"><h2>Status Timeline</h2></div>
          <div className="panel-body">
            <StatusTimeline points={data.status_timeline} />
          </div>
        </div>
        <div className="panel chart-panel">
          <div className="panel-header"><h2>HTTP Status Codes</h2></div>
          <div className="panel-body">
            <StatusCodeChart distribution={data.status_codes} />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header"><h2>Incident History</h2></div>
        <div className="panel-body">
          {!data.incidents?.length ? (
            <div className="empty"><p>No incidents recorded yet.</p></div>
          ) : (
            <div className="incident-list">
              {data.incidents.map((inc, idx) => (
                <div className="incident" key={`${inc.started_at}-${idx}`}>
                  <div className="icon">{inc.ended_at ? '🟢' : '🔴'}</div>
                  <div>
                    <div className="title">
                      {formatDateTime(inc.started_at)}
                      {inc.ended_at ? ' — Recovered' : ' — Ongoing'}
                    </div>
                    <div className="sub">
                      {inc.status_code ? `HTTP ${inc.status_code}` : ''}
                      {inc.error ? ` ${inc.error}` : ''}
                      {inc.duration_seconds != null
                        ? ` · Duration: ${Math.floor(inc.duration_seconds / 60)}m ${inc.duration_seconds % 60}s`
                        : data.incident_duration && !inc.ended_at
                          ? ` · Duration: ${data.incident_duration}`
                          : ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
