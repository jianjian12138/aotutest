<template>
  <div class="config-container">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">项目管理</h2>
          <div class="header-actions">
            <el-button type="primary" @click="handleCreateProject">
              <el-icon><Plus /></el-icon>
              新建项目
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="content">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchQuery"
            placeholder="请输入项目名称或描述"
            clearable
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select
            v-model="statusFilter"
            placeholder="筛选项目状态"
            clearable
            class="filter-select"
          >
            <el-option label="活跃" value="active" />
            <el-option label="已归档" value="archived" />
          </el-select>
          
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </div>
        
        <!-- 项目列表 -->
        <el-table
          :data="projects"
          stripe
          border
          style="width: 100%"
          @row-click="handleRowClick"
        >
          <el-table-column prop="id" label="项目ID" width="100" />
          <el-table-column prop="name" label="项目名称" />
          <el-table-column prop="description" label="项目描述" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag
                :type="getStatusTagType(scope.row.status)"
                size="small"
              >
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_by" label="创建人" width="120" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="handleViewProject(scope.row)">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button size="small" type="primary" @click="handleEditProject(scope.row)">
                <el-icon><EditPen /></el-icon>
                编辑
              </el-button>
              <el-button size="small" type="danger" @click="handleDeleteProject(scope.row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="pagination.total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>
    
    <!-- 新建项目对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建项目"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入项目描述"
            :rows="3"
          />
        </el-form-item>
        <el-form-item label="项目状态">
          <el-select v-model="form.status" placeholder="请选择项目状态">
            <el-option label="活跃" value="active" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>
<style scoped>
.page-container {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}
</style>
<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Plus, Search, View, EditPen, Delete } from '@element-plus/icons-vue'
import { 
  getPerformanceProjects, 
  createPerformanceProject, 
  updatePerformanceProject, 
  deletePerformanceProject 
} from '@/api/performance-test'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const statusFilter = ref('')

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 项目数据
const projects = ref([])

// 对话框
const dialogVisible = ref(false)
const dialogType = ref('create') // create or edit
const form = ref({
  id: null,
  name: '',
  description: '',
  status: 'active'
})

// 获取项目列表
const fetchProjects = async () => {
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value,
      status: statusFilter.value
    }
    const response = await getPerformanceProjects(params)
    projects.value = response.results || []
    pagination.total = response.count || 0
  } catch (error) {
    console.error('获取项目列表失败:', error)
    ElMessage.error('获取项目列表失败')
  }
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    active: 'success',
    archived: 'info'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    active: '活跃',
    archived: '已归档'
  }
  return textMap[status] || status
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchProjects()
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewProject(row)
}

// 查看项目
const handleViewProject = (row) => {
  router.push(`/performance-test/projects/${row.id}`)
}

// 编辑项目
const handleEditProject = (row) => {
  dialogType.value = 'edit'
  form.value = {
    id: row.id,
    name: row.name,
    description: row.description,
    status: row.status
  }
  dialogVisible.value = true
}

// 删除项目
const handleDeleteProject = (row) => {
  ElMessageBox.confirm('确定要删除这个项目吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deletePerformanceProject(row.id)
      ElMessage.success('项目删除成功')
      fetchProjects()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    // 取消删除
  })
}

// 新建项目
const handleCreateProject = () => {
  dialogType.value = 'create'
  form.value = {
    id: null,
    name: '',
    description: '',
    status: 'active'
  }
  dialogVisible.value = true
}

// 提交表单
const submitForm = async () => {
  if (!form.value.name) {
    ElMessage.warning('请输入项目名称')
    return
  }

  try {
    if (dialogType.value === 'create') {
      await createPerformanceProject({
        name: form.value.name,
        description: form.value.description,
        status: form.value.status
      })
      ElMessage.success('项目创建成功')
    } else {
      await updatePerformanceProject(form.value.id, {
        name: form.value.name,
        description: form.value.description,
        status: form.value.status
      })
      ElMessage.success('项目更新成功')
    }
    dialogVisible.value = false
    fetchProjects()
  } catch (error) {
    ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
  }
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchProjects()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchProjects()
}

onMounted(() => {
  fetchProjects()
})
</script>

