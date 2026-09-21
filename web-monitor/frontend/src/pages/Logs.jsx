import { useEffect, useState } from 'react'
import { StatusBadge, formatMs, formatDateTime } from '../components/StatusBadge'
import { useToast } from '../components/Toast'
import { exportLogsUrl, getLogs, getProjects, getWebsites } from '../services/api'

const emptyFilters = {
  project_id: '',
  website_id: '',
  status: '',
  date_from: '',
  date_to: '',
}

export default function Logs() {
  const toast = useToast()
  const [projects, setProjects] = useState([])
  const [websites, setWebsites] = useState([])
  const [filters, setFilters] = useState(emptyFilters)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    ;(async () => {
      try {
        const [p, w] = await Promise.all([getProjects(), getWebsites()])
        setProjects(p)
        setWebsites(w)
      } catch (err) {
        toast.push(err.message, 'error')
      }
    })()
    search()
  }, [])

  const search = async () => {
    setLoading(true)
    try {
      const params = {}
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params[k] = v
      })
      const data = await getLogs({ ...params, limit: 2000 })
      setLogs(data.logs || [])
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async () => {
    setFilters(emptyFilters)
    setLoading(true)
    try {
      const data = await getLogs({ limit: 2000 })
      setLogs(data.logs || [])
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const download = (format) => {
    const params = { format }
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params[k] = v
    })
    window.open(exportLogsUrl(params), '_blank')
  }

  const filteredWebsites = filters.project_id
    ? websites.filter((w) => w.project_id === filters.project_id)
    : websites

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Logs</h1>
          <p>Search and export monitoring check history (up to 31 days)</p>
        </div>
        <div className="header-actions">
          <button className="btn" onClick={() => download('csv')}>Download CSV</button>
          <button className="btn" onClick={() => download('json')}>Download JSON</button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-body">
          <div className="filters">
            <div className="field">
              <label>Project</label>
              <select
                value={filters.project_id}
                onChange={(e) =>
                  setFilters({ ...filters, project_id: e.target.value, website_id: '' })
                }
              >
                <option value="">All</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Website</label>
              <select
                value={filters.website_id}
                onChange={(e) => setFilters({ ...filters, website_id: e.target.value })}
              >
                <option value="">All</option>
                {filteredWebsites.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="">All</option>
                <option value="UP">UP</option>
                <option value="DOWN">DOWN</option>
              </select>
            </div>
            <div className="field">
              <label>Date From</label>
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Date To</label>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" onClick={search}>Search</button>
              <button className="btn" onClick={handleReset}>Reset</button>
            </div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Results</h2>
          <div className="meta">{logs.length} rows</div>
        </div>
        {loading ? (
          <div className="loading">Loading logs…</div>
        ) : logs.length === 0 ? (
          <div className="empty">
            <h3>No log entries found.</h3>
            <p>Try adjusting filters or wait for the monitoring engine to collect checks.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Project</th>
                  <th>Website</th>
                  <th>URL</th>
                  <th>Status</th>
                  <th>HTTP</th>
                  <th>Response</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((row, idx) => (
                  <tr key={`${row.timestamp}-${row.website_id}-${idx}`}>
                    <td className="mono">{formatDateTime(row.timestamp)}</td>
                    <td>{row.project_name}</td>
                    <td>{row.website_name}</td>
                    <td className="url-cell mono">{row.url}</td>
                    <td><StatusBadge status={row.status} /></td>
                    <td className="mono">{row.status_code ?? '—'}</td>
                    <td className="mono">{formatMs(row.response_time)}</td>
                    <td>{row.error || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
