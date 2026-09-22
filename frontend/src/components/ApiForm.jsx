const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const INTERVAL_PRESETS = [10, 15, 30, 45, 60, 90, 120]
const OPERATORS = [
  { id: 'equals', label: 'equals' },
  { id: 'not_equals', label: 'not equals' },
  { id: 'contains', label: 'contains' },
  { id: 'not_contains', label: 'not contains' },
  { id: 'exists', label: 'exists' },
  { id: 'not_exists', label: 'not exists' },
]
const BODY_METHODS = ['POST', 'PUT', 'PATCH']

export function emptyApiForm(projectId = '') {
  return {
    project_id: projectId,
    name: '',
    url: '',
    method: 'GET',
    enabled: true,
    check_interval: 60,
    timeout: 10,
    expected_status_code: 200,
    alert_enabled: true,
    custom_interval: false,
    headers: [{ key: '', value: '' }],
    body: '',
    auth_type: 'none',
    bearer_token: '',
    auth_username: '',
    auth_password: '',
    api_key_name: '',
    api_key_value: '',
    api_key_in: 'header',
    validation_enabled: false,
    validation_rules: [],
  }
}

export function apiToForm(api) {
  const preset = INTERVAL_PRESETS.includes(api.check_interval)
  const headers = Object.entries(api.headers || {}).map(([key, value]) => ({ key, value }))
  return {
    project_id: api.project_id,
    name: api.name,
    url: api.url,
    method: api.method || 'GET',
    enabled: api.enabled,
    check_interval: api.check_interval,
    timeout: api.timeout,
    expected_status_code: api.expected_status_code,
    alert_enabled: api.alert_enabled,
    custom_interval: !preset,
    headers: headers.length ? headers : [{ key: '', value: '' }],
    body: api.body || '',
    auth_type: api.auth_type || 'none',
    bearer_token: '',
    auth_username: api.auth_username || '',
    auth_password: '',
    api_key_name: api.api_key_name || '',
    api_key_value: '',
    api_key_in: api.api_key_in || 'header',
    validation_enabled: !!api.validation_enabled,
    validation_rules: (api.validation_rules || []).map((rule) => ({
      field: rule.field,
      operator: rule.operator,
      value: rule.value ?? '',
    })),
    bearer_configured: api.bearer_configured,
    password_configured: api.password_configured,
    api_key_configured: api.api_key_configured,
  }
}

export function buildApiPayload(form) {
  const interval = Number(form.check_interval)
  if (interval < 10 || interval > 120) {
    throw new Error('Check interval must be between 10 and 120 seconds')
  }
  const headers = {}
  form.headers.forEach((row) => {
    const key = (row.key || '').trim()
    if (key) headers[key] = row.value || ''
  })
  const contentType = Object.entries(headers).find(([k]) => k.toLowerCase() === 'content-type')?.[1] || ''
  const body = form.body || ''
  if (BODY_METHODS.includes(form.method) && body.trim()) {
    if (contentType.toLowerCase().includes('application/json') || body.trim().startsWith('{') || body.trim().startsWith('[')) {
      try {
        JSON.parse(body)
      } catch {
        throw new Error('Request body must be valid JSON')
      }
    }
  }
  if (form.validation_enabled) {
    form.validation_rules.forEach((rule) => {
      if (!(rule.field || '').trim()) throw new Error('Each validation rule needs a JSON field')
    })
  }
  const payload = {
    project_id: form.project_id,
    name: form.name,
    url: form.url,
    method: form.method,
    enabled: form.enabled,
    check_interval: interval,
    timeout: Number(form.timeout),
    expected_status_code: Number(form.expected_status_code),
    alert_enabled: form.alert_enabled,
    headers,
    body: BODY_METHODS.includes(form.method) ? body : '',
    auth_type: form.auth_type,
    auth_username: form.auth_username,
    api_key_name: form.api_key_name,
    api_key_in: form.api_key_in,
    validation_enabled: form.validation_enabled,
    validation_rules: form.validation_enabled
      ? form.validation_rules
          .filter((rule) => (rule.field || '').trim())
          .map((rule) => ({
            field: rule.field.trim(),
            operator: rule.operator,
            value: ['exists', 'not_exists'].includes(rule.operator) ? null : rule.value,
          }))
      : [],
  }
  if (form.bearer_token) payload.bearer_token = form.bearer_token
  if (form.auth_password) payload.auth_password = form.auth_password
  if (form.api_key_value) payload.api_key_value = form.api_key_value
  return payload
}

export default function ApiForm({ form, setForm, projects }) {
  const bodyEnabled = BODY_METHODS.includes(form.method)
  const update = (patch) => setForm({ ...form, ...patch })

  const setHeader = (index, patch) => {
    const headers = form.headers.map((row, i) => (i === index ? { ...row, ...patch } : row))
    update({ headers })
  }

  const setRule = (index, patch) => {
    const validation_rules = form.validation_rules.map((row, i) => (i === index ? { ...row, ...patch } : row))
    update({ validation_rules })
  }

  return (
    <div className="form-grid">
      <div className="field full">
        <label>Project</label>
        <select value={form.project_id} onChange={(e) => update({ project_id: e.target.value })}>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>API Name</label>
        <input value={form.name} onChange={(e) => update({ name: e.target.value })} />
      </div>
      <div className="field">
        <label>HTTP Method</label>
        <select value={form.method} onChange={(e) => update({ method: e.target.value })}>
          {HTTP_METHODS.map((method) => (
            <option key={method} value={method}>{method}</option>
          ))}
        </select>
      </div>
      <div className="field full">
        <label>URL</label>
        <input value={form.url} onChange={(e) => update({ url: e.target.value })} placeholder="https://api.example.com/health" />
      </div>
      <div className="field">
        <label>Check interval</label>
        <select
          value={form.custom_interval ? 'custom' : form.check_interval}
          onChange={(e) => {
            if (e.target.value === 'custom') update({ custom_interval: true })
            else update({ custom_interval: false, check_interval: Number(e.target.value) })
          }}
        >
          {INTERVAL_PRESETS.map((v) => (
            <option key={v} value={v}>{v} seconds</option>
          ))}
          <option value="custom">Custom (10–120)</option>
        </select>
      </div>
      {form.custom_interval && (
        <div className="field">
          <label>Custom interval (seconds)</label>
          <input
            type="number"
            min={10}
            max={120}
            value={form.check_interval}
            onChange={(e) => update({ check_interval: Number(e.target.value) })}
          />
        </div>
      )}
      <div className="field">
        <label>Timeout (seconds)</label>
        <input type="number" min={1} max={60} value={form.timeout} onChange={(e) => update({ timeout: Number(e.target.value) })} />
      </div>
      <div className="field">
        <label>Expected status code</label>
        <input
          type="number"
          min={100}
          max={599}
          value={form.expected_status_code}
          onChange={(e) => update({ expected_status_code: Number(e.target.value) })}
        />
      </div>
      <div className="field full">
        <label>Authentication</label>
        <select value={form.auth_type} onChange={(e) => update({ auth_type: e.target.value })}>
          <option value="none">No Authentication</option>
          <option value="bearer">Bearer Token</option>
          <option value="basic">Basic Authentication</option>
          <option value="api_key">API Key</option>
          <option value="custom_headers">Custom Headers</option>
        </select>
      </div>
      {form.auth_type === 'bearer' && (
        <div className="field full">
          <label>Token</label>
          <input
            type="password"
            autoComplete="new-password"
            placeholder={form.bearer_configured ? 'Leave blank to keep existing token' : 'Bearer token'}
            value={form.bearer_token}
            onChange={(e) => update({ bearer_token: e.target.value })}
          />
        </div>
      )}
      {form.auth_type === 'basic' && (
        <>
          <div className="field">
            <label>Username</label>
            <input value={form.auth_username} onChange={(e) => update({ auth_username: e.target.value })} />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              autoComplete="new-password"
              placeholder={form.password_configured ? 'Leave blank to keep existing password' : ''}
              value={form.auth_password}
              onChange={(e) => update({ auth_password: e.target.value })}
            />
          </div>
        </>
      )}
      {form.auth_type === 'api_key' && (
        <>
          <div className="field">
            <label>Key name</label>
            <input value={form.api_key_name} onChange={(e) => update({ api_key_name: e.target.value })} placeholder="X-API-Key" />
          </div>
          <div className="field">
            <label>Send in</label>
            <select value={form.api_key_in} onChange={(e) => update({ api_key_in: e.target.value })}>
              <option value="header">Header</option>
              <option value="query">Query parameter</option>
            </select>
          </div>
          <div className="field full">
            <label>API key</label>
            <input
              type="password"
              autoComplete="new-password"
              placeholder={form.api_key_configured ? 'Leave blank to keep existing key' : ''}
              value={form.api_key_value}
              onChange={(e) => update({ api_key_value: e.target.value })}
            />
          </div>
        </>
      )}
      <div className="field full">
        <label>Headers</label>
        {form.headers.map((row, index) => (
          <div className="kv-row" key={`header-${index}`}>
            <input placeholder="Key" value={row.key} onChange={(e) => setHeader(index, { key: e.target.value })} />
            <input
              placeholder="Value"
              type={/authorization|token|secret|password|api-key|apikey/i.test(row.key) ? 'password' : 'text'}
              value={row.value}
              onChange={(e) => setHeader(index, { value: e.target.value })}
            />
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => update({ headers: form.headers.filter((_, i) => i !== index) })}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => update({ headers: [...form.headers, { key: '', value: '' }] })}
        >
          Add Header
        </button>
      </div>
      <div className="field full">
        <label>Request body {bodyEnabled ? '(JSON)' : '(disabled for this method)'}</label>
        <textarea
          className="mono"
          disabled={!bodyEnabled}
          value={bodyEnabled ? form.body : ''}
          onChange={(e) => update({ body: e.target.value })}
          placeholder='{ "environment": "production" }'
        />
      </div>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={form.validation_enabled}
          onChange={(e) => update({ validation_enabled: e.target.checked })}
        />
        Enable response validation
      </label>
      {form.validation_enabled && (
        <div className="field full">
          <label>Response validation rules</label>
          {form.validation_rules.map((rule, index) => (
            <div className="kv-row three" key={`rule-${index}`}>
              <input placeholder="JSON field (e.g. data.status)" value={rule.field} onChange={(e) => setRule(index, { field: e.target.value })} />
              <select value={rule.operator} onChange={(e) => setRule(index, { operator: e.target.value })}>
                {OPERATORS.map((op) => (
                  <option key={op.id} value={op.id}>{op.label}</option>
                ))}
              </select>
              <input
                placeholder="Expected value"
                disabled={['exists', 'not_exists'].includes(rule.operator)}
                value={rule.value}
                onChange={(e) => setRule(index, { value: e.target.value })}
              />
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => update({ validation_rules: form.validation_rules.filter((_, i) => i !== index) })}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-sm"
            onClick={() =>
              update({
                validation_rules: [...form.validation_rules, { field: '', operator: 'equals', value: '' }],
              })
            }
          >
            Add rule
          </button>
        </div>
      )}
      <label className="checkbox-row">
        <input type="checkbox" checked={form.enabled} onChange={(e) => update({ enabled: e.target.checked })} />
        Enabled
      </label>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={form.alert_enabled}
          onChange={(e) => update({ alert_enabled: e.target.checked })}
        />
        Email alerts enabled
      </label>
    </div>
  )
}
