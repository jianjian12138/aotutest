<template>
  <div class="execution-log-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>执行日志管理</h2>
        </div>
      </template>
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入任务名称或日志内容"
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
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
              <el-option label="部分成功" value="partial" />
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
      
      <!-- 日志列表 -->
      <el-table
        :data="executionLogs"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="日志ID" width="100" />
        <el-table-column prop="task_id" label="任务ID" width="100" />
        <el-table-column prop="task_name" label="任务名称" />
        <el-table-column prop="status" label="执行状态" width="120">
          <template #default="scope">
            <el-tag
              :type="getStatusTagType(scope.row.status)"
              size="small"
            >
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="executed_by" label="执行人" width="120" />
        <el-table-column prop="execution_time" label="执行时间" width="120" />
        <el-table-column prop="start_time" label="开始时间" width="180" />
        <el-table-column prop="end_time" label="结束时间" width="180" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewLog(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="danger" @click="handleDeleteLog(scope.row)">
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
          :total="totalLogs"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 日志详情对话框 -->
    <el-dialog
      v-model="logDetailVisible"
      title="日志详情"
      width="80%"
      height="80%"
    >
      <el-scrollbar style="height: 100%;">
        <div class="log-detail-content">
          <!-- 日志基本信息 -->
          <div class="log-basic-info">
            <h3>基本信息</h3>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="日志ID">{{ selectedLog.id }}</el-descriptions-item>
              <el-descriptions-item label="任务ID">{{ selectedLog.task_id }}</el-descriptions-item>
              <el-descriptions-item label="任务名称">{{ selectedLog.task_name }}</el-descriptions-item>
              <el-descriptions-item label="执行状态">
                <el-tag
                  :type="getStatusTagType(selectedLog.status)"
                  size="small"
                >
                  {{ getStatusText(selectedLog.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="执行人">{{ selectedLog.executed_by }}</el-descriptions-item>
              <el-descriptions-item label="执行时间">{{ selectedLog.execution_time }}</el-descriptions-item>
              <el-descriptions-item label="开始时间">{{ selectedLog.start_time }}</el-descriptions-item>
              <el-descriptions-item label="结束时间">{{ selectedLog.end_time }}</el-descriptions-item>
            </el-descriptions>
          </div>
          
          <!-- 详细日志内容 -->
          <div class="log-content" style="margin-top: 20px;">
            <h3>详细日志</h3>
            <el-scrollbar style="height: 400px;">
              <div class="logs-container">
                <div
                  v-for="(log, index) in selectedLog.logs"
                  :key="index"
                  class="log-item"
                  :class="{'log-error': log.level === 'error', 'log-success': log.level === 'success'}"
                >
                  <span class="log-time">{{ log.timestamp }}</span>
                  <span class="log-level">{{ log.level.toUpperCase() }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </el-scrollbar>
          </div>
        </div>
      </el-scrollbar>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="logDetailVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Search, View, Delete } from '@element-plus/icons-vue'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const statusFilter = ref('')
const dateRange = ref([])

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20
})
const totalLogs = ref(35)

// 执行日志数据
const executionLogs = ref([
  {
    id: 1,
    task_id: 1,
    task_name: '电商网站首页测试',
    status: 'success',
    executed_by: 'admin',
    execution_time: '00:01:23',
    start_time: '2026-01-10 14:30:00',
    end_time: '2026-01-10 14:31:23'
  },
  {
    id: 2,
    task_id: 2,
    task_name: '用户登录流程测试',
    status: 'failed',
    executed_by: 'testuser',
    execution_time: '00:00:45',
    start_time: '2026-01-11 09:15:00',
    end_time: '2026-01-11 09:15:45'
  },
  {
    id: 3,
    task_id: 3,
    task_name: '商品搜索功能测试',
    status: 'success',
    executed_by: 'testuser',
    execution_time: '00:02:15',
    start_time: '2026-01-11 14:20:00',
    end_time: '2026-01-11 14:22:15'
  },
  {
    id: 4,
    task_id: 4,
    task_name: '购物车功能测试',
    status: 'failed',
    executed_by: 'admin',
    execution_time: '00:01:15',
    start_time: '2026-01-12 10:00:00',
    end_time: '2026-01-12 10:01:15'
  },
  {
    id: 5,
    task_id: 5,
    task_name: '订单流程测试',
    status: 'success',
    executed_by: 'testuser',
    execution_time: '00:03:30',
    start_time: '2026-01-12 14:00:00',
    end_time: '2026-01-12 14:03:30'
  }
])

// 选中的日志
const selectedLog = ref({
  id: 0,
  task_id: 0,
  task_name: '',
  status: '',
  executed_by: '',
  execution_time: '',
  start_time: '',
  end_time: '',
  logs: []
})

// 日志详情对话框
const logDetailVisible = ref(false)

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    success: 'success',
    failed: 'danger',
    partial: 'warning'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    success: '成功',
    failed: '失败',
    partial: '部分成功'
  }
  return textMap[status] || status
}

// 搜索
const handleSearch = () => {
  ElMessage.info('搜索功能开发中')
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewLog(row)
}

// 查看日志
const handleViewLog = (row) => {
  // 模拟加载详细日志
  selectedLog.value = {
    ...row,
    logs: [
      { timestamp: '2026-01-10 14:30:01', level: 'info', message: '任务开始执行' },
      { timestamp: '2026-01-10 14:30:02', level: 'info', message: '初始化Chrome浏览器' },
      { timestamp: '2026-01-10 14:30:05', level: 'info', message: '打开网页：https://www.example.com' },
      { timestamp: '2026-01-10 14:30:10', level: 'success', message: '成功加载首页' },
      { timestamp: '2026-01-10 14:30:15', level: 'info', message: '点击搜索框' },
      { timestamp: '2026-01-10 14:30:20', level: 'info', message: '输入搜索关键词：测试商品' },
      { timestamp: '2026-01-10 14:30:25', level: 'success', message: '搜索成功，显示结果列表' },
      { timestamp: '2026-01-10 14:31:23', level: 'info', message: '任务执行完成' }
    ]
  }
  logDetailVisible.value = true
}

// 删除日志
const handleDeleteLog = (row) => {
  ElMessageBox.confirm('确定要删除这个日志吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('日志删除成功')
  }).catch(() => {
    // 取消删除
  })
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
.execution-log-management {
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

.logs-container {
  padding: 10px;
}

.log-item {
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 4px;
  background-color: #f5f5f5;
}

.log-time {
  color: #909399;
  margin-right: 10px;
  font-size: 12px;
}

.log-level {
  margin-right: 10px;
  font-weight: bold;
  font-size: 12px;
}

.log-error {
  background-color: #fff1f0;
}

.log-error .log-level {
  color: #f56c6c;
}

.log-success {
  background-color: #f0f9eb;
}

.log-success .log-level {
  color: #67c23a;
}
</style>