import request from '@/utils/api'

// Midscene配置相关API
export function getMidsceneConfigs(params) {
  return request({
    url: '/api/midscene/configs/',
    method: 'get',
    params
  })
}

export function createMidsceneConfig(data) {
  return request({
    url: '/api/midscene/configs/',
    method: 'post',
    data
  })
}

export function getMidsceneConfig(id) {
  return request({
    url: `/api/midscene/configs/${id}/`,
    method: 'get'
  })
}

export function updateMidsceneConfig(id, data) {
  return request({
    url: `/api/midscene/configs/${id}/`,
    method: 'put',
    data
  })
}

export function deleteMidsceneConfig(id) {
  return request({
    url: `/api/midscene/configs/${id}/`,
    method: 'delete'
  })
}

export function testMidsceneConnection(id) {
  return request({
    url: `/api/midscene/configs/${id}/test_connection/`,
    method: 'post'
  })
}

// Midscene任务相关API
export function getMidsceneTasks(params) {
  return request({
    url: '/api/midscene/tasks/',
    method: 'get',
    params
  })
}

export function createMidsceneTask(data) {
  return request({
    url: '/api/midscene/tasks/',
    method: 'post',
    data
  })
}

export function getMidsceneTask(id) {
  return request({
    url: `/api/midscene/tasks/${id}/`,
    method: 'get'
  })
}

export function executeMidsceneTask(id) {
  return request({
    url: `/api/midscene/tasks/${id}/execute/`,
    method: 'post'
  })
}

export function stopMidsceneTask(id) {
  return request({
    url: `/api/midscene/tasks/${id}/stop/`,
    method: 'post'
  })
}

export function deleteMidsceneTask(id) {
  return request({
    url: `/api/midscene/tasks/${id}/`,
    method: 'delete'
  })
}

// 快速执行相关API
export function executeQuickMidsceneTask(data) {
  return request({
    url: '/api/midscene/tasks/execute_quick/',
    method: 'post',
    data
  })
}

// 执行日志相关API
export function getMidsceneExecutionLogs(params) {
  return request({
    url: '/api/midscene/execution-logs/',
    method: 'get',
    params
  })
}

// 仪表板相关API
export function getMidsceneDashboardSummary() {
  return request({
    url: '/api/midscene/dashboard/summary/',
    method: 'get'
  })
}
