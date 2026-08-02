import request from '@/utils/request'

/**
 * 获取项目列表
 */
export function getProjectList(params) {
  return request({
    url: '/projects/',
    method: 'get',
    params
  })
}

/**
 * 获取项目详情
 */
export function getProjectDetail(id) {
  return request({
    url: `/projects/${id}/`,
    method: 'get'
  })
}

/**
 * 创建项目
 */
export function createProject(data) {
  return request({
    url: '/projects/',
    method: 'post',
    data
  })
}

/**
 * 更新项目
 */
export function updateProject(id, data) {
  return request({
    url: `/projects/${id}/`,
    method: 'put',
    data
  })
}

/**
 * 部分更新项目
 */
export function partialUpdateProject(id, data) {
  return request({
    url: `/projects/${id}/`,
    method: 'patch',
    data
  })
}

/**
 * 删除项目
 */
export function deleteProject(id) {
  return request({
    url: `/projects/${id}/`,
    method: 'delete'
  })
}

/**
 * 获取项目成员
 */
export function getProjectMembers(id) {
  return request({
    url: `/projects/${id}/members/`,
    method: 'get'
  })
}

/**
 * 添加项目成员
 */
export function addProjectMember(id, data) {
  return request({
    url: `/projects/${id}/add_member/`,
    method: 'post',
    data
  })
}

/**
 * 删除项目成员
 */
export function removeProjectMember(id, memberId) {
  return request({
    url: `/projects/${id}/remove_member/${memberId}/`,
    method: 'delete'
  })
}

/**
 * 获取项目环境
 */
export function getProjectEnvironments(id) {
  return request({
    url: `/projects/${id}/environments/`,
    method: 'get'
  })
}

/**
 * 添加项目环境
 */
export function addProjectEnvironment(id, data) {
  return request({
    url: `/projects/${id}/environments/`,
    method: 'post',
    data
  })
}

/**
 * 获取项目统计
 */
export function getProjectStatistics(id) {
  return request({
    url: `/projects/${id}/statistics/`,
    method: 'get'
  })
}

/**
 * 获取所有项目（用于下拉选择）
 */
export function getAllProjects(params) {
  return request({
    url: '/projects/all/',
    method: 'get',
    params
  })
}
