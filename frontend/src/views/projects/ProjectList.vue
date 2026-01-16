<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">项目管理</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新建项目
      </el-button>
    </div>
    
    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-input
              v-model="searchText"
              placeholder="搜索项目名称"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="handleFilter">
              <el-option label="进行中" value="active" />
              <el-option label="已暂停" value="paused" />
              <el-option label="已完成" value="completed" />
              <el-option label="已归档" value="archived" />
            </el-select>
          </el-col>
        </el-row>
      </div>
      
      <el-table :data="projects" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="项目名称" min-width="200">
          <template #default="{ row }">
            <el-link @click="goToProject(row.id)" type="primary">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="300" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner.username" label="负责人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editProject(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteProject(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
    
    <!-- 创建/编辑项目对话框 -->
    <el-dialog
      :title="isEdit ? '编辑项目' : '新建项目'"
      v-model="showCreateDialog"
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="请输入项目描述"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="进行中" value="active" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已完成" value="completed" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import dayjs from 'dayjs'

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const showCreateDialog = ref(false)
const isEdit = ref(false)
const formRef = ref()

const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchText = ref('')
const statusFilter = ref('')

const form = reactive({
  id: null,
  name: '',
  description: '',
  status: 'active'
})

const rules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 2, max: 200, message: '项目名称长度在 2 到 200 个字符', trigger: 'blur' }
  ],
  status: [
    { required: true, message: '请选择项目状态', trigger: 'change' }
  ]
}

const fetchProjects = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      status: statusFilter.value
    }
    const response = await api.get('/projects/', { params })
    projects.value = response.data.results
    total.value = response.data.count
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchProjects()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchProjects()
}

const handlePageChange = () => {
  fetchProjects()
}

const goToProject = (id) => {
  router.push(`/ai-generation/projects/${id}`)
}

const editProject = (project) => {
  isEdit.value = true
  form.id = project.id
  form.name = project.name
  form.description = project.description
  form.status = project.status
  showCreateDialog.value = true
}

const resetForm = () => {
  form.id = null
  form.name = ''
  form.description = ''
  form.status = 'active'
  isEdit.value = false
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (isEdit.value) {
          await api.put(`/projects/${form.id}/`, form)
          ElMessage.success('项目更新成功')
        } else {
          await api.post('/projects/', form)
          ElMessage.success('项目创建成功')
        }
        showCreateDialog.value = false
        resetForm()
        fetchProjects()
      } catch (error) {
        ElMessage.error(isEdit.value ? '项目更新失败' : '项目创建失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

const deleteProject = async (project) => {
  try {
    await ElMessageBox.confirm('确定要删除这个项目吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/projects/${project.id}/`)
    ElMessage.success('项目删除成功')
    fetchProjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('项目删除失败')
    }
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

onMounted(() => {
  fetchProjects()
})
</script>

<style lang="scss" scoped>
.filter-bar {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>