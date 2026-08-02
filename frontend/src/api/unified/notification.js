import request from '@/utils/request'

/**
 * 获取通知配置列表
 */
export function getNotificationConfigList(params) {
  return request({
    url: '/notifications/notifications/',
    method: 'get',
    params
  })
}

/**
 * 获取通知配置详情
 */
export function getNotificationConfigDetail(id) {
  return request({
    url: `/notifications/notifications/${id}/`,
    method: 'get'
  })
}

/**
 * 创建通知配置
 */
export function createNotificationConfig(data) {
  return request({
    url: '/notifications/notifications/',
    method: 'post',
    data
  })
}

/**
 * 更新通知配置
 */
export function updateNotificationConfig(id, data) {
  return request({
    url: `/notifications/notifications/${id}/`,
    method: 'put',
    data
  })
}

/**
 * 部分更新通知配置
 */
export function partialUpdateNotificationConfig(id, data) {
  return request({
    url: `/notifications/notifications/${id}/`,
    method: 'patch',
    data
  })
}

/**
 * 删除通知配置
 */
export function deleteNotificationConfig(id) {
  return request({
    url: `/notifications/notifications/${id}/`,
    method: 'delete'
  })
}

/**
 * 获取通知日志
 */
export function getNotificationLogs(params) {
  return request({
    url: '/scheduler/notification-logs/',
    method: 'get',
    params
  })
}

/**
 * 测试通知配置
 */
export function testNotificationConfig(id) {
  return request({
    url: `/api/notifications/notifications/${id}/test/`,
    method: 'post'
  })
}
