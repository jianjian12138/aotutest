<template>
  <div class="scheduled-tasks">
    <div class="header">
      <h3>UI自动化定时任务</h3>
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
            <el-option label="测试用例执行" value="TEST_CASE" />
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
              {{ scope.row.task_type === 'TEST_SUITE' ? '测试套件' : '测试用例' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="notification_type_display" label="通知类型" width="130">
          <template #default="scope">
            <el-tag v-if="scope.row.notification_type_display && scope.row.notification_type_display !== '-'"
                    :type="getNotificationTypeTagType(scope.row.notification_type_display)"
                    size="small">
              {{ scope.row.notification_type_display }}
            </el-tag>
            <span v-else>-</span>
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
        <el-table-column prop="engine" label="执行引擎" width="120">
          <template #default="scope">
            <el-tag size="small" type="info">
              {{ scope.row.engine === 'playwright' ? 'Playwright' : 'Selenium' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="browser" label="浏览器" width="100">
          <template #default="scope">
            {{ scope.row.browser || 'chrome' }}
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
                  <el-dropdown-item command="resume" v-if="scope.row.status === 'PAUSED'">激活</el-dropdown-item>
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

        <el-form-item label="关联项目" required>
          <el-select v-model="taskForm.project" placeholder="请选择项目" @change="onProjectChange">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="任务类型" required>
          <el-radio-group v-model="taskForm.task_type" @change="onTaskTypeChange">
            <el-radio value="TEST_SUITE">测试套件执行</el-radio>
            <el-radio value="TEST_CASE">测试用例执行</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 根据任务类型显示不同配置 - 移到任务类型下面 -->
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

        <el-form-item v-if="taskForm.task_type === 'TEST_CASE'" label="测试用例" required>
          <el-select
            v-model="taskForm.test_cases"
            multiple
            filterable
            placeholder="请选择测试用例"
          >
            <el-option
              v-for="testCase in testCases"
              :key="testCase.id"
              :label="testCase.name"
              :value="testCase.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="触发器类型" required>
          <el-radio-group v-model="taskForm.trigger_type">
            <el-radio value="CRON">Cron表达式</el-radio>
            <el-radio value="INTERVAL">固定间隔</el-radio>
            <el-radio value="ONCE">单次执行</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 根据触发器类型显示不同配置 -->
        <el-form-item v-if="taskForm.trigger_type === 'CRON'" label="Cron表达式" required>
          <el-input v-model="taskForm.cron_expression" placeholder="0 0 * * *" />
          <div class="cron-help">
            <el-tooltip raw-content placement="top">
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

        <el-form-item label="执行引擎" required>
          <el-radio-group v-model="taskForm.engine">
            <el-radio value="playwright">Playwright</el-radio>
            <el-radio value="selenium">Selenium</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="浏览器类型" required>
          <el-select v-model="taskForm.browser" placeholder="请选择浏览器">
            <el-option label="Chrome" value="chrome" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="Edge" value="edge" />
          </el-select>
        </el-form-item>

        <el-form-item label="运行模式">
          <el-checkbox v-model="taskForm.headless">无头模式（后台运行）</el-checkbox>
        </el-form-item>

        <el-form-item label="通知设置">
          <el-checkbox v-model="taskForm.notify_on_success">执行成功时通知</el-checkbox>
          <el-checkbox v-model="taskForm.notify_on_failure">执行失败时通知</el-checkbox>
        </el-form-item>

        <el-form-item v-if="taskForm.notify_on_success || taskForm.notify_on_failure" label="通知类型">
          <el-select v-model="taskForm.notification_type" placeholder="请选择通知类型">
            <el-option label="邮箱通知" value="email" />
            <el-option label="Webhook机器人" value="webhook" />
            <el-option label="两者都发送" value="both" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="(taskForm.notify_on_success || taskForm.notify_on_failure) && (taskForm.notification_type === 'email' || taskForm.notification_type === 'both')" label="通知邮箱">
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown } from '@element-plus/icons-vue'
import {
  getScheduledTasks,
  createScheduledTask,
  updateScheduledTask,
  deleteScheduledTask,
  runScheduledTask,
  pauseScheduledTask,
  resumeScheduledTask,
  getUiProjects,
  getTestSuites,
  getTestCases,
  getUiUsers
} from '@/api/ui_automation.js'

// 数据状态
const tasks = ref([])
const projects = ref([])
const testSuites = ref([])
const testCases = ref([])
const users = ref([])
const loading = ref(false)
const submitting = ref(false)
const showCreateDialog = ref(false)
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
  project: '',
  task_type: 'TEST_SUITE',
  trigger_type: 'CRON',
  cron_expression: '0 0 * * *',
  interval_seconds: 3600,
  execute_at: '',
  test_suite: '',
  test_cases: [],
  engine: 'playwright',
  browser: 'chrome',
  headless: false,
  notify_on_success: false,
  notify_on_failure: false,
  notification_type: '',
  notify_emails: []
})

// 生命周期
onMounted(() => {
  loadTasks()
  loadProjects()
  loadUsers()
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

// 加载项目列表
const loadProjects = async () => {
  try {
    const response = await getUiProjects()
    projects.value = response.data.results
  } catch (error) {
    console.error('加载项目列表失败:', error)
  }
}

// 加载用户列表
const loadUsers = async () => {
  try {
    const response = await getUiUsers()
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

// 项目变化时加载对应的套件和用例
const onProjectChange = async (projectId) => {
  if (!projectId) return

  try {
    // 加载测试套件
    const suitesResponse = await getTestSuites({ project: projectId })
    testSuites.value = suitesResponse.data.results

    // 加载测试用例
    const casesResponse = await getTestCases({ project: projectId })
    testCases.value = casesResponse.data.results
  } catch (error) {
    console.error('加载项目数据失败:', error)
  }
}

// 任务类型变化
const onTaskTypeChange = () => {
  taskForm.test_suite = ''
  taskForm.test_cases = []
}

// 新建按钮点击
const handleCreateClick = () => {
  editingTask.value = null
  resetTaskForm()
  showCreateDialog.value = true
}

// 重置表单
const resetTaskForm = () => {
  Object.assign(taskForm, {
    name: '',
    description: '',
    project: '',
    task_type: 'TEST_SUITE',
    trigger_type: 'CRON',
    cron_expression: '0 0 * * *',
    interval_seconds: 3600,
    execute_at: '',
    test_suite: '',
    test_cases: [],
    engine: 'playwright',
    browser: 'chrome',
    headless: false,
    notify_on_success: false,
    notify_on_failure: false,
    notification_type: '',
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
    const submitData = {
      name: taskForm.name,
      description: taskForm.description,
      project: taskForm.project,
      task_type: taskForm.task_type,
      trigger_type: taskForm.trigger_type,
      engine: taskForm.engine,
      browser: taskForm.browser,
      headless: taskForm.headless,
      notify_on_success: taskForm.notify_on_success,
      notify_on_failure: taskForm.notify_on_failure
    }

    // 添加通知相关字段
    if (taskForm.notify_on_success || taskForm.notify_on_failure) {
      if (taskForm.notification_type) {
        submitData.notification_type = taskForm.notification_type
      }
      if (taskForm.notify_emails && taskForm.notify_emails.length > 0) {
        submitData.notify_emails = taskForm.notify_emails
      }
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
    } else if (taskForm.task_type === 'TEST_CASE') {
      submitData.test_cases = taskForm.test_cases
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

// 获取通知类型标签类型
const getNotificationTypeTagType = (typeDisplay) => {
  const typeMap = {
    '邮箱通知': '',
    'Webhook机器人': 'primary',
    '两者都发送': 'warning'
  }
  return typeMap[typeDisplay] || 'info'
}

// 处理任务操作
const handleTaskAction = (command, task) => {
  switch (command) {
    case 'pause':
      pauseTask(task)
      break
    case 'resume':
      resumeTask(task)
      break
    case 'edit':
      editTask(task)
      break
    case 'delete':
      deleteTask(task)
      break
  }
}

// 编辑任务
const editTask = async (task) => {
  editingTask.value = task
  Object.assign(taskForm, {
    name: task.name,
    description: task.description,
    project: task.project,
    task_type: task.task_type,
    trigger_type: task.trigger_type,
    cron_expression: task.cron_expression,
    interval_seconds: task.interval_seconds,
    execute_at: task.execute_at,
    test_suite: task.test_suite || '',
    test_cases: task.test_cases || [],
    engine: task.engine || 'playwright',
    browser: task.browser || 'chrome',
    headless: task.headless || false,
    notify_on_success: task.notify_on_success || false,
    notify_on_failure: task.notify_on_failure || false,
    notification_type: task.notification_type || '',
    notify_emails: task.notify_emails || []
  })

  // 加载项目相关数据
  if (task.project) {
    await onProjectChange(task.project)
  }

  showCreateDialog.value = true
}

// 暂停任务
const pauseTask = async (task) => {
  try {
    await pauseScheduledTask(task.id)
    ElMessage.success('任务已暂停')
    loadTasks()
  } catch (error) {
    console.error('暂停任务失败:', error)
    ElMessage.error('暂停任务失败')
  }
}

// 恢复任务
const resumeTask = async (task) => {
  try {
    await resumeScheduledTask(task.id)
    ElMessage.success('任务已恢复')
    loadTasks()
  } catch (error) {
    ElMessage.error('恢复任务失败')
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
  margin-bottom: 20px;
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
