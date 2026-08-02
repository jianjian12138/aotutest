import request from '@/utils/api'

export function getTestExecutions(params) {
  return request({
    url: '/ui-automation/test-executions/',
    method: 'get',
    params
  })
}

// 创建测试执行

export function createTestExecution(data) {
  return request({
    url: '/ui-automation/test-executions/',
    method: 'post',
    data
  })
}

// 获取测试执行详情

export function getTestExecutionDetail(id) {
  return request({
    url: `/ui-automation/test-executions/${id}/`,
    method: 'get'
  })
}

// 删除测试执行记录

export function deleteTestExecution(id) {
  return request({
    url: `/ui-automation/test-executions/${id}/`,
    method: 'delete'
  })
}

// 批量删除测试执行记录

export function batchDeleteTestExecutions(data) {
  return request({
    url: '/ui-automation/test-executions/batch_delete/',
    method: 'post',
    data
  })
}

// 运行测试执行

export function runTestExecution(id) {
  return request({
    url: `/ui-automation/test-executions/${id}/run/`,
    method: 'post'
  })
}

// 中止测试执行

export function abortTestExecution(id) {
  return request({
    url: `/ui-automation/test-executions/${id}/abort/`,
    method: 'post'
  })
}

// 测试环境相关API

// 获取测试环境列表

export function getTestEnvironments(params) {
  return request({
    url: '/ui-automation/test-environments/',
    method: 'get',
    params
  })
}

// 创建测试环境

export function createTestEnvironment(data) {
  return request({
    url: '/ui-automation/test-environments/',
    method: 'post',
    data
  })
}

// 获取测试环境详情

export function getTestEnvironmentDetail(id) {
  return request({
    url: `/ui-automation/test-environments/${id}/`,
    method: 'get'
  })
}

// 更新测试环境

export function updateTestEnvironment(id, data) {
  return request({
    url: `/ui-automation/test-environments/${id}/`,
    method: 'patch',
    data
  })
}

// 删除测试环境

export function deleteTestEnvironment(id) {
  return request({
    url: `/ui-automation/test-environments/${id}/`,
    method: 'delete'
  })
}

// 截图相关API

// 获取截图列表

export function getScreenshots(params) {
  return request({
    url: '/ui-automation/screenshots/',
    method: 'get',
    params
  })
}

// 创建截图

export function createScreenshot(data) {
  return request({
    url: '/ui-automation/screenshots/',
    method: 'post',
    data
  })
}

// 获取截图详情

export function getScreenshotDetail(id) {
  return request({
    url: `/ui-automation/screenshots/${id}/`,
    method: 'get'
  })
}

// 删除截图

export function deleteScreenshot(id) {
  return request({
    url: `/ui-automation/screenshots/${id}/`,
    method: 'delete'
  })
}

// ============ 新增功能API ============

// 元素分组相关API

export function getOperationRecords(params) {
  return request({
    url: '/ui-automation/operation-records/',
    method: 'get',
    params
  })
}

// 创建操作记录

export function createOperationRecord(data) {
  return request({
    url: '/ui-automation/operation-records/',
    method: 'post',
    data
  })
}

// ==================== 定时任务相关API ====================

// 获取定时任务列表

export function getAIExecutionRecords(params) {
  return request({
    url: '/ui-automation/ai-execution-records/',
    method: 'get',
    params
  })
}

// 获取 AI 执行记录详情

export function getAIExecutionRecordDetail(id) {
  return request({
    url: `/ui-automation/ai-execution-records/${id}/`,
    method: 'get'
  })
}

// 执行临时 AI 任务

export function batchDeleteAIExecutionRecords(ids) {
  return request({
    url: '/ui-automation/ai-execution-records/batch_delete/',
    method: 'post',
    data: { ids }
  })
}

// 获取 AI 执行报告

export function getAIExecutionReport(id, params = {}) {
  return request({
    url: `/ui-automation/ai-execution-records/${id}/report/`,
    method: 'get',
    params
  })
}

// 导出 AI 执行报告为 PDF

export function exportAIExecutionReportPDF(id, params = {}) {
  return request({
    url: `/ui-automation/ai-execution-records/${id}/export-pdf/`,
    method: 'get',
    params,
    responseType: 'blob'
  })
}

// ==================== 设备管理相关API ====================

// 获取设备列表

export function getExecutionNodes(params) {
  return request({
    url: '/ui-automation/execution-nodes/',
    method: 'get',
    params
  })
}

// 注册节点

export function registerExecutionNode(data) {
  return request({
    url: '/ui-automation/execution-nodes/register/',
    method: 'post',
    data
  })
}

// 删除节点

export function deleteExecutionNode(id) {
  return request({
    url: `/ui-automation/execution-nodes/${id}/`,
    method: 'delete'
  })
}

// ==================== UI测试模块相关API ====================

// 获取UI测试模块树
