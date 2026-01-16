<template>
  <div class="scheduled-tasks">
    <div class="header">
      <h3>定时任务管理</h3>
      <el-button type="primary" @click="handleCreateClick">
        <el-icon><Plus /></el-icon>
        新建定时任务
      </el-button>
    </div>

    <!-- 筛选条件 -->
    <div class="filters">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-select v-model="filters.task_type" placeholder="任务类型" clearable>
            <el-option label="测试套件执行" value="TEST_SUITE" />
            <el-option label="API请求执行" value="API_REQUEST" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filters.trigger_type" placeholder="触发器类型" clearable>
            <el-option label="Cron表达式" value="CRON" />
            <el-option label="固定间隔" value="INTERVAL" />
            <el-option label="单次执行" value="ONCE" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filters.status" placeholder="任务状态" clearable>
            <el-option label="激活" value="ACTIVE" />
            <el-option label="暂停" value="PAUSED" />
            <el-option label="已完成" value="COMPLETED" />
            <el-option label="失败" value="FAILED" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" @click="loadTasks">搜索</el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 任务列表 -->
    <div class="task-list">
      <el-table :data="tasks" v-loading="loading">
        <el-table-column prop="name" label="任务名称" min-width="200" />
        <el-table-column prop="task_type" label="任务类型" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.task_type === 'TEST_SUITE' ? 'success' : 'primary'">
              {{ scope.row.task_type === 'TEST_SUITE' ? '测试套件' : 'API请求' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_type" label="触发器类型" width="120">
          <template #default="scope">
            <el-tag>
              {{ scope.row.trigger_type === 'CRON' ? 'Cron' : scope.row.trigger_type === 'INTERVAL' ? '间隔' : '单次' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'ACTIVE' ? 'success' : scope.row.status === 'PAUSED' ? 'warning' : 'info'">
              {{ scope.row.status === 'ACTIVE' ? '激活' : scope.row.status === 'PAUSED' ? '暂停' : '完成' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="notification_type_display" label="通知类型" width="120">
          <template #default="scope">
            <el-tag 
              :type="getNotificationTypeTag(scope.row.notification_type_display)" 
              size="small"
            >
              {{ scope.row.notification_type_display || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_time" label="下次执行时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.next_run_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_run_time" label="上次执行时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.last_run_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="runTaskNow(scope.row)" :loading="scope.row.running">
              立即执行
            </el-button>
            <el-dropdown @command="(command) => handleTaskAction(command, scope.row)">
              <el-button size="small">
                更多<el-icon><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">编辑</el-dropdown-item>
                  <el-dropdown-item command="pause" v-if="scope.row.status === 'ACTIVE'">暂停</el-dropdown-item>
                  <el-dropdown-item command="activate" v-if="scope.row.status === 'PAUSED'">激活</el-dropdown-item>
                  <el-dropdown-item command="logs">执行日志</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.current"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadTasks"
        @current-change="loadTasks"
      />
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTask ? '编辑定时任务' : '新建定时任务'"
      width="800px"
      @close="resetTaskForm"
    >
      <el-form :model="taskForm" label-width="120px">
        <el-form-item label="任务名称" required>
          <el-input v-model="taskForm.name" placeholder="请输入任务名称" />
        </el-form-item>
        
        <el-form-item label="任务描述">
          <el-input v-model="taskForm.description" type="textarea" placeholder="请输入任务描述" />
        </el-form-item>
        
        <el-form-item label="任务类型" required>
          <el-radio-group v-model="taskForm.task_type">
            <el-radio label="TEST_SUITE">测试套件执行</el-radio>
            <el-radio label="API_REQUEST">API请求执行</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="触发器类型" required>
          <el-radio-group v-model="taskForm.trigger_type">
            <el-radio label="CRON">Cron表达式</el-radio>
            <el-radio label="INTERVAL">固定间隔</el-radio>
            <el-radio label="ONCE">单次执行</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <!-- 根据触发器类型显示不同配置 -->
        <el-form-item v-if="taskForm.trigger_type === 'CRON'" label="Cron表达式" required>
          <el-input v-model="taskForm.cron_expression" placeholder="0 0 * * *" />
          <div class="cron-help">
            <el-tooltip
              raw-content
              placement="top"
            >
              <template #content>
                <div style="line-height: 1.6; text-align: left;">
                  <div>Cron表达式格式: 分 时 日 月 周</div>
                  <div>• 分: 0-59</div>
                  <div>• 时: 0-23</div>
                  <div>• 日: 1-31</div>
                  <div>• 月: 1-12 或 JAN-DEC</div>
                  <div>• 周: 0-6 或 SUN-SAT (0=周日)</div>
                  <div style="margin-top: 8px;">常用示例:</div>
                  <div>• 每天0点: 0 0 * * *</div>
                  <div>• 每小时: 0 * * * *</div>
                  <div>• 每周一9点: 0 9 * * 1</div>
                  <div>• 每月1号0点: 0 0 1 * *</div>
                </div>
              </template>
              <span style="cursor: pointer; color: #409EFF;">Cron帮助信息</span>
            </el-tooltip>
          </div>
        </el-form-item>
        
        <el-form-item v-if="taskForm.trigger_type === 'INTERVAL'" label="间隔时间" required>
          <el-input-number v-model="taskForm.interval_seconds" :min="60" :step="60" />
          <span class="unit">秒</span>
        </el-form-item>
        
        <el-form-item v-if="taskForm.trigger_type === 'ONCE'" label="执行时间" required>
          <el-date-picker
            v-model="taskForm.execute_at"
            type="datetime"
            placeholder="选择执行时间"
          />
        </el-form-item>
        
        <!-- 根据任务类型显示不同配置 -->
        <el-form-item v-if="taskForm.task_type === 'TEST_SUITE'" label="测试套件" required>
          <el-select v-model="taskForm.test_suite" placeholder="请选择测试套件">
            <el-option
              v-for="suite in testSuites"
              :key="suite.id"
              :label="suite.name"
              :value="suite.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="taskForm.task_type === 'API_REQUEST'" label="API请求" required>
          <el-select v-model="taskForm.api_request" placeholder="请选择API请求">
            <el-option
              v-for="request in apiRequests"
              :key="request.id"
              :label="request.name"
              :value="request.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="执行环境">
          <el-select v-model="taskForm.environment" placeholder="请选择执行环境">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="通知设置">
          <el-checkbox v-model="taskForm.notify_on_success">执行成功时通知</el-checkbox>
          <el-checkbox v-model="taskForm.notify_on_failure">执行失败时通知</el-checkbox>
        </el-form-item>
        
        <el-form-item v-if="taskForm.notify_on_success || taskForm.notify_on_failure" label="通知类型">
          <el-select v-model="taskForm.notification_type" placeholder="请选择通知类型">
            <el-option label="邮箱通知" value="email" />
            <el-option label="Webhook机器人" value="webhook" />
            <el-option label="两种都发送" value="both" />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="(taskForm.notify_on_success || taskForm.notify_on_failure) && taskForm.notification_type !== 'webhook'" label="通知邮箱">
          <el-select
            v-model="taskForm.notify_emails"
            multiple
            filterable
            placeholder="请选择通知邮箱"
          >
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.display_name"
              :value="user.email"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitTaskForm" :loading="submitting">
          {{ editingTask ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 执行日志对话框 -->
    <el-dialog v-model="showLogsDialog" title="任务执行日志" width="1000px">
      <el-table :data="executionLogs" v-loading="logsLoading">
        <el-table-column prop="start_time" label="开始时间" width="180">
          <template #default="scope">
            <div class="time-cell">{{ formatDateTime(scope.row.start_time) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="180">
          <template #default="scope">
            <div class="time-cell">{{ formatDateTime(scope.row.end_time) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'COMPLETED' ? 'success' : 'danger'">
              {{ scope.row.status === 'COMPLETED' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" width="300" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { 
  getScheduledTasks, 
  createScheduledTask, 
  updateScheduledTask, 
  deleteScheduledTask, 
  runScheduledTask, 
  getExecutionLogs,
  getTestSuites,
  getApiRequests,
  getEnvironments,
  getUsers
} from '@/api/api-testing.js'

// 数据状态
const tasks = ref([])
const executionLogs = ref([])
const testSuites = ref([])
const apiRequests = ref([])
const environments = ref([])
const users = ref([]) // 添加用户列表
const loading = ref(false)
const logsLoading = ref(false)
const submitting = ref(false)
const showCreateDialog = ref(false)
const showLogsDialog = ref(false)
const editingTask = ref(null)

// 筛选条件
const filters = reactive({
  task_type: '',
  trigger_type: '',
  status: ''
})

// 分页配置
const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

// 表单数据
const taskForm = reactive({
  name: '',
  description: '',
  task_type: 'TEST_SUITE',
  trigger_type: 'CRON',
  cron_expression: '0 0 * * *',
  interval_seconds: 3600,
  execute_at: '',
  test_suite: '',
  api_request: '',
  environment: '',
  notify_on_success: false,
  notify_on_failure: false,
  notify_emails: []
})

// 生命周期
onMounted(() => {
  loadTasks()
  loadTestSuites()
  loadApiRequests()
  loadEnvironments()
  loadUsers() // 加载用户列表
})

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.current,
      page_size: pagination.size,
      ...filters
    }
    const response = await getScheduledTasks(params)
    tasks.value = response.data.results
    pagination.total = response.data.count
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

// 加载测试套件
const loadTestSuites = async () => {
  try {
    const response = await getTestSuites()
    testSuites.value = response.data.results
  } catch (error) {
    console.error('加载测试套件失败:', error)
  }
}

// 加载API请求
const loadApiRequests = async () => {
  try {
    const response = await getApiRequests()
    apiRequests.value = response.data.results
  } catch (error) {
    console.error('加载API请求失败:', error)
  }
}

// 加载环境
const loadEnvironments = async () => {
  try {
    const response = await getEnvironments()
    environments.value = response.data.results
  } catch (error) {
    console.error('加载环境失败:', error)
  }
}

// 加载用户列表
const loadUsers = async () => {
  try {
    const response = await getUsers()
    // 处理分页数据结构
    const usersData = response.data.results || response.data
    users.value = usersData.map(user => ({
      ...user,
      display_name: user.first_name ? `${user.first_name}（${user.email}）` : `${user.username}（${user.email}）`
    }))
  } catch (error) {
    console.error('加载用户列表失败:', error)
  }
}

// 新建按钮点击
const handleCreateClick = () => {
  console.log('新建按钮点击')
  editingTask.value = null
  resetTaskForm()
  showCreateDialog.value = true
}

// 重置表单
const resetTaskForm = () => {
  Object.assign(taskForm, {
    name: '',
    description: '',
    task_type: 'TEST_SUITE',
    trigger_type: 'CRON',
    cron_expression: '0 0 * * *',
    interval_seconds: 3600,
    execute_at: '',
    test_suite: '',
    api_request: '',
    environment: '',
    notify_on_success: false,
    notify_on_failure: false,
    notification_type: 'email',
    notify_emails: []
  })
}

// 重置筛选
const resetFilters = () => {
  Object.assign(filters, {
    task_type: '',
    trigger_type: '',
    status: ''
  })
  loadTasks()
}

// 提交任务表单
const submitTaskForm = async () => {
  submitting.value = true
  try {
    // 准备提交数据，确保格式正确
    const submitData = {
      name: taskForm.name,
      description: taskForm.description,
      task_type: taskForm.task_type,
      trigger_type: taskForm.trigger_type,
      notify_on_success: taskForm.notify_on_success,
      notify_on_failure: taskForm.notify_on_failure,
      notification_type_input: taskForm.notification_type,
      notify_emails: taskForm.notify_emails,
      environment: taskForm.environment
    }

    // 根据触发器类型添加对应字段
    if (taskForm.trigger_type === 'CRON') {
      submitData.cron_expression = taskForm.cron_expression
    } else if (taskForm.trigger_type === 'INTERVAL') {
      submitData.interval_seconds = taskForm.interval_seconds
    } else if (taskForm.trigger_type === 'ONCE') {
      submitData.execute_at = taskForm.execute_at
    }

    // 根据任务类型添加对应字段
    if (taskForm.task_type === 'TEST_SUITE') {
      submitData.test_suite = taskForm.test_suite
    } else if (taskForm.task_type === 'API_REQUEST') {
      submitData.api_request = taskForm.api_request
    }

    if (editingTask.value) {
      await updateScheduledTask(editingTask.value.id, submitData)
      ElMessage.success('更新任务成功')
    } else {
      await createScheduledTask(submitData)
      ElMessage.success('创建任务成功')
    }
    showCreateDialog.value = false
    loadTasks()
  } catch (error) {
    console.error('任务操作失败:', error)
    ElMessage.error(error.response?.data?.error || 
                   error.response?.data?.detail || 
                   (editingTask.value ? '更新任务失败' : '创建任务失败'))
  } finally {
    submitting.value = false
  }
}

// 立即执行任务
const runTaskNow = async (task) => {
  try {
    task.running = true
    await runScheduledTask(task.id)
    ElMessage.success('任务已开始执行')
    // 等待一段时间后刷新任务状态
    setTimeout(() => {
      loadTasks()
    }, 2000)
  } catch (error) {
    ElMessage.error('执行任务失败')
  } finally {
    task.running = false
  }
}

// 格式化日期时间
const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).replace(/\//g, '-')
}

// 获取通知类型标签样式
const getNotificationTypeTag = (typeDisplay) => {
  const typeMap = {
    '邮箱通知': '',
    'Webhook机器人': 'primary',
    '两种都发送': 'warning'
  }
  return typeMap[typeDisplay] || 'info'
}

// 查看执行日志
const viewTaskLogs = async (task) => {
  logsLoading.value = true
  try {
    const response = await getExecutionLogs(task.id)
    executionLogs.value = response.data.results || response.data
    showLogsDialog.value = true
  } catch (error) {
    console.error('加载执行日志失败:', error)
    ElMessage.error('加载执行日志失败')
  } finally {
    logsLoading.value = false
  }
}

// 处理任务操作
const handleTaskAction = (command, task) => {
  switch (command) {
    case 'pause':
      pauseTask(task)
      break
    case 'activate':
      activateTask(task)
      break
    case 'edit':
      editTask(task)
      break
    case 'logs':
      viewTaskLogs(task)
      break
    case 'delete':
      deleteTask(task)
      break
  }
}

// 编辑任务
const editTask = (task) => {
  editingTask.value = task
  Object.assign(taskForm, {
    name: task.name,
    description: task.description,
    task_type: task.task_type,
    trigger_type: task.trigger_type,
    cron_expression: task.cron_expression,
    interval_seconds: task.interval_seconds,
    execute_at: task.execute_at,
    test_suite: task.test_suite || null,
    api_request: task.api_request || null,
    environment: task.environment || null,
    notify_on_success: task.notify_on_success,
    notify_on_failure: task.notify_on_failure,
    notification_type: task.notification_type || 'email',
    notify_emails: task.notify_emails || []
  })
  console.log('编辑任务数据回显:', {
    test_suite: task.test_suite,
    environment: task.environment,
    taskForm_test_suite: taskForm.test_suite,
    taskForm_environment: taskForm.environment
  })
  showCreateDialog.value = true
}

// 暂停任务
const pauseTask = async (task) => {
  try {
    await api.post(`/api-testing/scheduled-tasks/${task.id}/pause/`)
    ElMessage.success('任务已暂停')
    loadTasks()
  } catch (error) {
    console.error('暂停任务失败:', error)
    ElMessage.error('暂停任务失败')
  }
}

// 激活任务
const activateTask = async (task) => {
  try {
    await api.post(`/api-testing/scheduled-tasks/${task.id}/activate/`)
    ElMessage.success('任务已激活')
    loadTasks()
  } catch (error) {
    ElMessage.error('激活任务失败')
  }
}

// 删除任务
const deleteTask = async (task) => {
  try {
    await ElMessageBox.confirm('确定要删除这个定时任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteScheduledTask(task.id)
    ElMessage.success('删除任务成功')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除任务失败')
    }
  }
}
</script>

<style scoped>
.scheduled-tasks {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: px;
}

.filters {
  margin-bottom: 20px;
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
}

.task-list {
  flex: 1;
  overflow: hidden;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.cron-help {
  margin-top: 8px;
  font-size: 12px;
}

.unit {
  margin-left: 8px;
  color: #606266;
}
</style>