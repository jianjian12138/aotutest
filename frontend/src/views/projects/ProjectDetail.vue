<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">项目详情</h1>
      <el-button type="primary" @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>
    
    <div class="card-container">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="项目信息" name="info">
          <div v-if="project">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="项目名称">{{ project.name }}</el-descriptions-item>
              <el-descriptions-item label="项目状态">
                <el-tag :type="getStatusType(project.status)">{{ getStatusText(project.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="负责人">{{ project.owner?.username }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(project.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="项目描述" :span="2">{{ project.description || '暂无描述' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="项目成员" name="members">
          <div class="members-section">
            <el-button type="primary" @click="showAddMemberDialog = true">添加成员</el-button>
            <el-table :data="project?.members || []" style="width: 100%; margin-top: 20px;">
              <el-table-column prop="user.username" label="用户名" />
              <el-table-column prop="user.email" label="邮箱" />
              <el-table-column prop="role" label="角色" />
              <el-table-column prop="joined_at" label="加入时间">
                <template #default="{ row }">
                  {{ formatDate(row.joined_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button size="small" type="danger" @click="removeMember(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="环境配置" name="environments">
          <div class="environments-section">
            <el-button type="primary" @click="showAddEnvDialog = true">添加环境</el-button>
            <el-table :data="project?.environments || []" style="width: 100%; margin-top: 20px;">
              <el-table-column prop="name" label="环境名称" />
              <el-table-column prop="base_url" label="基础URL" />
              <el-table-column prop="description" label="描述" />
              <el-table-column prop="is_default" label="默认环境">
                <template #default="{ row }">
                  <el-tag v-if="row.is_default" type="success">是</el-tag>
                  <span v-else>否</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'
import dayjs from 'dayjs'

const route = useRoute()
const project = ref(null)
const activeTab = ref('info')
const showAddMemberDialog = ref(false)
const showAddEnvDialog = ref(false)

const fetchProject = async () => {
  try {
    const response = await api.get(`/projects/${route.params.id}/`)
    project.value = response.data
  } catch (error) {
    ElMessage.error('获取项目详情失败')
  }
}

const getStatusType = (status) => {
  const typeMap = {
    active: 'success',
    paused: 'warning',
    completed: 'info',
    archived: 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    active: '进行中',
    paused: '已暂停',
    completed: '已完成',
    archived: '已归档'
  }
  return textMap[status] || status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const removeMember = async (member) => {
  try {
    await api.delete(`/projects/${route.params.id}/members/${member.id}/`)
    ElMessage.success('成员删除成功')
    fetchProject()
  } catch (error) {
    ElMessage.error('删除成员失败')
  }
}

onMounted(() => {
  fetchProject()
})
</script>

<style lang="scss" scoped>
.members-section, .environments-section {
  padding: 20px 0;
}
</style>