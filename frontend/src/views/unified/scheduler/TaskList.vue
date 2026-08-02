<template>
  <BasePage title="定时任务管理">
    <template #actions>
      <PremiumButton type="primary" glow @click="handleCreateTask">
        <el-icon><Plus /></el-icon>
        新建任务
      </PremiumButton>
    </template>

    <div class="unified-task-list-wrapper">
      <PremiumCard class="filter-card" padding="16px 24px">
        <div class="filter-section">
          <el-input
            v-model="searchText"
            placeholder="搜索任务名称"
            clearable
            style="width: 250px"
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-select
            v-model="taskTypeFilter"
            placeholder="任务类型"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="API测试" value="API" />
            <el-option label="UI自动化" value="UI" />
            <el-option label="性能测试" value="PERFORMANCE" />
            <el-option label="通用任务" value="GENERAL" />
          </el-select>

          <el-select
            v-model="statusFilter"
            placeholder="状态"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="激活" value="ACTIVE" />
            <el-option label="暂停" value="PAUSED" />
            <el-option label="已完成" value="COMPLETED" />
          </el-select>

          <el-select
            v-model="projectFilter"
            placeholder="项目"
            clearable
            filterable
            style="width: 200px"
            @change="handleFilter"
          >
            <el-option
              v-for="project in projectList"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </div>
      </PremiumCard>

      <PremiumCard class="table-card" padding="0">
        <el-table class="premium-table" :data="tasks" v-loading="loading" stripe style="width: 100%">
          <el-table-column prop="name" label="任务名称" min-width="200">
        <template #default="{ row }">
          <el-link @click="viewTask(row.id)" type="primary">
            {{ row.name }}
          </el-link>
        </template>
      </el-table-column>

      <el-table-column prop="task_type" label="任务类型" width="120">
        <template #default="{ row }">
          <el-tag :type="getTaskTypeTag(row.task_type)" size="small">
            {{ getTaskTypeText(row.task_type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="project_name" label="所属项目" width="150" />

      <el-table-column prop="trigger_type" label="触发类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ getTriggerTypeText(row.trigger_type) }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="cron_expression" label="Cron表达式" width="150" show-overflow-tooltip />

      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="next_run_time" label="下次运行" width="180">
        <template #default="{ row }">
          {{ formatDate(row.next_run_time) }}
        </template>
      </el-table-column>

      <el-table-column prop="total_runs" label="运行次数" width="80" align="center" />

      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="viewTask(row.id)">查看</el-button>
          <el-button size="small" @click="editTask(row)">编辑</el-button>
          <el-button
            size="small"
            type="success"
            @click="executeTask(row)"
            :loading="row.executing"
          >
            运行
          </el-button>
          <el-dropdown @command="(cmd) => handleAction(cmd, row)">
            <el-button size="small">
              更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  command="pause"
                  v-if="row.status === 'ACTIVE'"
                >
                  暂停
                </el-dropdown-item>
                <el-dropdown-item
                  command="resume"
                  v-if="row.status === 'PAUSED'"
                >
                  恢复
                </el-dropdown-item>
                <el-dropdown-item
                  command="delete"
                  divided
                >
                  删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

        <div class="pagination-footer">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next, jumper"
            @current-change="handlePageChange"
          />
        </div>
      </PremiumCard>
    </div>

    <!-- 创建/编辑任务对话框 -->
    <el-dialog
      :title="isEdit ? '编辑任务' : '新建任务'"
      v-model="showDialog"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form :model="taskForm" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="taskForm.name" placeholder="请输入任务名称" />
        </el-form-item>

        <el-form-item label="所属项目" prop="project">
          <el-select v-model="taskForm.project" placeholder="请选择项目" style="width: 100%" filterable>
            <el-option
              v-for="project in projectList"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="taskForm.task_type" placeholder="请选择任务类型" style="width: 100%">
            <el-option label="API测试" value="API" />
            <el-option label="UI自动化" value="UI" />
            <el-option label="性能测试" value="PERFORMANCE" />
            <el-option label="通用任务" value="GENERAL" />
          </el-select>
        </el-form-item>

        <el-form-item label="触发类型" prop="trigger_type">
          <el-select v-model="taskForm.trigger_type" placeholder="请选择触发类型" style="width: 100%">
            <el-option label="Cron表达式" value="CRON" />
            <el-option label="固定间隔" value="INTERVAL" />
            <el-option label="单次执行" value="ONCE" />
          </el-select>
        </el-form-item>

        <el-form-item label="Cron表达式" prop="cron_expression" v-if="taskForm.trigger_type === 'CRON'">
          <el-input v-model="taskForm.cron_expression" placeholder="例如: 0 0 * * * (每天0点执行)" />
          <div class="form-tip">
            <span>格式: 分 时 日 月 周</span>
            <el-button size="small" link @click="showCronHelp">查看帮助</el-button>
          </div>
        </el-form-item>

        <el-form-item label="间隔(秒)" prop="interval_seconds" v-if="taskForm.trigger_type === 'INTERVAL'">
          <el-input-number v-model="taskForm.interval_seconds" :min="60" :max="31536000" />
        </el-form-item>

        <el-form-item label="执行时间" prop="execute_at" v-if="taskForm.trigger_type === 'ONCE'">
          <el-date-picker
            v-model="taskForm.execute_at"
            type="datetime"
            placeholder="选择执行时间"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="taskForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入任务描述"
          />
        </el-form-item>

        <el-form-item label="通知配置">
          <el-checkbox v-model="taskForm.notify_on_success">成功时通知</el-checkbox>
          <el-checkbox v-model="taskForm.notify_on_failure">失败时通知</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDialog = false">取消</el-button>
          <PremiumButton type="primary" @click="handleSave" :loading="saving" glow>保存</PremiumButton>
        </span>
      </template>
    </el-dialog>

    <!-- Cron表达式帮助对话框 -->
    <el-dialog
      title="Cron表达式帮助"
      v-model="showCronDialog"
      width="600px"
    >
      <div class="cron-help">
        <h4>Cron表达式格式</h4>
        <p>格式: 分 时 日 月 周</p>
        <p>例如: 0 0 * * * 表示每天0点0分执行</p>

        <h4>常用示例</h4>
        <el-table :data="cronExamples" border size="small">
          <el-table-column prop="expression" label="表达式" width="150" />
          <el-table-column prop="description" label="说明" />
        </el-table>
      </div>
    </el-dialog>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, ArrowDown } from '@element-plus/icons-vue'
import {
  getTaskList,
  createTask,
  updateTask,
  deleteTask as deleteTaskApi,
  executeTask as executeTaskApi,
  pauseTask,
  resumeTask
} from '@/api/unified/scheduler'
import { getAllProjects } from '@/api/unified/project'

const router = useRouter()

// 数据
const tasks = ref([])
const projectList = ref([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const showCronDialog = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const searchText = ref('')
const taskTypeFilter = ref('')
const statusFilter = ref('')
const projectFilter = ref('')

// 表单
const taskForm = reactive({
  name: '',
  project: null,
  task_type: 'GENERAL',
  trigger_type: 'CRON',
  cron_expression: '',
  interval_seconds: 3600,
  execute_at: null,
  description: '',
  notify_on_success: false,
  notify_on_failure: true
})

const formRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  project: [{ required: true, message: '请选择项目', trigger: 'change' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  trigger_type: [{ required: true, message: '请选择触发类型', trigger: 'change' }],
  cron_expression: [
    { required: true, message: '请输入Cron表达式', trigger: 'blur' }
  ],
  interval_seconds: [
    { required: true, message: '请输入间隔时间', trigger: 'blur' }
  ],
  execute_at: [
    { required: true, message: '请选择执行时间', trigger: 'change' }
  ]
}

const cronExamples = [
  { expression: '0 0 * * *', description: '每天0点0分执行' },
  { expression: '0 */6 * * *', description: '每6小时执行一次' },
  { expression: '0 0 * * 1', description: '每周一0点执行' },
  { expression: '0 0 1 * *', description: '每月1号0点执行' },
  { expression: '0 9-18 * * 1-5', description: '工作日9点到18点每小时执行' },
  { expression: '*/30 * * * *', description: '每30分钟执行一次' }
]

let editingId = null

// 方法
const fetchTasks = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      task_type: taskTypeFilter.value,
      status: statusFilter.value,
      project: projectFilter.value
    }
    const cleanParams = Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== null && v !== ''));
    const response = await getTaskList(cleanParams)
    tasks.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取任务列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const response = await getAllProjects()
    projectList.value = response.data.results || response.data
  } catch (error) {
    console.error('获取项目列表失败', error)
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchTasks()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchTasks()
}

const handlePageChange = () => {
  fetchTasks()
}

const handleCreateTask = () => {
  isEdit.value = false
  editingId = null
  Object.assign(taskForm, {
    name: '',
    project: null,
    task_type: 'GENERAL',
    trigger_type: 'CRON',
    cron_expression: '',
    interval_seconds: 3600,
    execute_at: null,
    description: '',
    notify_on_success: false,
    notify_on_failure: true
  })
  showDialog.value = true
}

const editTask = (row) => {
  isEdit.value = true
  editingId = row.id
  Object.assign(taskForm, {
    name: row.name,
    project: row.project,
    task_type: row.task_type,
    trigger_type: row.trigger_type,
    cron_expression: row.cron_expression || '',
    interval_seconds: row.interval_seconds || 3600,
    execute_at: row.execute_at || null,
    description: row.description || '',
    notify_on_success: row.notify_on_success || false,
    notify_on_failure: row.notify_on_failure || true
  })
  showDialog.value = true
}

const handleSave = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      const data = { ...taskForm }

      if (isEdit.value) {
        await updateTask(editingId, data)
        ElMessage.success('任务更新成功')
      } else {
        await createTask(data)
        ElMessage.success('任务创建成功')
      }

      showDialog.value = false
      fetchTasks()
    } catch (error) {
      ElMessage.error(isEdit.value ? '任务更新失败' : '任务创建失败')
      console.error(error)
    } finally {
      saving.value = false
    }
  })
}

const executeTask = async (row) => {
  row.executing = true
  try {
    await executeTaskApi(row.id)
    ElMessage.success('任务已开始执行')
  } catch (error) {
    ElMessage.error('任务执行失败')
    console.error(error)
  } finally {
    row.executing = false
  }
}

const handleAction = async (command, row) => {
  switch (command) {
    case 'pause':
      try {
        await pauseTask(row.id)
        ElMessage.success('任务已暂停')
        fetchTasks()
      } catch (error) {
        ElMessage.error('任务暂停失败')
        console.error(error)
      }
      break
    case 'resume':
      try {
        await resumeTask(row.id)
        ElMessage.success('任务已恢复')
        fetchTasks()
      } catch (error) {
        ElMessage.error('任务恢复失败')
        console.error(error)
      }
      break
    case 'delete':
      try {
        await ElMessageBox.confirm(
          `确定要删除任务 "${row.name}" 吗？`,
          '删除确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await deleteTaskApi(row.id)
        ElMessage.success('任务删除成功')
        fetchTasks()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('任务删除失败')
          console.error(error)
        }
      }
      break
  }
}

const viewTask = (id) => {
  router.push(`/unified/scheduler/${id}`)
}

const showCronHelp = () => {
  showCronDialog.value = true
}

// 辅助方法
const getTaskTypeTag = (type) => {
  const tags = {
    API: 'primary',
    UI: 'success',
    PERFORMANCE: 'warning',
    GENERAL: 'info'
  }
  return tags[type] || 'info'
}

const getTaskTypeText = (type) => {
  const texts = {
    API: 'API测试',
    UI: 'UI自动化',
    PERFORMANCE: '性能测试',
    GENERAL: '通用任务'
  }
  return texts[type] || type
}

const getTriggerTypeText = (type) => {
  const texts = {
    CRON: 'Cron',
    INTERVAL: '间隔',
    ONCE: '单次'
  }
  return texts[type] || type
}

const getStatusType = (status) => {
  const types = {
    ACTIVE: 'success',
    PAUSED: 'warning',
    COMPLETED: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    ACTIVE: '激活',
    PAUSED: '暂停',
    COMPLETED: '已完成'
  }
  return texts[status] || status
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  fetchTasks()
  fetchProjects()
})
</script>

<style scoped>
.unified-task-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-section {
  display: flex;
  gap: 12px;
}

.form-tip {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.cron-help h4 {
  margin: 16px 0 8px 0;
}

.cron-help p {
  margin: 4px 0;
  color: #606266;
}
</style>
