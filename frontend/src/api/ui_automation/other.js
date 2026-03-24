import request from '@/utils/api'

export function getUiUsers(params) {
  return request({
    url: '/api-testing/users/',
    method: 'get',
    params
  })
}

// ==================== AI 智能模式相关API ====================

// 获取 AI 用例列表

export function getAICases(params) {
  return request({
    url: '/ui-automation/ai-cases/',
    method: 'get',
    params
  })
}

// 创建 AI 用例

export function createAICase(data) {
  return request({
    url: '/ui-automation/ai-cases/',
    method: 'post',
    data
  })
}

// 获取 AI 用例详情

export function getAICaseDetail(id) {
  return request({
    url: `/ui-automation/ai-cases/${id}/`,
    method: 'get'
  })
}

// 更新 AI 用例

export function updateAICase(id, data) {
  return request({
    url: `/ui-automation/ai-cases/${id}/`,
    method: 'patch',
    data
  })
}

// 删除 AI 用例

export function deleteAICase(id) {
  return request({
    url: `/ui-automation/ai-cases/${id}/`,
    method: 'delete'
  })
}

// 运行 AI 用例

export function runAICase(id) {
  return request({
    url: `/ui-automation/ai-cases/${id}/run/`,
    method: 'post'
  })
}

// 获取 AI 执行记录列表

export function getDebugFiles() {
  return request({
    url: '/ui-automation/debug-files/',
    method: 'get'
  })
}

// 获取调试文件内容

export function getDebugFileContent(url) {
  return request({
    url: '/ui-automation/debug-files/content/',
    method: 'get',
    params: { url }
  })
}

// ==================== 节点管理相关API ====================

// 获取节点列表
