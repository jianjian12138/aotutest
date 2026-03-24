<template>
  <div class="project-detail" v-loading="loading">
    <div class="page-header">
      <el-button @click="goBack" :icon="ArrowLeft">返回</el-button>
      <div class="header-content">
        <h2>{{ project.name }}</h2>
        <el-tag :type="getProjectTypeTag(project.project_type)" size="large">
          {{ getProjectTypeText(project.project_type) }}
        </el-tag>
        <el-tag :type="getStatusType(project.status)">
          {{ getStatusText(project.status) }}
        </el-tag>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="editProject">编辑项目</el-button>
        <el-button type="danger" @click="deleteProject">删除项目</el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="info-card">
          <template #header>
            <span>项目信息</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="项目名称">{{ project.name }}</el-descriptions-item>
            <el-descriptions-item label="项目类型">
              {{ getProjectTypeText(project.project_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              {{ getStatusText(project.status) }}
            </el-descriptions-item>
            <el-descriptions-item label="负责人">{{ project.owner?.username }}</el-descriptions-item>
            <el-descriptions-item label="基础URL" :span="2">
              {{ project.base_url || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="开始日期">
              {{ formatDate(project.start_date) }}
            </el-descriptions-item>
            <el-descriptions-item label="结束日期">
              {{ formatDate(project.end_date) }}
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">
              {{ project.description || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(project.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatDate(project.updated_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="members-card">
          <template #header>
            <div class="card-header">
              <span>项目成员 ({{ project.members?.length || 0 }})</span>
              <el-button size="small" @click="showAddMemberDialog">添加成员</el-button>
            </div>
          </template>
          <el-table :data="project.members" stripe>
            <el-table-column prop="user.username" label="用户名" />
            <el-table-column prop="user.email" label="邮箱" />
            <el-table-column prop="role" label="角色">
              <template #default="{ row }">
                <el-tag size="small">{{ getRoleText(row.role) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="joined_at" label="加入时间">
              <template #default="{ row }">
                {{ formatDate(row.joined_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button
                  size="small"
                  type="danger"
                  link
                  @click="removeMember(row)"
                  v-if="row.role !== 'owner'"
                >
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card class="environments-card">
          <template #header>
            <div class="card-header">
              <span>项目环境 ({{ project.environments?.length || 0 }})</span>
              <el-button size="small" @click="showAddEnvironmentDialog">添加环境</el-button>
            </div>
          </template>
          <el-table :data="project.environments" stripe>
            <el-table-column prop="name" label="环境名称" />
            <el-table-column prop="base_url" label="基础URL" />
            <el-table-column prop="is_default" label="默认环境">
              <template #default="{ row }">
                <el-tag v-if="row.is_default" type="success" size="small">是</el-tag>
                <el-tag v-else type="info" size="small">否</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="statistics-card">
          <template #header>
            <span>项目统计</span>
          </template>
          <el-statistic title="成员数" :value="statistics.members_count" />
          <el-divider />
          <el-statistic title="环境数" :value="statistics.environments_count" />
          <el-divider />
          <el-statistic title="测试用例数" :value="statistics.testcases_count" />
          <el-divider />
          <el-statistic title="测试套件数" :value="statistics.testsuites_count" />
          <el-divider />
          <el-statistic title="定时任务数" :value="statistics.tasks_count" />
          <el-divider />
          <el-statistic title="报告数" :value="statistics.reports_count" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加成员对话框 -->
    <el-dialog
      title="添加成员"
      v-model="showAddMember"
      width="500px"
    >
      <el-form :model="memberForm" label-width="80px">
        <el-form-item label="用户ID">
          <el-input v-model="memberForm.user_id" placeholder="请输入用户ID" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="memberForm.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="开发者" value="developer" />
            <el-option label="测试者" value="tester" />
            <el-option label="观察者" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddMember = false">取消</el-button>
        <el-button type="primary" @click="handleAddMember">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加环境对话框 -->
    <el-dialog
      title="添加环境"
      v-model="showAddEnvironment"
      width="500px"
    >
      <el-form :model="environmentForm" label-width="80px">
        <el-form-item label="环境名称" required>
          <el-input v-model="environmentForm.name" placeholder="请输入环境名称" />
        </el-form-item>
        <el-form-item label="基础URL" required>
          <el-input v-model="environmentForm.base_url" placeholder="请输入基础URL（如 http://localhost:8080）" />
        </el-form-item>
        <el-form-item label="默认环境">
          <el-switch v-model="environmentForm.is_default" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="environmentForm.description" type="textarea" placeholder="请输入环境描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddEnvironment = false">取消</el-button>
        <el-button type="primary" @click="handleAddEnvironment">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import {
  getProjectDetail,
  deleteProject as deleteProjectApi,
  addProjectMember,
  removeProjectMember as removeMemberApi,
  getProjectStatistics,
  addProjectEnvironment
} from '@/api/unified/project'

const router = useRouter()
const route = useRoute()

const projectId = route.params.id
const loading = ref(false)
const project = ref({})
const statistics = ref({})

// 成员管理
const showAddMember = ref(false)
const memberForm = reactive({
  user_id: '',
  role: 'tester'
})

// 环境管理
const showAddEnvironment = ref(false)
const environmentForm = reactive({
  name: '',
  base_url: '',
  is_default: false,
  description: ''
})

// 方法
const fetchProjectDetail = async () => {
  loading.value = true
  try {
    const response = await getProjectDetail(projectId)
    project.value = response.data
  } catch (error) {
    ElMessage.error('获取项目详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchStatistics = async () => {
  try {
    const response = await getProjectStatistics(projectId)
    statistics.value = response.data
  } catch (error) {
    console.error('获取统计数据失败', error)
  }
}

const goBack = () => {
  router.push('/unified/projects')
}

const editProject = () => {
  router.push(`/unified/projects/${projectId}/edit`)
}

const deleteProject = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目 "${project.value.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteProjectApi(projectId)
    ElMessage.success('项目删除成功')
    router.push('/unified/projects')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('项目删除失败')
      console.error(error)
    }
  }
}

const showAddMemberDialog = () => {
  memberForm.user_id = ''
  memberForm.role = 'tester'
  showAddMember.value = true
}

const handleAddMember = async () => {
  try {
    await addProjectMember(projectId, memberForm)
    ElMessage.success('成员添加成功')
    showAddMember.value = false
    fetchProjectDetail()
  } catch (error) {
    ElMessage.error('成员添加失败')
    console.error(error)
  }
}

const removeMember = async (member) => {
  try {
    await ElMessageBox.confirm(
      `确定要移除成员 "${member.user.username}" 吗？`,
      '移除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await removeMemberApi(projectId, member.id)
    ElMessage.success('成员移除成功')
    fetchProjectDetail()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('成员移除失败')
      console.error(error)
    }
  }
}

const showAddEnvironmentDialog = () => {
  environmentForm.name = ''
  environmentForm.base_url = ''
  environmentForm.is_default = false
  environmentForm.description = ''
  showAddEnvironment.value = true
}

const handleAddEnvironment = async () => {
  if (!environmentForm.name || !environmentForm.base_url) {
    ElMessage.warning('请填写必填项')
    return
  }
  try {
    const data = { ...environmentForm, project: projectId }
    await addProjectEnvironment(projectId, data)
    ElMessage.success('环境添加成功')
    showAddEnvironment.value = false
    fetchProjectDetail()
  } catch (error) {
    ElMessage.error('环境添加失败')
    console.error(error)
  }
}

// 辅助方法
const getProjectTypeTag = (type) => {
  const tags = {
    API: 'primary',
    UI: 'success',
    PERFORMANCE: 'warning',
    GENERAL: 'info'
  }
  return tags[type] || 'info'
}

const getProjectTypeText = (type) => {
  const texts = {
    API: 'API测试',
    UI: 'UI自动化',
    PERFORMANCE: '性能测试',
    GENERAL: '通用项目'
  }
  return texts[type] || type
}

const getStatusType = (status) => {
  const types = {
    active: 'success',
    paused: 'warning',
    completed: 'info',
    archived: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    active: '进行中',
    paused: '已暂停',
    completed: '已完成',
    archived: '已归档'
  }
  return texts[status] || status
}

const getRoleText = (role) => {
  const texts = {
    owner: '负责人',
    admin: '管理员',
    developer: '开发者',
    tester: '测试者',
    viewer: '观察者'
  }
  return texts[role] || role
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  fetchProjectDetail()
  fetchStatistics()
})
</script>

<style scoped>
.project-detail {
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-content h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.info-card,
.members-card,
.environments-card,
.statistics-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
