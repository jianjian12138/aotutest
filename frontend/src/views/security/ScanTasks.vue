<template>
  <div class="scan-tasks">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">扫描任务管理</h2>
          <el-button type="primary" @click="handleCreateTask">
            <el-icon><Plus /></el-icon>
            新建扫描任务
          </el-button>
        </div>
      </template>
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入任务名称或目标地址"
              prefix-icon="Search"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="statusFilter"
              placeholder="任务状态"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option label="已激活" :value="true" />
              <el-option label="未激活" :value="false" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
            />
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
          </el-col>
        </el-row>
      </div>
      
      <!-- 任务列表 -->
      <el-table
        :data="scanTasks"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="任务ID" width="100" />
        <el-table-column prop="name" label="任务名称" />
        <el-table-column prop="target" label="扫描目标" show-overflow-tooltip />
        <el-table-column prop="scan_type" label="扫描类型" width="120" />
        <el-table-column prop="status" label="状态" width="120">
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
        <el-table-column prop="finished_at" label="完成时间" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewTask(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="primary" @click="handleExecuteTask(scope.row)">
              <el-icon><VideoPlay /></el-icon>
              执行
            </el-button>
            <el-button size="small" type="danger" @click="handleDeleteTask(scope.row)">
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
          :total="totalTasks"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 新建任务对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建扫描任务"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="扫描目标" required>
          <el-input v-model="form.target" placeholder="请输入URL或IP地址" />
        </el-form-item>
        <el-form-item label="扫描类型" required>
          <el-select v-model="form.scan_type" placeholder="请选择扫描类型">
            <el-option label="基础扫描" value="basic" />
            <el-option label="深度扫描" value="deep" />
            <el-option label="快速扫描" value="quick" />
          </el-select>
        </el-form-item>
        <el-form-item label="扫描描述">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入扫描描述"
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

    <!-- 任务详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="任务详情"
      width="600px"
    >
      <el-descriptions border :column="1">
        <el-descriptions-item label="任务名称">{{ currentTask.name }}</el-descriptions-item>
        <el-descriptions-item label="扫描目标">{{ currentTask.target }}</el-descriptions-item>
        <el-descriptions-item label="扫描类型">
          {{ currentTask.scan_type === 'basic' ? '基础扫描' : currentTask.scan_type === 'deep' ? '深度扫描' : '快速扫描' }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(currentTask.status)">
            {{ getStatusText(currentTask.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建人">{{ currentTask.created_by }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ currentTask.created_at }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ currentTask.finished_at }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ currentTask.description }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailVisible = false">关闭</el-button>
          <el-button type="primary" @click="handleExecuteTask(currentTask)" :disabled="currentTask.status === 'running'">执行</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Plus, Search, View, VideoPlay, Delete } from '@element-plus/icons-vue'
import { 
  getSecurityProjects, 
  createSecurityProject, 
  deleteSecurityProject, 
  executeSecurityProject,
  getSecurityConfigs,
  getSecurityProject
} from '@/api/security'
import api from '@/utils/api'

const router = useRouter()

// 数据
const scanTasks = ref([])
const configs = ref([])
const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const dateRange = ref([])
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})
const totalTasks = computed(() => pagination.total)

// 详情对话框
const detailVisible = ref(false)
const currentTask = ref({})

// 获取配置列表
const fetchConfigs = async () => {
  try {
    const response = await getSecurityConfigs({ page_size: 100 })
    configs.value = response.results || []
  } catch (error) {
    console.error('获取配置列表失败:', error)
  }
}

// 获取任务列表
const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value,
      is_active: statusFilter.value
    }
    const response = await getSecurityProjects(params)
    scanTasks.value = response.results
    pagination.total = response.count
  } catch (error) {
    ElMessage.error('获取扫描任务失败')
  } finally {
    loading.value = false
  }
}

// 对话框
const dialogVisible = ref(false)
const form = ref({
  name: '',
  target: '',
  scan_type: 'deep',
  description: '',
  config: null
})

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    pending: 'warning',
    running: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchData()
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewTask(row)
}

// 查看任务
const handleViewTask = async (row) => {
  try {
    const response = await getSecurityProject(row.id)
    currentTask.value = response
    detailVisible.value = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

// 执行任务
const handleExecuteTask = async (row) => {
  try {
    await executeSecurityProject(row.id)
    ElNotification({
      title: '提示',
      message: `已触发扫描任务：${row.name}`,
      type: 'success'
    })
    fetchData()
  } catch (error) {
    ElMessage.error('执行失败')
  }
}

// 删除任务
const handleDeleteTask = (row) => {
  ElMessageBox.confirm('确定要删除这个扫描任务吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteSecurityProject(row.id)
      ElMessage.success('扫描任务删除成功')
      fetchData()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 新建任务
const handleCreateTask = () => {
  dialogVisible.value = true
  form.value = {
    name: '',
    target: '',
    scan_type: 'deep',
    description: '',
    config: configs.value.length > 0 ? configs.value[0].id : null
  }
}

const submitForm = async () => {
  if (!form.value.name || !form.value.target) {
    ElMessage.warning('请填写必要信息')
    return
  }
  try {
    await createSecurityProject(form.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  fetchData()
}

const handleCurrentChange = (val) => {
  pagination.currentPage = val
  fetchData()
}

onMounted(() => {
  fetchConfigs()
  fetchData()
})
</script>

<style scoped>


.scan-tasks {
  padding: 0px;
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