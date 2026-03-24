import request from '@/utils/api'

export function getScheduledTasks(params) {
  return request({
    url: '/ui-automation/scheduled-tasks/',
    method: 'get',
    params
  })
}

// 创建定时任务

export function createScheduledTask(data) {
  return request({
    url: '/ui-automation/scheduled-tasks/',
    method: 'post',
    data
  })
}

// 获取定时任务详情

export function getScheduledTaskDetail(id) {
  return request({
    url: `/ui-automation/scheduled-tasks/${id}/`,
    method: 'get'
  })
}

// 更新定时任务

export function updateScheduledTask(id, data) {
  return request({
    url: `/ui-automation/scheduled-tasks/${id}/`,
    method: 'patch',
    data
  })
}

// 删除定时任务

export function deleteScheduledTask(id) {
  return request({
    url: `/ui-automation/scheduled-tasks/${id}/`,
    method: 'delete'
  })
}

// 暂停定时任务

export function pauseScheduledTask(id) {
  return request({
    url: `/ui-automation/scheduled-tasks/${id}/pause/`,
    method: 'post'
  })
}

// 恢复定时任务

export function resumeScheduledTask(id) {
  return request({
    url: `/ui-automation/scheduled-tasks/${id}/resume/`,
    method: 'post'
  })
}

// 立即运行任务

export function runScheduledTask(id) {
  return request({
    url: `/ui-automation/scheduled-tasks/${id}/run_now/`,
    method: 'post'
  })
}

// ==================== 通知配置相关API ====================

// 获取通知配置列表

export function getNotificationConfigs(params) {
  return request({
    url: '/ui-automation/notification-configs/',
    method: 'get',
    params
  })
}

// 创建通知配置

export function createNotificationConfig(data) {
  return request({
    url: '/ui-automation/notification-configs/',
    method: 'post',
    data
  })
}

// 获取通知配置详情

export function getNotificationConfigDetail(id) {
  return request({
    url: `/ui-automation/notification-configs/${id}/`,
    method: 'get'
  })
}

// 更新通知配置

export function updateNotificationConfig(id, data) {
  return request({
    url: `/ui-automation/notification-configs/${id}/`,
    method: 'patch',
    data
  })
}

// 删除通知配置

export function deleteNotificationConfig(id) {
  return request({
    url: `/ui-automation/notification-configs/${id}/`,
    method: 'delete'
  })
}

// 设置为默认配置

export function setDefaultNotificationConfig(id) {
  return request({
    url: `/ui-automation/notification-configs/${id}/set_default/`,
    method: 'post'
  })
}

// ==================== 通知日志相关API ====================

// 获取通知日志列表

export function getNotificationLogs(params) {
  return request({
    url: '/ui-automation/notification-logs/',
    method: 'get',
    params
  })
}

// 重试发送通知

export function retryNotification(id) {
  return request({
    url: `/ui-automation/notification-logs/${id}/retry/`,
    method: 'post'
  })
}

// ==================== 任务通知设置相关API ====================

// 获取任务通知设置

export function getTaskNotificationSettings(params) {
  return request({
    url: '/ui-automation/task-notification-settings/',
    method: 'get',
    params
  })
}

// 创建任务通知设置

export function createTaskNotificationSetting(data) {
  return request({
    url: '/ui-automation/task-notification-settings/',
    method: 'post',
    data
  })
}

// 更新任务通知设置

export function updateTaskNotificationSetting(id, data) {
  return request({
    url: `/ui-automation/task-notification-settings/${id}/`,
    method: 'patch',
    data
  })
}

// 获取用户列表（复用接口测试的用户接口）

export function runAdhocAITask(data) {
  return request({
    url: '/ui-automation/ai-execution-records/run_adhoc/',
    method: 'post',
    data
  })
}

// 停止 AI 任务

export function stopAITask(id) {
  return request({
    url: `/ui-automation/ai-execution-records/${id}/stop/`,
    method: 'post'
  })
}

// 批量删除 AI 执行记录

export function getDeviceList(params) {
  return request({
    url: '/ui-automation/devices/',
    method: 'get',
    params
  })
}

// 刷新设备列表

export function refreshDeviceList() {
  return request({
    url: '/ui-automation/devices/refresh/',
    method: 'get'
  })
}

// 连接远程设备

export function connectRemoteDevice(ip, port) {
  return request({
    url: '/ui-automation/devices/connect_remote/',
    method: 'post',
    data: { ip, port }
  })
}

// 断开设备连接

export function disconnectDevice(device) {
  return request({
    url: `/ui-automation/devices/${device.id}/disconnect/`,
    method: 'post'
  })
}

// ==================== 调试文件相关API ====================

// 获取调试文件列表
