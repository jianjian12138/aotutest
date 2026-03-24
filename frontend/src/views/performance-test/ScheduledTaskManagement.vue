<template>
  <BasePage title="定时任务管理">
    <template #actions>
      <el-button type="primary" @click="handleCreateScheduledTask">
        <el-icon><Plus /></el-icon>
        新建任务
      </el-button>
    </template>

    <div class="content">
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入定时任务名称或描述"
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
              <el-option label="运行中" value="RUNNING" />
              <el-option label="已暂停" value="PAUSED" />
              <el-option label="已完成" value="COMPLETED" />
              <el-option label="已失败" value="FAILED" />
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
      
      <!-- 定时任务列表 -->
      <el-table
        :data="scheduledTasks"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="任务ID" width="100" />
        <el-table-column prop="name" label="任务名称" />
        <el-table-column prop="description" label="任务描述" show-overflow-tooltip />
        <el-table-column prop="test_suite.name" label="测试套件" width="180" />
        <el-table-column prop="cron_expression" label="Cron表达式" width="200" />
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
        <el-table-column prop="next_run_time" label="下次运行时间" width="180" />
        <el-table-column prop="last_run_time" label="上次运行时间" width="180" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewScheduledTask(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="primary" @click="handleEditScheduledTask(scope.row)">
              <el-icon><EditPen /></el-icon>
              编辑
            </el-button>
            <template v-if="scope.row.status === 'RUNNING'">
              <el-button size="small" type="warning" @click="handlePauseScheduledTask(scope.row)">
                <el-icon><VideoPause /></el-icon>
                暂停
              </el-button>
            </template>
            <template v-else>
              <el-button size="small" type="success" @click="handleResumeScheduledTask(scope.row)">
                <el-icon><VideoPlay /></el-icon>
                恢复
              </el-button>
            </template>
            <el-button size="small" type="danger" @click="handleDeleteScheduledTask(scope.row)">
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
    
    <!-- 新建定时任务对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建定时任务"
      width="700px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="请输入定时任务名称" />
        </el-form-item>
        <el-form-item label="测试套件" required>
          <el-select v-model="form.test_suite_id" placeholder="请选择测试套件">
            <el-option
              v-for="suite in testSuites"
              :key="suite.id"
              :label="suite.name"
              :value="suite.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron表达式" required>
          <el-input v-model="form.cron_expression" placeholder="请输入Cron表达式，如：0 0 * * * ?" />
        </el-form-item>
        <el-form-item label="并发数">
          <el-input-number v-model="form.concurrency" :min="1" :max="1000" :step="1" />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入任务描述"
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
  </BasePage>
</template>
<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Plus, Search, View, EditPen, VideoPlay, VideoPause, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'

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
const scheduledTasks = ref([])
const testSuites = ref([])
const loading = ref(false)

// 获取测试套件列表
const fetchTestSuites = async () => {
  try {
    const response = await api.get('/performance-testing/test-suites/', {
      params: { page_size: 100 }
    })
    testSuites.value = response.data.results
  } catch (error) {
    console.error('获取测试套件列表失败:', error)
  }
}

// 获取定时任务列表
const fetchScheduledTasks = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value,
      status: statusFilter.value
    }
    const response = await api.get('/performance-testing/scheduled-tasks/', { params })
    scheduledTasks.value = response.data.results
    pagination.total = response.data.count
  } catch (error) {
    ElMessage.error('获取定时任务列表失败')
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
  test_suite_id: '',
  cron_expression: '',
  concurrency: 50,
  description: ''
})

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    RUNNING: 'success',
    PAUSED: 'warning',
    COMPLETED: 'info',
    FAILED: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    RUNNING: '运行中',
    PAUSED: '已暂停',
    COMPLETED: '已完成',
    FAILED: '已失败'
  }
  return textMap[status] || status
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchScheduledTasks()
}

// 处理行点击
const handleRowClick = (row) => {
  // handleViewScheduledTask(row)
}

// 查看定时任务
const handleViewScheduledTask = (row) => {
  router.push(`/performance-test/scheduled-tasks/${row.id}`)
}

// 编辑定时任务
const handleEditScheduledTask = (row) => {
  dialogType.value = 'edit'
  form.id = row.id
  form.name = row.name
  form.test_suite_id = row.test_suite?.id || row.test_suite // Adjust based on API response
  form.cron_expression = row.cron_expression
  form.concurrency = row.concurrency
  form.description = row.description
  dialogVisible.value = true
}

// 暂停定时任务
const handlePauseScheduledTask = (row) => {
  ElMessageBox.confirm('确定要暂停这个定时任务吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await api.post(`/performance-testing/scheduled-tasks/${row.id}/pause/`)
      ElMessage.success(`定时任务 ${row.name} 已暂停`)
      fetchScheduledTasks()
    } catch (error) {
      ElMessage.error('暂停失败')
    }
  }).catch(() => {
    // 取消暂停
  })
}

// 恢复定时任务
const handleResumeScheduledTask = (row) => {
  ElMessageBox.confirm('确定要恢复这个定时任务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(async () => {
    try {
      await api.post(`/performance-testing/scheduled-tasks/${row.id}/resume/`)
      ElMessage.success(`定时任务 ${row.name} 已恢复`)
      fetchScheduledTasks()
    } catch (error) {
      ElMessage.error('恢复失败')
    }
  }).catch(() => {
    // 取消恢复
  })
}

// 删除定时任务
const handleDeleteScheduledTask = (row) => {
  ElMessageBox.confirm('确定要删除这个定时任务吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/performance-testing/scheduled-tasks/${row.id}/`)
      ElMessage.success('定时任务删除成功')
      fetchScheduledTasks()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    // 取消删除
  })
}

// 新建定时任务
const handleCreateScheduledTask = () => {
  dialogType.value = 'create'
  form.id = null
  form.name = ''
  form.test_suite_id = testSuites.value.length > 0 ? testSuites.value[0].id : ''
  form.cron_expression = ''
  form.concurrency = 50
  form.description = ''
  dialogVisible.value = true
}

// 提交表单
const submitForm = async () => {
  if (!form.name || !form.test_suite_id || !form.cron_expression) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  try {
    const data = {
      name: form.name,
      test_suite: form.test_suite_id,
      cron_expression: form.cron_expression,
      concurrency: form.concurrency,
      description: form.description
    }
    
    if (dialogType.value === 'create') {
      await api.post('/performance-testing/scheduled-tasks/', data)
      ElMessage.success('定时任务创建成功')
    } else {
      await api.put(`/performance-testing/scheduled-tasks/${form.id}/`, data)
      ElMessage.success('定时任务更新成功')
    }
    dialogVisible.value = false
    fetchScheduledTasks()
  } catch (error) {
    ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
  }
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchScheduledTasks()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchScheduledTasks()
}

onMounted(() => {
  fetchTestSuites()
  fetchScheduledTasks()
})
</script>

<style scoped>
/* 页面特定样式 */

.scheduled-task-management {
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
