<template>
  <base-page title="UI项目管理">
    <template #actions>
      <el-button type="primary" @click="goToUnifiedProjects">
        <el-icon><View /></el-icon>
        跳转到统一管理
      </el-button>
    </template>
    
    <el-alert
      title="提示"
      type="info"
      :closable="false"
      style="margin-bottom: 20px"
    >
      UI自动化项目管理已整合到【统一管理】模块，请点击上方按钮跳转查看所有项目。
    </el-alert>
    
    <div class="projects-header">
      <h4>UI项目管理</h4>
      <div class="search-filter">
        <el-input
          v-model="searchText"
          placeholder="搜索项目名称"
          clearable
          style="width: 300px; margin-right: 15px"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="goToUnifiedProjects">
          <el-icon><View /></el-icon>
          查看统一项目管理
        </el-button>
      </div>
    </div>
    
    <div class="projects-list">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project-item"
        @click="goToProjectDetail(project.id)"
      >
        <div class="project-header">
          <div class="project-info">
            <h4 class="project-name">{{ project.name }}</h4>
            <p class="project-description">{{ project.description || '暂无描述' }}</p>
          </div>
          <div class="project-actions">
            <el-button size="small" type="primary" text @click.stop="editProject(project)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="danger" text @click.stop="deleteProject(project.id)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </div>
        <div class="project-meta">
          <el-tag :type="getStatusType(project.status)" size="small">
            {{ getStatusText(project.status) }}
          </el-tag>
          <span class="update-time">{{ formatDate(null, null, project.updated_at) }}</span>
        </div>
      </div>
    </div>
    
    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="pagination.currentPage"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 创建项目对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建UI自动化项目" width="500px">
      <el-form ref="createFormRef" :model="createForm" :rules="formRules" label-width="80px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" placeholder="请输入项目描述" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="createForm.status" placeholder="请选择项目状态">
            <el-option label="未开始" value="NOT_STARTED" />
            <el-option label="进行中" value="IN_PROGRESS" />
            <el-option label="已结束" value="COMPLETED" />
          </el-select>
        </el-form-item>
        <el-form-item label="基础URL" prop="base_url">
          <el-input v-model="createForm.base_url" placeholder="请输入基础URL" />
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker v-model="createForm.start_date" type="date" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker v-model="createForm.end_date" type="date" placeholder="选择日期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="handleCreate">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 编辑项目对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑UI自动化项目" width="500px">
      <el-form ref="editFormRef" :model="editForm" :rules="formRules" label-width="80px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input v-model="editForm.description" type="textarea" placeholder="请输入项目描述" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="editForm.status" placeholder="请选择项目状态">
            <el-option label="未开始" value="NOT_STARTED" />
            <el-option label="进行中" value="IN_PROGRESS" />
            <el-option label="已结束" value="COMPLETED" />
          </el-select>
        </el-form-item>
        <el-form-item label="基础URL" prop="base_url">
          <el-input v-model="editForm.base_url" placeholder="请输入基础URL" />
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker v-model="editForm.start_date" type="date" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker v-model="editForm.end_date" type="date" placeholder="选择日期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditDialog = false">取消</el-button>
          <el-button type="primary" @click="handleEdit">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 项目详情弹框 -->
    <el-dialog v-model="showDetailDialog" title="项目详情" width="600px">
      <div v-if="currentProjectDetail" class="view-dialog-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目名称">{{ currentProjectDetail.name }}</el-descriptions-item>
          <el-descriptions-item label="项目状态">
            <el-tag :type="getStatusType(currentProjectDetail.status)">
              {{ getStatusText(currentProjectDetail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="项目描述" :span="2">{{ currentProjectDetail.description || '暂无描述' }}</el-descriptions-item>
          <el-descriptions-item label="基础URL">{{ currentProjectDetail.base_url }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentProjectDetail.owner?.username || '暂无' }}</el-descriptions-item>
          <el-descriptions-item label="开始日期" :span="2">{{ currentProjectDetail.start_date ? formatDate(null, null, currentProjectDetail.start_date) : '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="结束日期" :span="2">{{ currentProjectDetail.end_date ? formatDate(null, null, currentProjectDetail.end_date) : '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ formatDate(null, null, currentProjectDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">{{ formatDate(null, null, currentProjectDetail.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <div v-else class="text-center text-gray-500">
        加载中...
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDetailDialog = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </base-page>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, Edit, Delete } from '@element-plus/icons-vue'
import { getUiProjects, createUiProject, updateUiProject, deleteUiProject } from '@/api/ui_automation'

const router = useRouter()

// 跳转到统一管理项目页面
const goToUnifiedProjects = () => {
  router.push('/unified/projects')
}

// 项目数据
const projects = ref([])
const loading = ref(false)
const total = ref(0)
const pagination = reactive({
  currentPage: 1,
  pageSize: 10
})

// 搜索和筛选
const searchText = ref('')
const statusFilter = ref('')

// 表单相关
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const createFormRef = ref(null)
const editFormRef = ref(null)
const currentEditId = ref(null)

// 表单数据
const createForm = reactive({
  name: '',
  description: '',
  status: 'IN_PROGRESS',
  base_url: '',
  start_date: null,
  end_date: null
})

const editForm = reactive({
  name: '',
  description: '',
  status: 'IN_PROGRESS',
  base_url: '',
  start_date: null,
  end_date: null
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 2, max: 200, message: '项目名称长度在 2 到 200 个字符', trigger: 'blur' }
  ],
  base_url: [
    { required: true, message: '请输入基础URL', trigger: 'blur' },
    { type: 'url', message: '请输入有效的URL', trigger: 'blur' }
  ]
}

// 格式化日期
const formatDate = (row, column, cellValue) => {
  if (!cellValue) return ''
  return new Date(cellValue).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 获取状态样式
const getStatusType = (status) => {
  const statusMap = {
    'NOT_STARTED': 'warning',
    'IN_PROGRESS': 'primary',
    'COMPLETED': 'success'
  }
  return statusMap[status] || 'default'
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'NOT_STARTED': '未开始',
    'IN_PROGRESS': '进行中',
    'COMPLETED': '已结束'
  }
  return statusMap[status] || status
}

// 加载项目列表
const loadProjects = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize
    }
    
    // 添加搜索条件
    if (searchText.value) {
      params.search = searchText.value
    }
    
    // 添加筛选条件
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    
    const response = await getUiProjects(params)
    projects.value = response.data.results || response.data
    total.value = response.data.count || projects.value.length
  } catch (error) {
    ElMessage.error('获取项目列表失败')
    console.error('获取项目列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  pagination.currentPage = 1
  loadProjects()
}

// 筛选处理
const handleFilter = () => {
  pagination.currentPage = 1
  loadProjects()
}

// 分页处理
const handleSizeChange = (size) => {
  pagination.pageSize = size
  loadProjects()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  loadProjects()
}

// 详情相关
const showDetailDialog = ref(false)
const currentProjectDetail = ref(null)

// 查看项目详情
const goToProjectDetail = (id) => {
  // 查找当前项目
  const project = projects.value.find(p => p.id === id)
  if (project) {
    currentProjectDetail.value = project
    showDetailDialog.value = true
  } else {
    ElMessage.error('未找到项目信息')
  }
}

// 编辑项目
const editProject = (project) => {
  currentEditId.value = project.id
  // 复制项目数据到编辑表单
  Object.assign(editForm, {
    name: project.name,
    description: project.description,
    status: project.status,
    base_url: project.base_url,
    start_date: project.start_date ? new Date(project.start_date) : null,
    end_date: project.end_date ? new Date(project.end_date) : null
  })
  showEditDialog.value = true
}

// 删除项目
const deleteProject = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个项目吗？删除后数据将无法恢复。', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteUiProject(id)
    ElMessage.success('项目删除成功')
    loadProjects()
  } catch (error) {
    if (error === 'cancel') return
    ElMessage.error('项目删除失败')
    console.error('删除项目失败:', error)
  }
}

// 导入用户store
import { useUserStore } from '@/stores/user'

// 日期格式化辅助函数
const formatDateToISO = (date) => {
  if (!date) return null
  // 确保是Date对象
  const d = new Date(date)
  // 格式化为YYYY-MM-DD格式
  return d.toISOString().split('T')[0]
}

// 处理创建项目
const handleCreate = async () => {
  const validate = await createFormRef.value.validate()
  if (!validate) return
  
  try {
    const userStore = useUserStore()
    // 确保用户信息已加载
    if (!userStore.user?.id) {
      await userStore.fetchProfile()
    }
    
    // 创建包含owner字段的项目数据，并格式化日期字段
    const projectData = {
      ...createForm,
      owner: userStore.user.id,  // 添加owner字段，值为当前登录用户ID
      // 格式化日期为YYYY-MM-DD格式
      start_date: formatDateToISO(createForm.start_date),
      end_date: formatDateToISO(createForm.end_date)
    }
    
    await createUiProject(projectData)
    ElMessage.success('项目创建成功')
    showCreateDialog.value = false
    
    // 重置表单
    Object.keys(createForm).forEach(key => {
      createForm[key] = ''
    })
    createForm.status = 'IN_PROGRESS'
    
    loadProjects()
  } catch (error) {
    ElMessage.error('项目创建失败')
    console.error('创建项目失败:', error)
  }
}

// 处理编辑项目
const handleEdit = async () => {
  const validate = await editFormRef.value.validate()
  if (!validate) return
  
  try {
    // 创建包含格式化日期字段的项目数据
    const projectData = {
      ...editForm,
      // 格式化日期为YYYY-MM-DD格式
      start_date: formatDateToISO(editForm.start_date),
      end_date: formatDateToISO(editForm.end_date)
    }
    
    await updateUiProject(currentEditId.value, projectData)
    ElMessage.success('项目更新成功')
    showEditDialog.value = false
    loadProjects()
  } catch (error) {
    ElMessage.error('项目更新失败')
    console.error('更新项目失败:', error)
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
/* .project-management-container, .page-header, .page-title, .header-actions, .main-content, .content-wrapper 已被 BasePage 替代 */

.projects-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e6e6e6;
  flex-shrink: 0;

  h4 {
    margin: 0;
    color: #303133;
    font-size: 18px;
  }

  .search-filter {
    display: flex;
    align-items: center;
  }
}

.projects-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 20px;
}

.project-item {
  border: 1px solid #e6e6e6;
  border-radius: 8px;
  margin-bottom: 15px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.project-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.project-info {
  flex: 1;
  margin-right: 20px;
}

.project-name {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.project-description {
  margin: 0;
  color: #606266;
  font-size: 14px;
  line-height: 1.5;
}

.project-actions {
  display: flex;
  gap: 10px;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 14px;
  color: #909399;
}

.update-time {
  font-size: 12px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

