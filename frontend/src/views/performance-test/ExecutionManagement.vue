<template>
  <div class="execution-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">执行管理</h2>
          <el-button type="primary" @click="handleCreateExecution">
            <el-icon><Plus /></el-icon>
            新建执行
          </el-button>
        </div>
      </template>
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入测试套件名称或执行ID"
              prefix-icon="Search"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="statusFilter"
              placeholder="执行状态"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option label="运行中" value="RUNNING" />
              <el-option label="已完成" value="COMPLETED" />
              <el-option label="已失败" value="FAILED" />
              <el-option label="已停止" value="STOPPED" />
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
      
      <!-- 执行列表 -->
      <el-table
        :data="executions"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="执行ID" width="100" />
        <el-table-column prop="test_suite.name" label="测试套件" show-overflow-tooltip />
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
        <el-table-column prop="concurrency" label="并发数" width="100" />
        <el-table-column prop="total_requests" label="请求总数" width="120" />
        <el-table-column prop="response_time_avg" label="平均响应时间(ms)" width="150" />
        <el-table-column prop="success_rate" label="成功率" width="100">
          <template #default="scope">
            <el-progress :percentage="scope.row.success_rate || 0" :stroke-width="16" text-inside :show-text="true" />
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="180" />
        <el-table-column prop="end_time" label="结束时间" width="180" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewExecution(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="success" @click="handleViewReport(scope.row)">
              <el-icon><DataAnalysis /></el-icon>
              报告
            </el-button>
            <template v-if="scope.row.status === 'RUNNING'">
              <el-button size="small" type="warning" @click="handleStopExecution(scope.row)">
                <el-icon><VideoPause /></el-icon>
                停止
              </el-button>
            </template>
            <el-button size="small" type="danger" @click="handleDeleteExecution(scope.row)">
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
          :total="totalExecutions"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Plus, Search, View, DataAnalysis, VideoPause, Delete } from '@element-plus/icons-vue'
import { 
  getPerformanceExecutions, 
  deletePerformanceExecution, 
  stopPerformanceTest 
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

// 数据
const executions = ref([])
const loading = ref(false)

// 获取执行列表
const fetchExecutions = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value,
      status: statusFilter.value
    }
    const response = await getPerformanceExecutions(params)
    executions.value = response.data.results || response.results || []
    pagination.total = response.data.count || response.count || 0
  } catch (error) {
    console.error('获取执行列表失败:', error)
    ElMessage.error('获取执行列表失败')
  } finally {
    loading.value = false
  }
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    RUNNING: 'primary',
    COMPLETED: 'success',
    FAILED: 'danger',
    STOPPED: 'warning'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    RUNNING: '运行中',
    COMPLETED: '已完成',
    FAILED: '已失败',
    STOPPED: '已停止'
  }
  return textMap[status] || status
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchExecutions()
}

// 处理行点击
const handleRowClick = (row) => {
  // handleViewExecution(row)
}

// 查看执行
const handleViewExecution = (row) => {
  router.push(`/performance-test/executions/${row.id}`)
}

// 查看报告
const handleViewReport = (row) => {
  router.push(`/performance-test/executions/${row.id}/report`)
}

// 停止执行
const handleStopExecution = (row) => {
  ElMessageBox.confirm('确定要停止这个执行吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await stopPerformanceTest(row.id)
      ElMessage.success(`执行 ${row.id} 已停止`)
      fetchExecutions()
    } catch (error) {
      ElMessage.error('停止失败')
    }
  }).catch(() => {
    // 取消停止
  })
}

// 删除执行
const handleDeleteExecution = (row) => {
  ElMessageBox.confirm('确定要删除这个执行记录吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deletePerformanceExecution(row.id)
      ElMessage.success('执行记录删除成功')
      fetchExecutions()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    // 取消删除
  })
}

// 新建执行
const handleCreateExecution = () => {
  router.push('/performance-test/executions/create')
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchExecutions()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchExecutions()
}

onMounted(() => {
  fetchExecutions()
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
.execution-management {
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