<template>
  <div class="execution-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>执行管理</h2>
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
        <el-table-column prop="test_suite.name" label="测试套件" />
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Plus, Search, View, DataAnalysis, VideoPause, Delete } from '@element-plus/icons-vue'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const statusFilter = ref('')

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20
})
const totalExecutions = ref(23)

// 执行数据
const executions = ref([
  {
    id: 1,
    test_suite: { name: '用户登录性能测试' },
    status: 'COMPLETED',
    concurrency: 100,
    total_requests: 10000,
    response_time_avg: 123,
    success_rate: 99.8,
    start_time: '2026-01-12 14:30:00',
    end_time: '2026-01-12 14:45:00'
  },
  {
    id: 2,
    test_suite: { name: '商品列表性能测试' },
    status: 'COMPLETED',
    concurrency: 50,
    total_requests: 5000,
    response_time_avg: 256,
    success_rate: 99.5,
    start_time: '2026-01-12 10:15:00',
    end_time: '2026-01-12 10:30:00'
  },
  {
    id: 3,
    test_suite: { name: '订单流程性能测试' },
    status: 'FAILED',
    concurrency: 30,
    total_requests: 2000,
    response_time_avg: 456,
    success_rate: 85.2,
    start_time: '2026-01-11 16:00:00',
    end_time: '2026-01-11 16:15:00'
  },
  {
    id: 4,
    test_suite: { name: 'API基础性能测试' },
    status: 'RUNNING',
    concurrency: 200,
    total_requests: 5000,
    response_time_avg: 89,
    success_rate: 99.9,
    start_time: '2026-01-12 16:30:00',
    end_time: null
  }
])

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
  ElMessage.info('搜索功能开发中')
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewExecution(row)
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
  }).then(() => {
    ElMessage.success(`执行 ${row.id} 已停止`)
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
  }).then(() => {
    ElMessage.success('执行记录删除成功')
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
  pagination.value.pageSize = size
}

const handleCurrentChange = (current) => {
  pagination.value.currentPage = current
}
</script>

<style scoped>
.execution-management {
  padding: 20px;
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