import api from '@/utils/api'

// 漏洞相关
export function getVulnerabilities(params) {
  return api.get('/strix-security/vulnerabilities/', { params })
}

export function updateVulnerability(id, data) {
  return api.patch(`/strix-security/vulnerabilities/${id}/`, data)
}

export function getSecurityDashboardStats() {
  return api.get('/strix-security/dashboard/summary/')
}

// 扫描任务相关
export function getSecurityProjects(params) {
  return api.get('/strix-security/projects/', { params })
}

export function getSecurityProject(id) {
  return api.get(`/strix-security/projects/${id}/`)
}

export function createSecurityProject(data) {
  return api.post('/strix-security/projects/', data)
}

export function deleteSecurityProject(id) {
  return api.delete(`/strix-security/projects/${id}/`)
}

export function executeSecurityProject(id) {
  return api.post(`/strix-security/projects/${id}/execute/`)
}

export function getSecurityConfigs(params) {
  return api.get('/strix-security/configs/', { params })
}

// 报告相关 (Assuming report endpoints based on views)
export function getSecurityReports(params) {
  return api.get('/strix-security/executions/', { params })
}

export function getSecurityReportDetail(id) {
  return api.get(`/strix-security/executions/${id}/`)
}

export function downloadSecurityReport(id) {
  return api.get(`/strix-security/executions/${id}/download/`, {
    responseType: 'blob'
  })
}
