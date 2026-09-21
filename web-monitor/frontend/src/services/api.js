import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      'Request failed'
    return Promise.reject(new Error(typeof message === 'string' ? message : JSON.stringify(message)))
  }
)

export const getDashboard = () => api.get('/dashboard').then((r) => r.data)
export const getHealth = () => api.get('/health').then((r) => r.data)

export const getProjects = () => api.get('/projects').then((r) => r.data)
export const getProject = (id) => api.get(`/projects/${id}`).then((r) => r.data)
export const createProject = (data) => api.post('/projects', data).then((r) => r.data)
export const updateProject = (id, data) => api.put(`/projects/${id}`, data).then((r) => r.data)
export const deleteProject = (id) => api.delete(`/projects/${id}`).then((r) => r.data)
export const getProjectDetails = (id) => api.get(`/projects/${id}/details`).then((r) => r.data)

export const getWebsites = (projectId) =>
  api.get('/websites', { params: projectId ? { project_id: projectId } : {} }).then((r) => r.data)
export const createWebsite = (data) => api.post('/websites', data).then((r) => r.data)
export const updateWebsite = (id, data) => api.put(`/websites/${id}`, data).then((r) => r.data)
export const deleteWebsite = (id) => api.delete(`/websites/${id}`).then((r) => r.data)
export const getWebsiteDetails = (id, range = '24h') =>
  api.get(`/websites/${id}/details`, { params: { range } }).then((r) => r.data)

export const getLogs = (params) => api.get('/logs', { params }).then((r) => r.data)
export const exportLogsUrl = (params) => {
  const qs = new URLSearchParams()
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.set(k, v)
  })
  return `/api/logs/export?${qs.toString()}`
}

export const getEmailSettings = () => api.get('/settings/email').then((r) => r.data)
export const updateEmailSettings = (data) => api.put('/settings/email', data).then((r) => r.data)
export const testEmail = (recipient) =>
  api.post('/settings/email/test', recipient ? { recipient } : {}).then((r) => r.data)

export default api
