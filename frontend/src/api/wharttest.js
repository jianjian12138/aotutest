import request from '@/utils/api'

// WHartTest配置API
export function getWHartTestConfigs(params) {
  return request({
    url: '/wharttest/configs/',
    method: 'get',
    params
  })
}

export function createWHartTestConfig(data) {
  return request({
    url: '/wharttest/configs/',
    method: 'post',
    data
  })
}

export function updateWHartTestConfig(id, data) {
  return request({
    url: `/wharttest/configs/${id}/`,
    method: 'put',
    data
  })
}

export function deleteWHartTestConfig(id) {
  return request({
    url: `/wharttest/configs/${id}/`,
    method: 'delete'
  })
}

export function testWHartTestConfigConnection(id) {
  return request({
    url: `/wharttest/configs/${id}/test_connection/`,
    method: 'post'
  })
}

// WHartTest项目API
export function getWHartTestProjects(params) {
  return request({
    url: '/wharttest/projects/',
    method: 'get',
    params
  })
}

export function createWHartTestProject(data) {
  return request({
    url: '/wharttest/projects/',
    method: 'post',
    data
  })
}

export function updateWHartTestProject(id, data) {
  return request({
    url: `/wharttest/projects/${id}/`,
    method: 'put',
    data
  })
}

export function deleteWHartTestProject(id) {
  return request({
    url: `/wharttest/projects/${id}/`,
    method: 'delete'
  })
}

export function getWHartTestProject(id) {
  return request({
    url: `/wharttest/projects/${id}/`,
    method: 'get'
  })
}

// WHartTest任务API
export function getWHartTestTasks(params) {
  return request({
    url: '/wharttest/tasks/',
    method: 'get',
    params
  })
}

export function createWHartTestTask(data) {
  return request({
    url: '/wharttest/tasks/',
    method: 'post',
    data
  })
}

export function updateWHartTestTask(id, data) {
  return request({
    url: `/wharttest/tasks/${id}/`,
    method: 'put',
    data
  })
}

export function deleteWHartTestTask(id) {
  return request({
    url: `/wharttest/tasks/${id}/`,
    method: 'delete'
  })
}

export function getWHartTestTask(id) {
  return request({
    url: `/wharttest/tasks/${id}/`,
    method: 'get'
  })
}

// WHartTest执行记录API
export function getWHartTestExecutions(params) {
  return request({
    url: '/wharttest/executions/',
    method: 'get',
    params
  })
}

export function createWHartTestExecution(data) {
  return request({
    url: '/wharttest/executions/',
    method: 'post',
    data
  })
}

export function deleteWHartTestExecution(id) {
  return request({
    url: `/wharttest/executions/${id}/`,
    method: 'delete'
  })
}

export function getWHartTestExecution(id) {
  return request({
    url: `/wharttest/executions/${id}/`,
    method: 'get'
  })
}

export function executeWHartTest(id) {
  return request({
    url: `/wharttest/executions/${id}/execute/`,
    method: 'post'
  })
}

export function stopWHartTest(id) {
  return request({
    url: `/wharttest/executions/${id}/stop/`,
    method: 'post'
  })
}

// WHartTest集成日志API
export function getWHartTestIntegrationLogs(params) {
  return request({
    url: '/wharttest/integration-logs/',
    method: 'get',
    params
  })
}

// 仪表盘API
export function getWHartTestDashboardSummary() {
  return request({
    url: '/wharttest/dashboard/summary/',
    method: 'get'
  })
}
