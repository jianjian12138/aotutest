<template>
  <div class="scan-tasks">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>扫描任务管理</h2>
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
              <el-option label="待执行" value="pending" />
              <el-option label="执行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Plus, Search, View, VideoPlay, Delete } from '@element-plus/icons-vue'

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
const totalTasks = ref(30)

// 扫描任务数据
const scanTasks = ref([
  {
    id: 1,
    name: '电商网站安全扫描',
    target: 'https://example.com',
    scan_type: '深度扫描',
    status: 'completed',
    created_by: 'admin',
    created_at: '2026-01-10 14:30:00',
    finished_at: '2026-01-10 15:45:00'
  },
  {
    id: 2,
    name: '测试网站快速扫描',
    target: 'https://test.com',
    scan_type: '快速扫描',
    status: 'pending',
    created_by: 'testuser',
    created_at: '2026-01-11 09:15:00',
    finished_at: ''
  },
  {
    id: 3,
    name: '内部系统安全检查',
    target: '192.168.1.100',
    scan_type: '基础扫描',
    status: 'running',
    created_by: 'admin',
    created_at: '2026-01-11 14:20:00',
    finished_at: ''
  },
  {
    id: 4,
    name: 'API服务安全测试',
    target: 'https://api.example.com',
    scan_type: '深度扫描',
    status: 'failed',
    created_by: 'testuser',
    created_at: '2026-01-12 10:00:00',
    finished_at: '2026-01-12 10:15:00'
  },
  {
    id: 5,
    name: '管理后台安全审计',
    target: 'https://admin.example.com',
    scan_type: '深度扫描',
    status: 'completed',
    created_by: 'admin',
    created_at: '2026-01-12 14:00:00',
    finished_at: '2026-01-12 15:30:00'
  }
])

// 对话框
const dialogVisible = ref(false)
const form = ref({
  name: '',
  target: '',
  scan_type: '',
  description: ''
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
  ElMessage.info('搜索功能开发中')
}

// 处理行点击
const handleRowClick = (row) => {
  router.push(`/strix-security/scan-tasks/${row.id}`)
}

// 查看任务
const handleViewTask = (row) => {
  router.push(`/strix-security/scan-tasks/${row.id}`)
}

// 执行任务
const handleExecuteTask = (row) => {
  ElNotification({
    title: '提示',
    message: `开始执行扫描任务：${row.name}`,
    type: 'success'
  })
}

// 删除任务
const handleDeleteTask = (row) => {
  ElMessageBox.confirm('确定要删除这个扫描任务吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('扫描任务删除成功')
  }).catch(() => {
    // 取消删除
  })
}

// 新建任务
const handleCreateTask = () => {
  dialogVisible.value = true
  form.value = {
    name: '',
    target: '',
    scan_type: '',
    description: ''
  }
}

// 提交表单
const submitForm = () => {
  ElMessage.success('扫描任务创建成功')
  dialogVisible.value = false
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
.scan-tasks {
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