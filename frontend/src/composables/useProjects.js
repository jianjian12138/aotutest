/**
 * 项目相关逻辑 Composable
 * 封装项目加载、切换等通用逻辑，避免重复代码
 */
import { ref, onMounted } from 'vue'
import request from '@/utils/api'

export function useProjects() {
  const projects = ref([])
  const loading = ref(false)

  /**
   * 加载项目列表
   * @param {Object} params - 查询参数
   */
  const loadProjects = async (params = {}) => {
    loading.value = true
    try {
      const response = await request.get('/ui-automation/config/project/projects/', { params })
      projects.value = response.data.results || response.data || []
      return projects.value
    } catch (error) {
      console.error('加载项目失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取单个项目详情
   * @param {number} projectId - 项目ID
   */
  const getProject = async (projectId) => {
    try {
      const response = await request.get(`/ui-automation/config/project/projects/${projectId}/`)
      return response.data
    } catch (error) {
      console.error('获取项目详情失败:', error)
      throw error
    }
  }

  /**
   * 创建项目
   * @param {Object} data - 项目数据
   */
  const createProject = async (data) => {
    try {
      const response = await request.post('/ui-automation/config/project/projects/', data)
      return response.data
    } catch (error) {
      console.error('创建项目失败:', error)
      throw error
    }
  }

  /**
   * 更新项目
   * @param {number} projectId - 项目ID
   * @param {Object} data - 项目数据
   */
  const updateProject = async (projectId, data) => {
    try {
      const response = await request.put(`/ui-automation/config/project/projects/${projectId}/`, data)
      return response.data
    } catch (error) {
      console.error('更新项目失败:', error)
      throw error
    }
  }

  /**
   * 删除项目
   * @param {number} projectId - 项目ID
   */
  const deleteProject = async (projectId) => {
    try {
      await request.delete(`/ui-automation/config/project/projects/${projectId}/`)
    } catch (error) {
      console.error('删除项目失败:', error)
      throw error
    }
  }

  return {
    projects,
    loading,
    loadProjects,
    getProject,
    createProject,
    updateProject,
    deleteProject
  }
}
