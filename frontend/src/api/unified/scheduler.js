import request from '@/utils/request'

/**
 * 获取定时任务列表
 */
export function getTaskList(params) {
  return request({
    url: '/scheduler/tasks/',
    method: 'get',
    params
  })
}

/**
 * 获取任务详情
 */
export function getTaskDetail(id) {
  return request({
    url: `/scheduler/tasks/${id}/`,
    method: 'get'
  })
}

/**
 * 创建定时任务
 */
export function createTask(data) {
  return request({
    url: '/scheduler/tasks/',
    method: 'post',
    data
  })
}

/**
 * 更新定时任务
 */
export function updateTask(id, data) {
  return request({
    url: `/scheduler/tasks/${id}/`,
    method: 'put',
    data
  })
}

/**
 * 部分更新定时任务
 */
export function partialUpdateTask(id, data) {
  return request({
    url: `/scheduler/tasks/${id}/`,
    method: 'patch',
    data
  })
}

/**
 * 删除定时任务
 */
export function deleteTask(id) {
  return request({
    url: `/scheduler/tasks/${id}/`,
    method: 'delete'
  })
}

/**
 * 获取任务执行日志
 */
export function getTaskExecutionLogs(taskId, params) {
  return request({
    url: `/scheduler/logs/`,
    method: 'get',
    params: {
      ...params,
      task: taskId
    }
  })
}

/**
 * 手动执行任务
 */
export function executeTask(id) {
  return request({
    url: `/scheduler/tasks/${id}/execute/`,
    method: 'post'
  })
}

/**
 * 暂停任务
 */
export function pauseTask(id) {
  return request({
    url: `/scheduler/tasks/${id}/pause/`,
    method: 'post'
  })
}

/**
 * 恢复任务
 */
export function resumeTask(id) {
  return request({
    url: `/scheduler/tasks/${id}/resume/`,
    method: 'post'
  })
}
