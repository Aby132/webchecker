import { useEffect, useState } from 'react'
import { useToast } from '../components/Toast'
import { getEmailSettings, testEmail, updateEmailSettings } from '../services/api'

export default function EmailAlerts({ embedded = false }) {
  const toast = useToast()
  const [form, setForm] = useState({
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    from_email: '',
    recipientsText: '',
    use_tls: true,
    password_configured: false,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    ;(async () => {
      try {
        const data = await getEmailSettings()
        setForm({
          smtp_host: data.smtp_host || '',
          smtp_port: data.smtp_port || 587,
          smtp_username: data.smtp_username || '',
          smtp_password: '',
          from_email: data.from_email || '',
          recipientsText: (data.recipients || []).join('\n'),
          use_tls: data.use_tls !== false,
          password_configured: data.password_configured,
        })
      } catch (err) {
        toast.push(err.message, 'error')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      const recipients = form.recipientsText
        .split(/[\n,;]+/)
        .map((s) => s.trim())
        .filter(Boolean)
      const payload = {
        smtp_host: form.smtp_host,
        smtp_port: Number(form.smtp_port),
        smtp_username: form.smtp_username,
        from_email: form.from_email,
        recipients,
        use_tls: form.use_tls,
      }
      if (form.smtp_password) {
        payload.smtp_password = form.smtp_password
      }
      const data = await updateEmailSettings(payload)
      setForm((prev) => ({
        ...prev,
        smtp_password: '',
        password_configured: data.password_configured,
        recipientsText: (data.recipients || []).join('\n'),
      }))
      toast.push('Email configuration saved')
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const sendTest = async () => {
    setTesting(true)
    try {
      await testEmail()
      toast.push('Test email sent')
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setTesting(false)
    }
  }

  if (loading) return <div className="loading">Loading email settings…</div>

  return (
    <div>
      {!embedded && (
        <div className="page-header">
          <div>
            <h1>Email Alerts</h1>
            <p>SMTP configuration for DOWN and RECOVERY notifications</p>
          </div>
          <div className="header-actions">
            <button className="btn" disabled={testing} onClick={sendTest}>
              {testing ? 'Sending…' : 'Test Email'}
            </button>
            <button className="btn btn-primary" disabled={saving} onClick={save}>
              {saving ? 'Saving…' : 'Save Configuration'}
            </button>
          </div>
        </div>
      )}

      {embedded && (
        <div className="header-actions" style={{ marginBottom: 14, justifyContent: 'flex-end' }}>
          <button className="btn" disabled={testing} onClick={sendTest}>
            {testing ? 'Sending…' : 'Test Email'}
          </button>
          <button className="btn btn-primary" disabled={saving} onClick={save}>
            {saving ? 'Saving…' : 'Save Configuration'}
          </button>
        </div>
      )}

      <div className="panel">
        <div className="panel-body">
          <div className="form-grid">
            <div className="field">
              <label>SMTP Host</label>
              <input
                value={form.smtp_host}
                onChange={(e) => setForm({ ...form, smtp_host: e.target.value })}
                placeholder="smtp.gmail.com"
              />
            </div>
            <div className="field">
              <label>SMTP Port</label>
              <input
                type="number"
                value={form.smtp_port}
                onChange={(e) => setForm({ ...form, smtp_port: e.target.value })}
              />
            </div>
            <div className="field">
              <label>SMTP Username</label>
              <input
                value={form.smtp_username}
                onChange={(e) => setForm({ ...form, smtp_username: e.target.value })}
              />
            </div>
            <div className="field">
              <label>
                SMTP Password
                {form.password_configured ? ' (configured - leave blank to keep)' : ''}
              </label>
              <input
                type="password"
                value={form.smtp_password}
                onChange={(e) => setForm({ ...form, smtp_password: e.target.value })}
                placeholder={form.password_configured ? '••••••••' : ''}
                autoComplete="new-password"
              />
            </div>
            <div className="field">
              <label>From Email</label>
              <input
                value={form.from_email}
                onChange={(e) => setForm({ ...form, from_email: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Use TLS</label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={form.use_tls}
                  onChange={(e) => setForm({ ...form, use_tls: e.target.checked })}
                />
                STARTTLS / TLS enabled
              </label>
            </div>
            <div className="field full">
              <label>Recipient Emails (one per line)</label>
              <textarea
                value={form.recipientsText}
                onChange={(e) => setForm({ ...form, recipientsText: e.target.value })}
                placeholder={'admin@example.com\ndevops@example.com'}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
