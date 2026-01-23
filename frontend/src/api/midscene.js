import api from '@/utils/api'

export function getConfigs(params) {
  return api.get('/midscene/configs/', { params })
}

export function createConfig(data) {
  return api.post('/midscene/configs/', data)
}

export function updateConfig(id, data) {
  return api.put(`/midscene/configs/${id}/`, data)
}

export function deleteConfig(id) {
  return api.delete(`/midscene/configs/${id}/`)
}

export function testConfigConnection(id) {
  return api.post(`/midscene/configs/${id}/test_connection/`)
}

export function getTasks(params) {
  return api.get('/midscene/tasks/', { params })
}

export function getTask(id) {
  return api.get(`/midscene/tasks/${id}/`)
}

export function createTask(data) {
  return api.post('/midscene/tasks/', data)
}

export function updateTask(id, data) {
  return api.put(`/midscene/tasks/${id}/`, data)
}

export function deleteTask(id) {
  return api.delete(`/midscene/tasks/${id}/`)
}

export function executeTask(id) {
  return api.post(`/midscene/tasks/${id}/execute/`)
}

export function stopTask(id) {
  return api.post(`/midscene/tasks/${id}/stop/`)
}

export function getExecutionLogs(params) {
  return api.get('/midscene/execution-logs/', { params })
}

export function deleteExecutionLog(id) {
  return api.delete(`/midscene/execution-logs/${id}/`)
}

export function executeQuickMidsceneTask(data) {
  return api.post('/midscene/tasks/execute_quick/', data)
}

export function getMidsceneTasks(params) {
  return getTasks(params)
}

export function getMidsceneConfigs(params) {
  return getConfigs(params)
}

export function getDashboardSummary() {
  return api.get('/midscene/dashboard/summary/')
}
