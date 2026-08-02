import request from '@/utils/api'

export function getDashboardStats() {
  return request({
    url: '/ui-automation/dashboard/stats/',
    method: 'get'
  })
}

// UI项目相关API

// 获取UI项目列表

export function getUiProjects(params) {
  return request({
    url: '/ui-automation/projects/',
    method: 'get',
    params
  })
}

// 创建UI项目

export function createUiProject(data) {
  return request({
    url: '/ui-automation/projects/',
    method: 'post',
    data
  })
}

// 获取UI项目详情

export function getUiProjectDetail(id) {
  return request({
    url: `/ui-automation/projects/${id}/`,
    method: 'get'
  })
}

// 更新UI项目

export function updateUiProject(id, data) {
  return request({
    url: `/ui-automation/projects/${id}/`,
    method: 'patch',
    data
  })
}

// 删除UI项目

export function deleteUiProject(id) {
  return request({
    url: `/ui-automation/projects/${id}/`,
    method: 'delete'
  })
}

// 定位策略相关API

// 获取定位策略列表
