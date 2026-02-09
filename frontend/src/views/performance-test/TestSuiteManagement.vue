<template>
  <div class="test-suite-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">测试套件管理</h2>
          <el-button type="primary" @click="handleCreateTestSuite">
            <el-icon><Plus /></el-icon>
            新建测试套件
          </el-button>
        </div>
      </template>
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入测试套件名称或描述"
              prefix-icon="Search"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="projectFilter"
              placeholder="所属项目"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option
                v-for="project in projects"
                :key="project.id"
                :label="project.name"
                :value="project.id"
              />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
          </el-col>
        </el-row>
      </div>
      
      <!-- 测试套件列表 -->
      <el-table
        :data="testSuites"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="套件ID" width="100" />
        <el-table-column prop="name" label="测试套件名称" />
        <el-table-column prop="description" label="套件描述" show-overflow-tooltip />
        <el-table-column prop="project_name" label="所属项目" width="150" />
        <el-table-column prop="collection_count" label="集合数量" width="120" />
        <el-table-column prop="request_count" label="请求数量" width="120" />
        <el-table-column prop="created_by" label="创建人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewTestSuite(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="primary" @click="handleEditTestSuite(scope.row)">
              <el-icon><EditPen /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="warning" @click="handleRunTestSuite(scope.row)">
              <el-icon><VideoPlay /></el-icon>
              运行
            </el-button>
            <el-button size="small" type="danger" @click="handleDeleteTestSuite(scope.row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
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
    </el-card>
    
    <!-- 新建测试套件对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建测试套件"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="套件名称" required>
          <el-input v-model="form.name" placeholder="请输入测试套件名称" />
        </el-form-item>
        <el-form-item label="所属项目" required>
          <el-select v-model="form.project_id" placeholder="请选择所属项目">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Worker数量">
          <el-input-number v-model="form.worker_count" :min="0" :max="10" placeholder="0为单机模式" />
          <div class="form-tip" style="font-size: 12px; color: #999; margin-left: 10px; display: inline-block;">
            0表示单机模式，大于0表示分布式模式的Worker进程数
          </div>
        </el-form-item>
        <el-form-item label="套件描述">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入测试套件描述"
            :rows="3"
          />
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

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Plus, Search, View, EditPen, VideoPlay, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const projectFilter = ref('')

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 数据
const testSuites = ref([])
const projects = ref([])
const loading = ref(false)

// 获取项目列表
const fetchProjects = async () => {
  try {
    const response = await api.get('/performance-testing/projects/', {
      params: { page_size: 100 }
    })
    projects.value = response.data.results
  } catch (error) {
    console.error('获取项目列表失败:', error)
  }
}

// 获取测试套件列表
const fetchTestSuites = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value,
      project: projectFilter.value
    }
    const response = await api.get('/performance-testing/test-suites/', { params })
    testSuites.value = response.data.results
    pagination.total = response.data.count
  } catch (error) {
    ElMessage.error('获取测试套件列表失败')
  } finally {
    loading.value = false
  }
}

// 对话框
const dialogVisible = ref(false)
const dialogType = ref('create')
const form = reactive({
  id: null,
  name: '',
  project_id: '',
  description: '',
  worker_count: 0
})

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchTestSuites()
}

// 处理行点击
const handleRowClick = (row) => {
  // handleViewTestSuite(row)
}

// 查看测试套件
const handleViewTestSuite = (row) => {
  router.push(`/performance-test/test-suites/${row.id}`)
}

// 编辑测试套件
const handleEditTestSuite = (row) => {
  dialogType.value = 'edit'
  form.id = row.id
  form.name = row.name
  form.project_id = row.project
  form.description = row.description
  dialogVisible.value = true
}

// 运行测试套件
const handleRunTestSuite = (row) => {
  ElMessageBox.confirm('确定要运行这个测试套件吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(async () => {
    try {
      await api.post(`/performance-testing/test-suites/${row.id}/run/`)
      ElMessage.success(`测试套件 ${row.name} 开始运行`)
      // router.push(`/performance-test/executions/create?test_suite_id=${row.id}`)
    } catch (error) {
      ElMessage.error('运行失败')
    }
  }).catch(() => {
    // 取消运行
  })
}

// 删除测试套件
const handleDeleteTestSuite = (row) => {
  ElMessageBox.confirm('确定要删除这个测试套件吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/performance-testing/test-suites/${row.id}/`)
      ElMessage.success('测试套件删除成功')
      fetchTestSuites()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    // 取消删除
  })
}

// 新建测试套件
const handleCreateTestSuite = () => {
  dialogType.value = 'create'
  form.id = null
  form.name = ''
  form.project_id = projectFilter.value || (projects.value.length > 0 ? projects.value[0].id : '')
  form.description = ''
  dialogVisible.value = true
}

// 提交表单
const submitForm = async () => {
  if (!form.name || !form.project_id) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  try {
    const data = {
      name: form.name,
      project: form.project_id,
      description: form.description,
      worker_count: form.worker_count
    }
    
    if (dialogType.value === 'create') {
      await api.post('/performance-testing/test-suites/', data)
      ElMessage.success('测试套件创建成功')
    } else {
      await api.put(`/performance-testing/test-suites/${form.id}/`, data)
      ElMessage.success('测试套件更新成功')
    }
    dialogVisible.value = false
    fetchTestSuites()
  } catch (error) {
    ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
  }
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchTestSuites()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchTestSuites()
}

onMounted(() => {
  fetchProjects()
  fetchTestSuites()
})
</script>

<style scoped>
/* 页面特定样式 */
.page-container {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}
.test-suite-management {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-filter {
  margin-bottom: 20px;
  padding: 20px 0;
  background-color: #fafafa;
  border-radius: 8px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>