<template>
  <div class="project-management">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header">
          <h2 class="page-title">项目管理</h2>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog = true">
              <el-icon><Plus /></el-icon>
              新建项目
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="content">
        <!-- 项目列表 -->
        <el-table 
          :data="projects" 
          v-loading="loading" 
          style="width: 100%"
          border
          stripe
        >
          <el-table-column prop="name" label="项目名称" min-width="200" />
          <el-table-column prop="project_type" label="项目类型" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.project_type === 'HTTP' ? 'primary' : 'success'">
                {{ scope.row.project_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="项目状态" width="120">
            <template #default="scope">
              <el-tag 
                :type="getStatusType(scope.row.status)"
              >
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="owner.username" label="负责人" width="150" />
          <el-table-column prop="start_date" label="开始日期" width="120" />
          <el-table-column prop="end_date" label="结束日期" width="120" />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="scope">
              <el-button link type="primary" @click="editProject(scope.row)">编辑</el-button>
              <el-button link type="primary" @click="viewProject(scope.row)">查看</el-button>
              <el-button link type="danger" @click="deleteProject(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>

    <!-- 新建/编辑项目对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingProject ? '编辑项目' : '新建项目'"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        
        <el-form-item label="项目描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入项目描述"
          />
        </el-form-item>
        
        <el-form-item label="项目类型" prop="project_type">
          <el-radio-group v-model="form.project_type">
            <el-radio value="HTTP">HTTP</el-radio>
            <el-radio value="WEBSOCKET">WebSocket</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="项目状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择项目状态">
            <el-option label="未开始" value="NOT_STARTED" />
            <el-option label="进行中" value="IN_PROGRESS" />
            <el-option label="已结束" value="COMPLETED" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="负责人" prop="owner">
          <el-select v-model="form.owner" placeholder="请选择负责人" filterable>
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="团队成员" prop="member_ids">
          <el-select
            v-model="form.member_ids"
            multiple
            placeholder="请选择团队成员"
            filterable
          >
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker
            v-model="form.start_date"
            type="date"
            placeholder="请选择开始日期"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker
            v-model="form.end_date"
            type="date"
            placeholder="请选择结束日期"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ editingProject ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看项目详情对话框 -->
    <el-dialog
      v-model="showViewDialog"
      title="项目详情"
      width="600px"
    >
      <el-descriptions :column="1" border>
        <el-descriptions-item label="项目名称">{{ viewedProject?.name }}</el-descriptions-item>
        <el-descriptions-item label="项目描述">{{ viewedProject?.description || '无' }}</el-descriptions-item>
        <el-descriptions-item label="项目类型">
          <el-tag :type="viewedProject?.project_type === 'HTTP' ? 'primary' : 'success'">
            {{ viewedProject?.project_type }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="项目状态">
          <el-tag :type="getStatusType(viewedProject?.status)">
            {{ getStatusText(viewedProject?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="负责人">{{ viewedProject?.owner?.username }}</el-descriptions-item>
        <el-descriptions-item label="团队成员">
          <div v-if="viewedProject?.members?.length">
            <el-tag
              v-for="member in viewedProject.members"
              :key="member.id"
              size="small"
              style="margin-right: 5px; margin-bottom: 5px;"
            >
              {{ member.username }}
            </el-tag>
          </div>
          <span v-else>无</span>
        </el-descriptions-item>
        <el-descriptions-item label="开始日期">{{ viewedProject?.start_date || '未设置' }}</el-descriptions-item>
        <el-descriptions-item label="结束日期">{{ viewedProject?.end_date || '未设置' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(viewedProject?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(viewedProject?.updated_at) }}</el-descriptions-item>
      </el-descriptions>
      
      <template #footer>
        <el-button @click="showViewDialog = false">关闭</el-button>
        <el-button type="primary" @click="editProject(viewedProject)">编辑</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, ElDescriptions, ElDescriptionsItem } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const loading = ref(false)
const projects = ref([])
const users = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showCreateDialog = ref(false)
const showViewDialog = ref(false)
const editingProject = ref(null)
const viewedProject = ref(null)
const submitting = ref(false)
const formRef = ref()

const form = reactive({
  name: '',
  description: '',
  project_type: 'HTTP',
  status: 'NOT_STARTED',
  owner: null,
  member_ids: [],
  start_date: '',
  end_date: ''
})

const rules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' }
  ],
  project_type: [
    { required: true, message: '请选择项目类型', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择项目状态', trigger: 'change' }
  ],
  owner: [
    { required: true, message: '请选择负责人', trigger: 'change' }
  ]
}

const getStatusType = (status) => {
  const typeMap = {
    'NOT_STARTED': 'info',
    'IN_PROGRESS': 'warning',
    'COMPLETED': 'success'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'NOT_STARTED': '未开始',
    'IN_PROGRESS': '进行中',
    'COMPLETED': '已结束'
  }
  return textMap[status] || status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const loadProjects = async () => {
  loading.value = true
  try {
    const response = await api.get('/api-testing/projects/', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    projects.value = response.data.results
    total.value = response.data.count
  } catch (error) {
    ElMessage.error('加载项目列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadUsers = async () => {
  try {
    const response = await api.get('/api-testing/users/')
    users.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('加载用户列表失败')
    console.error(error)
  }
}

const createSampleProject = async () => {
  try {
    await api.post('/api-testing/projects/create-sample/')
    ElMessage.success('示例项目创建成功')
    await loadProjects()
  } catch (error) {
    if (error.response?.data?.message) {
      ElMessage.warning(error.response.data.message)
    } else {
      ElMessage.error('创建示例项目失败')
    }
  }
}

const handleSizeChange = (size) => {
  pageSize.value = size
  loadProjects()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  loadProjects()
}

const editProject = (project) => {
  editingProject.value = project
  form.name = project.name
  form.description = project.description
  form.project_type = project.project_type
  form.status = project.status
  form.owner = project.owner.id
  form.member_ids = project.members.map(m => m.id)
  form.start_date = project.start_date
  form.end_date = project.end_date
  showCreateDialog.value = true
}

const viewProject = (project) => {
  // 显示项目详情弹框
  showViewDialog.value = true
  viewedProject.value = project
}

const deleteProject = async (project) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目 "${project.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await api.delete(`/api-testing/projects/${project.id}/`)
    ElMessage.success('删除成功')
    await loadProjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitting.value = true
  try {
    const data = { ...form }
    if (data.start_date) {
      data.start_date = dayjs(data.start_date).format('YYYY-MM-DD')
    }
    if (data.end_date) {
      data.end_date = dayjs(data.end_date).format('YYYY-MM-DD')
    }
    
    if (editingProject.value) {
      await api.put(`/api-testing/projects/${editingProject.value.id}/`, data)
      ElMessage.success('项目更新成功')
    } else {
      await api.post('/api-testing/projects/', data)
      ElMessage.success('项目创建成功')
    }
    
    showCreateDialog.value = false
    await loadProjects()
  } catch (error) {
    ElMessage.error(editingProject.value ? '更新项目失败' : '创建项目失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  editingProject.value = null
  Object.assign(form, {
    name: '',
    description: '',
    project_type: 'HTTP',
    status: 'NOT_STARTED',
    owner: null,
    member_ids: [],
    start_date: '',
    end_date: ''
  })
  formRef.value?.resetFields()
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadUsers()])
  
  // 如果没有项目，询问是否创建示例项目
  if (projects.value.length === 0) {
    try {
      await ElMessageBox.confirm(
        '当前没有任何项目，是否创建宠物店示例项目？',
        '提示',
        {
          confirmButtonText: '创建示例项目',
          cancelButtonText: '稍后再说',
          type: 'info'
        }
      )
      await createSampleProject()
    } catch (error) {
      // 用户取消，不处理
    }
  }
})
</script>

<style scoped>
.project-management {
  width: 100%;
}

.page-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.content {
  padding: 20px 0;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}
</style>