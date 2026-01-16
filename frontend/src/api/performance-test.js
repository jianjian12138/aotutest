import request from '@/utils/api'

// 性能测试项目相关API
export function getPerformanceProjects(params) {
  return request({
    url: '/api/performance/projects/',
    method: 'get',
    params
  })
}

export function createPerformanceProject(data) {
  return request({
    url: '/api/performance/projects/',
    method: 'post',
    data
  })
}

export function getPerformanceProject(id) {
  return request({
    url: `/api/performance/projects/${id}/`,
    method: 'get'
  })
}

export function updatePerformanceProject(id, data) {
  return request({
    url: `/api/performance/projects/${id}/`,
    method: 'put',
    data
  })
}

export function deletePerformanceProject(id) {
  return request({
    url: `/api/performance/projects/${id}/`,
    method: 'delete'
  })
}

// 性能测试集合相关API
export function getPerformanceCollections(params) {
  return request({
    url: '/api/performance/collections/',
    method: 'get',
    params
  })
}

export function createPerformanceCollection(data) {
  return request({
    url: '/api/performance/collections/',
    method: 'post',
    data
  })
}

export function getPerformanceCollection(id) {
  return request({
    url: `/api/performance/collections/${id}/`,
    method: 'get'
  })
}

export function updatePerformanceCollection(id, data) {
  return request({
    url: `/api/performance/collections/${id}/`,
    method: 'put',
    data
  })
}

export function deletePerformanceCollection(id) {
  return request({
    url: `/api/performance/collections/${id}/`,
    method: 'delete'
  })
}

// 性能测试请求相关API
export function getPerformanceRequests(params) {
  return request({
    url: '/api/performance/requests/',
    method: 'get',
    params
  })
}

export function createPerformanceRequest(data) {
  return request({
    url: '/api/performance/requests/',
    method: 'post',
    data
  })
}

export function getPerformanceRequest(id) {
  return request({
    url: `/api/performance/requests/${id}/`,
    method: 'get'
  })
}

export function updatePerformanceRequest(id, data) {
  return request({
    url: `/api/performance/requests/${id}/`,
    method: 'put',
    data
  })
}

export function deletePerformanceRequest(id) {
  return request({
    url: `/api/performance/requests/${id}/`,
    method: 'delete'
  })
}

// 性能测试环境相关API
export function getPerformanceEnvironments(params) {
  return request({
    url: '/api/performance/environments/',
    method: 'get',
    params
  })
}

export function createPerformanceEnvironment(data) {
  return request({
    url: '/api/performance/environments/',
    method: 'post',
    data
  })
}

export function getPerformanceEnvironment(id) {
  return request({
    url: `/api/performance/environments/${id}/`,
    method: 'get'
  })
}

export function updatePerformanceEnvironment(id, data) {
  return request({
    url: `/api/performance/environments/${id}/`,
    method: 'put',
    data
  })
}

export function deletePerformanceEnvironment(id) {
  return request({
    url: `/api/performance/environments/${id}/`,
    method: 'delete'
  })
}

// 性能测试套件相关API
export function getPerformanceTestSuites(params) {
  return request({
    url: '/api/performance/test-suites/',
    method: 'get',
    params
  })
}

export function createPerformanceTestSuite(data) {
  return request({
    url: '/api/performance/test-suites/',
    method: 'post',
    data
  })
}

export function getPerformanceTestSuite(id) {
  return request({
    url: `/api/performance/test-suites/${id}/`,
    method: 'get'
  })
}

export function updatePerformanceTestSuite(id, data) {
  return request({
    url: `/api/performance/test-suites/${id}/`,
    method: 'put',
    data
  })
}

export function deletePerformanceTestSuite(id) {
  return request({
    url: `/api/performance/test-suites/${id}/`,
    method: 'delete'
  })
}

// 性能测试执行相关API
export function getPerformanceExecutions(params) {
  return request({
    url: '/api/performance/executions/',
    method: 'get',
    params
  })
}

export function createPerformanceExecution(data) {
  return request({
    url: '/api/performance/executions/',
    method: 'post',
    data
  })
}

export function getPerformanceExecution(id) {
  return request({
    url: `/api/performance/executions/${id}/`,
    method: 'get'
  })
}

export function executePerformanceTest(id) {
  return request({
    url: `/api/performance/executions/${id}/execute/`,
    method: 'post'
  })
}

export function stopPerformanceTest(id) {
  return request({
    url: `/api/performance/executions/${id}/stop/`,
    method: 'post'
  })
}

export function deletePerformanceExecution(id) {
  return request({
    url: `/api/performance/executions/${id}/`,
    method: 'delete'
  })
}

// 仪表板相关API
export function getPerformanceDashboardSummary() {
  return request({
    url: '/api/performance/dashboard/summary/',
    method: 'get'
  })
}

// 定时任务相关API
export function getPerformanceScheduledTasks(params) {
  return request({
    url: '/api/performance/scheduled-tasks/',
    method: 'get',
    params
  })
}

export function createPerformanceScheduledTask(data) {
  return request({
    url: '/api/performance/scheduled-tasks/',
    method: 'post',
    data
  })
}

export function getPerformanceScheduledTask(id) {
  return request({
    url: `/api/performance/scheduled-tasks/${id}/`,
    method: 'get'
  })
}

export function updatePerformanceScheduledTask(id, data) {
  return request({
    url: `/api/performance/scheduled-tasks/${id}/`,
    method: 'put',
    data
  })
}

export function deletePerformanceScheduledTask(id) {
  return request({
    url: `/api/performance/scheduled-tasks/${id}/`,
    method: 'delete'
  })
}

export function togglePerformanceScheduledTaskStatus(id) {
  return request({
    url: `/api/performance/scheduled-tasks/${id}/toggle-status/`,
    method: 'post'
  })
}
