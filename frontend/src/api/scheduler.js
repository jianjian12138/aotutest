import api from '@/utils/api'

export default {
  // 定时任务
  getTasks(params) {
    return api.get('/scheduler/tasks/', { params })
  },
  
  createTask(data) {
    return api.post('/scheduler/tasks/', data)
  },
  
  updateTask(id, data) {
    return api.put(`/scheduler/tasks/${id}/`, data)
  },
  
  deleteTask(id) {
    return api.delete(`/scheduler/tasks/${id}/`)
  },
  
  runTaskOnce(id) {
    return api.post(`/scheduler/tasks/${id}/run_once/`)
  },

  // 通知配置
  getNotificationConfigs(params) {
    return api.get('/scheduler/notifications/', { params })
  },
  
  createNotificationConfig(data) {
    return api.post('/scheduler/notifications/', data)
  },
  
  updateNotificationConfig(id, data) {
    return api.put(`/scheduler/notifications/${id}/`, data)
  },
  
  deleteNotificationConfig(id) {
    return api.delete(`/scheduler/notifications/${id}/`)
  },

  // 执行日志
  getExecutionLogs(params) {
    return api.get('/scheduler/logs/', { params })
  }
}
