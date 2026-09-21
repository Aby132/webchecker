import { useEffect, useState } from 'react'
import Modal from '../components/Modal'
import { useToast } from '../components/Toast'
import { StatusBadge } from '../components/StatusBadge'
import {
  createProject,
  createWebsite,
  deleteProject,
  deleteWebsite,
  getProjects,
  getWebsites,
  updateProject,
  updateWebsite,
} from '../services/api'
import EmailAlerts from './EmailAlerts'

const INTERVAL_PRESETS = [10, 15, 30, 45, 60, 90, 120]

const emptyProject = { name: '', description: '', enabled: true }
const emptyWebsite = {
  project_id: '',
  name: '',
  url: '',
  enabled: true,
  check_interval: 60,
  timeout: 10,
  expected_status_code: 200,
  alert_enabled: true,
  custom_interval: false,
}

export default function Configuration({ initialTab = 'projects' }) {
  const toast = useToast()
  const [tab, setTab] = useState(initialTab)
  const [projects, setProjects] = useState([])
  const [websites, setWebsites] = useState([])
  const [loading, setLoading] = useState(true)

  const [projectModal, setProjectModal] = useState(null)
  const [websiteModal, setWebsiteModal] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const [formProject, setFormProject] = useState(emptyProject)
  const [formWebsite, setFormWebsite] = useState(emptyWebsite)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [p, w] = await Promise.all([getProjects(), getWebsites()])
      setProjects(p)
      setWebsites(w)
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openCreateProject = () => {
    setFormProject(emptyProject)
    setProjectModal('create')
  }

  const openEditProject = (project) => {
    setFormProject({
      name: project.name,
      description: project.description || '',
      enabled: project.enabled,
    })
    setProjectModal(project)
  }

  const saveProject = async () => {
    setSaving(true)
    try {
      if (projectModal === 'create') {
        await createProject(formProject)
        toast.push('Project created')
      } else {
        await updateProject(projectModal.id, formProject)
        toast.push('Project updated')
      }
      setProjectModal(null)
      await load()
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const openCreateWebsite = () => {
    setFormWebsite({
      ...emptyWebsite,
      project_id: projects[0]?.id || '',
    })
    setWebsiteModal('create')
  }

  const openEditWebsite = (site) => {
    const preset = INTERVAL_PRESETS.includes(site.check_interval)
    setFormWebsite({
      project_id: site.project_id,
      name: site.name,
      url: site.url,
      enabled: site.enabled,
      check_interval: site.check_interval,
      timeout: site.timeout,
      expected_status_code: site.expected_status_code,
      alert_enabled: site.alert_enabled,
      custom_interval: !preset,
    })
    setWebsiteModal(site)
  }

  const saveWebsite = async () => {
    const interval = Number(formWebsite.check_interval)
    if (interval < 10 || interval > 120) {
      toast.push('Check interval must be between 10 and 120 seconds', 'error')
      return
    }
    setSaving(true)
    try {
      const payload = {
        project_id: formWebsite.project_id,
        name: formWebsite.name,
        url: formWebsite.url,
        enabled: formWebsite.enabled,
        check_interval: interval,
        timeout: Number(formWebsite.timeout),
        expected_status_code: Number(formWebsite.expected_status_code),
        alert_enabled: formWebsite.alert_enabled,
      }
      if (websiteModal === 'create') {
        await createWebsite(payload)
        toast.push('Website added')
      } else {
        await updateWebsite(websiteModal.id, payload)
        toast.push('Website updated')
      }
      setWebsiteModal(null)
      await load()
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const runConfirm = async () => {
    if (!confirm) return
    setSaving(true)
    try {
      if (confirm.type === 'project') {
        await deleteProject(confirm.id)
        toast.push('Project deleted')
      } else {
        await deleteWebsite(confirm.id)
        toast.push('Website deleted')
      }
      setConfirm(null)
      await load()
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const toggleProject = async (project) => {
    try {
      await updateProject(project.id, { enabled: !project.enabled })
      await load()
    } catch (err) {
      toast.push(err.message, 'error')
    }
  }

  const toggleWebsite = async (site) => {
    try {
      await updateWebsite(site.id, { enabled: !site.enabled })
      await load()
    } catch (err) {
      toast.push(err.message, 'error')
    }
  }

  const projectName = (id) => projects.find((p) => p.id === id)?.name || id

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Configuration</h1>
          <p>Manage projects, websites, and monitoring settings</p>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === 'projects' ? 'active' : ''}`} onClick={() => setTab('projects')}>
          Projects
        </button>
        <button className={`tab ${tab === 'websites' ? 'active' : ''}`} onClick={() => setTab('websites')}>
          Websites
        </button>
        <button className={`tab ${tab === 'email' ? 'active' : ''}`} onClick={() => setTab('email')}>
          Email Alerts
        </button>
      </div>

      {tab === 'email' ? (
        <EmailAlerts embedded />
      ) : loading ? (
        <div className="loading">Loading…</div>
      ) : tab === 'projects' ? (
        <div className="panel">
          <div className="panel-header">
            <h2>Projects</h2>
            <button className="btn btn-primary btn-sm" onClick={openCreateProject}>Create project</button>
          </div>
          {projects.length === 0 ? (
            <div className="empty">
              <h3>No projects yet.</h3>
              <p>Create a project to group your monitored websites.</p>
              <button className="btn btn-primary" onClick={openCreateProject}>Create project</button>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Enabled</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((p) => (
                    <tr key={p.id}>
                      <td>{p.name}</td>
                      <td>{p.description || '—'}</td>
                      <td><StatusBadge status={p.enabled ? 'UP' : 'DISABLED'} /></td>
                      <td style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-sm" onClick={() => openEditProject(p)}>Edit</button>
                        <button className="btn btn-sm" onClick={() => toggleProject(p)}>
                          {p.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => setConfirm({ type: 'project', id: p.id, name: p.name })}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="panel">
          <div className="panel-header">
            <h2>Websites</h2>
            <button
              className="btn btn-primary btn-sm"
              onClick={openCreateWebsite}
              disabled={!projects.length}
            >
              Add website
            </button>
          </div>
          {websites.length === 0 ? (
            <div className="empty">
              <h3>No websites configured yet.</h3>
              <p>Add your first website to start monitoring.</p>
              <button className="btn btn-primary" onClick={openCreateWebsite} disabled={!projects.length}>
                Add website
              </button>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Project</th>
                    <th>URL</th>
                    <th>Interval</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {websites.map((w) => (
                    <tr key={w.id}>
                      <td>{w.name}</td>
                      <td>{projectName(w.project_id)}</td>
                      <td className="url-cell mono">{w.url}</td>
                      <td className="mono">{w.check_interval}s</td>
                      <td><StatusBadge status={w.enabled ? w.status : 'DISABLED'} /></td>
                      <td style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-sm" onClick={() => openEditWebsite(w)}>Edit</button>
                        <button className="btn btn-sm" onClick={() => toggleWebsite(w)}>
                          {w.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => setConfirm({ type: 'website', id: w.id, name: w.name })}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {projectModal && (
        <Modal
          title={projectModal === 'create' ? 'Create project' : 'Edit project'}
          onClose={() => setProjectModal(null)}
          footer={
            <>
              <button className="btn" onClick={() => setProjectModal(null)}>Cancel</button>
              <button className="btn btn-primary" disabled={saving} onClick={saveProject}>
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          }
        >
          <div className="form-grid one">
            <div className="field">
              <label>Name</label>
              <input
                value={formProject.name}
                onChange={(e) => setFormProject({ ...formProject, name: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Description</label>
              <textarea
                value={formProject.description}
                onChange={(e) => setFormProject({ ...formProject, description: e.target.value })}
              />
            </div>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={formProject.enabled}
                onChange={(e) => setFormProject({ ...formProject, enabled: e.target.checked })}
              />
              Enabled
            </label>
          </div>
        </Modal>
      )}

      {websiteModal && (
        <Modal
          title={websiteModal === 'create' ? 'Add website' : 'Edit website'}
          onClose={() => setWebsiteModal(null)}
          footer={
            <>
              <button className="btn" onClick={() => setWebsiteModal(null)}>Cancel</button>
              <button className="btn btn-primary" disabled={saving} onClick={saveWebsite}>
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          }
        >
          <div className="form-grid">
            <div className="field full">
              <label>Project</label>
              <select
                value={formWebsite.project_id}
                onChange={(e) => setFormWebsite({ ...formWebsite, project_id: e.target.value })}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Name</label>
              <input
                value={formWebsite.name}
                onChange={(e) => setFormWebsite({ ...formWebsite, name: e.target.value })}
              />
            </div>
            <div className="field">
              <label>URL</label>
              <input
                value={formWebsite.url}
                onChange={(e) => setFormWebsite({ ...formWebsite, url: e.target.value })}
                placeholder="https://example.com"
              />
            </div>
            <div className="field">
              <label>Check interval</label>
              <select
                value={formWebsite.custom_interval ? 'custom' : formWebsite.check_interval}
                onChange={(e) => {
                  if (e.target.value === 'custom') {
                    setFormWebsite({ ...formWebsite, custom_interval: true })
                  } else {
                    setFormWebsite({
                      ...formWebsite,
                      custom_interval: false,
                      check_interval: Number(e.target.value),
                    })
                  }
                }}
              >
                {INTERVAL_PRESETS.map((v) => (
                  <option key={v} value={v}>{v} seconds</option>
                ))}
                <option value="custom">Custom (10–120)</option>
              </select>
            </div>
            {formWebsite.custom_interval && (
              <div className="field">
                <label>Custom interval (seconds)</label>
                <input
                  type="number"
                  min={10}
                  max={120}
                  value={formWebsite.check_interval}
                  onChange={(e) =>
                    setFormWebsite({ ...formWebsite, check_interval: Number(e.target.value) })
                  }
                />
              </div>
            )}
            <div className="field">
              <label>Timeout (seconds)</label>
              <input
                type="number"
                min={1}
                max={60}
                value={formWebsite.timeout}
                onChange={(e) => setFormWebsite({ ...formWebsite, timeout: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label>Expected status code</label>
              <input
                type="number"
                min={100}
                max={599}
                value={formWebsite.expected_status_code}
                onChange={(e) =>
                  setFormWebsite({ ...formWebsite, expected_status_code: Number(e.target.value) })
                }
              />
            </div>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={formWebsite.enabled}
                onChange={(e) => setFormWebsite({ ...formWebsite, enabled: e.target.checked })}
              />
              Enabled
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={formWebsite.alert_enabled}
                onChange={(e) => setFormWebsite({ ...formWebsite, alert_enabled: e.target.checked })}
              />
              Email alerts enabled
            </label>
          </div>
        </Modal>
      )}

      {confirm && (
        <Modal
          title="Confirm delete"
          onClose={() => setConfirm(null)}
          footer={
            <>
              <button className="btn" onClick={() => setConfirm(null)}>Cancel</button>
              <button className="btn btn-danger" disabled={saving} onClick={runConfirm}>
                {saving ? 'Deleting…' : 'Delete'}
              </button>
            </>
          }
        >
          <p>
            Delete <strong>{confirm.name}</strong>?
            {confirm.type === 'project'
              ? ' This will also remove associated websites and their log entries.'
              : ' This will also remove related log entries.'}
          </p>
        </Modal>
      )}
    </div>
  )
}
