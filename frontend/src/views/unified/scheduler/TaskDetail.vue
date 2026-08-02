<template>
  <div class="task-detail" v-loading="loading">
    <div class="page-header">
      <el-button @click="goBack" :icon="ArrowLeft">返回</el-button>
      <div class="header-content">
        <h2>{{ task.name }}</h2>
        <el-tag :type="getTaskTypeTag(task.task_type)" size="large">
          {{ getTaskTypeText(task.task_type) }}
        </el-tag>
        <el-tag :type="getStatusType(task.status)">
          {{ getStatusText(task.status) }}
        </el-tag>
      </div>
      <div class="header-actions">
        <el-button type="success" @click="executeTask" :loading="executing">
          <el-icon><VideoPlay /></el-icon>
          立即执行
        </el-button>
        <el-button
          v-if="task.status === 'ACTIVE'"
          type="warning"
          @click="handlePauseTask"
        >
          <el-icon><VideoPause /></el-icon>
          暂停
        </el-button>
        <el-button
          v-if="task.status === 'PAUSED'"
          type="success"
          @click="handleResumeTask"
        >
          <el-icon><VideoPlay /></el-icon>
          恢复
        </el-button>
        <el-button type="primary" @click="editTask">编辑</el-button>
        <el-button type="danger" @click="handleDeleteTask">删除</el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="info-card">
          <template #header>
            <span>任务信息</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="任务名称">{{ task.name }}</el-descriptions-item>
            <el-descriptions-item label="任务类型">
              {{ getTaskTypeText(task.task_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="所属项目">{{ task.project_name }}</el-descriptions-item>
            <el-descriptions-item label="触发类型">
              {{ getTriggerTypeText(task.trigger_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="Cron表达式" :span="2" v-if="task.trigger_type === 'CRON'">
              {{ task.cron_expression }}
            </el-descriptions-item>
            <el-descriptions-item label="间隔时间" :span="2" v-if="task.trigger_type === 'INTERVAL'">
              {{ task.interval_seconds }} 秒
            </el-descriptions-item>
            <el-descriptions-item label="执行时间" :span="2" v-if="task.trigger_type === 'ONCE'">
              {{ formatDate(task.execute_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              {{ getStatusText(task.status) }}
            </el-descriptions-item>
            <el-descriptions-item label="下次运行">
              {{ formatDate(task.next_run_time) }}
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">
              {{ task.description || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(task.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatDate(task.updated_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="logs-card">
          <template #header>
            <div class="card-header">
              <span>执行日志</span>
              <el-button size="small" @click="refreshLogs">刷新</el-button>
            </div>
          </template>
          <el-table :data="executionLogs" stripe>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getLogStatusType(row.status)" size="small">
                  {{ getLogStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="开始时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.start_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="end_time" label="结束时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.end_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时(秒)" width="100" align="center">
              <template #default="{ row }">
                {{ row.duration?.toFixed(2) || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" link @click="viewLogDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination">
            <el-pagination
              v-model:current-page="logPage"
              :page-size="logPageSize"
              :total="logTotal"
              layout="total, prev, pager, next"
              @current-change="handleLogPageChange"
            />
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="statistics-card">
          <template #header>
            <span>任务统计</span>
          </template>
          <el-statistic title="总运行次数" :value="task.total_runs || 0" />
          <el-divider />
          <el-statistic title="成功次数" :value="task.successful_runs || 0" />
          <el-divider />
          <el-statistic title="失败次数" :value="task.failed_runs || 0" />
          <el-divider />
          <el-statistic title="成功率" :value="successRate" suffix="%" />
        </el-card>

        <el-card class="notification-card">
          <template #header>
            <span>通知配置</span>
          </template>
          <el-form label-width="100px">
            <el-form-item label="成功通知">
              <el-switch v-model="task.notify_on_success" disabled />
              <span class="status-text">
                {{ task.notify_on_success ? '已启用' : '已禁用' }}
              </span>
            </el-form-item>
            <el-form-item label="失败通知">
              <el-switch v-model="task.notify_on_failure" disabled />
              <span class="status-text">
                {{ task.notify_on_failure ? '已启用' : '已禁用' }}
              </span>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 日志详情对话框 -->
    <el-dialog
      title="执行日志详情"
      v-model="showLogDetail"
      width="800px"
    >
      <el-descriptions :column="1" border>
        <el-descriptions-item label="状态">
          <el-tag :type="getLogStatusType(currentLog.status)">
            {{ getLogStatusText(currentLog.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">
          {{ formatDate(currentLog.start_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="结束时间">
          {{ formatDate(currentLog.end_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="耗时">
          {{ currentLog.duration?.toFixed(2) }} 秒
        </el-descriptions-item>
        <el-descriptions-item label="错误信息">
          {{ currentLog.error_message || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="执行结果">
          <pre v-if="currentLog.result">{{ JSON.stringify(currentLog.result, null, 2) }}</pre>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, VideoPlay, VideoPause } from '@element-plus/icons-vue'
import {
  getTaskDetail,
  deleteTask as deleteTaskApi,
  executeTask as executeTaskApi,
  pauseTask,
  resumeTask,
  getTaskExecutionLogs
} from '@/api/unified/scheduler'

const router = useRouter()
const route = useRoute()

const taskId = route.params.id
const loading = ref(false)
const executing = ref(false)
const task = ref({})
const executionLogs = ref([])
const showLogDetail = ref(false)
const currentLog = ref({})

// 分页
const logPage = ref(1)
const logPageSize = ref(10)
const logTotal = ref(0)

// 计算属性
const successRate = computed(() => {
  if (!task.value.total_runs || task.value.total_runs === 0) return 0
  return ((task.value.successful_runs / task.value.total_runs) * 100).toFixed(2)
})

// 方法
const fetchTaskDetail = async () => {
  loading.value = true
  try {
    const response = await getTaskDetail(taskId)
    task.value = response.data
  } catch (error) {
    ElMessage.error('获取任务详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchExecutionLogs = async () => {
  try {
    const params = {
      page: logPage.value,
      page_size: logPageSize.value
    }
    const response = await getTaskExecutionLogs(taskId, params)
    executionLogs.value = response.data.results || response.data
    logTotal.value = response.data.count || response.data.length
  } catch (error) {
    console.error('获取执行日志失败', error)
  }
}

const goBack = () => {
  router.push('/unified/scheduler')
}

const editTask = () => {
  ElMessage.info('编辑功能开发中')
}

const executeTask = async () => {
  executing.value = true
  try {
    await executeTaskApi(taskId)
    ElMessage.success('任务已开始执行')
    setTimeout(() => {
      fetchTaskDetail()
      fetchExecutionLogs()
    }, 1000)
  } catch (error) {
    ElMessage.error('任务执行失败')
    console.error(error)
  } finally {
    executing.value = false
  }
}

const handlePauseTask = async () => {
  try {
    await pauseTask(taskId)
    ElMessage.success('任务已暂停')
    fetchTaskDetail()
  } catch (error) {
    ElMessage.error('任务暂停失败')
    console.error(error)
  }
}

const handleResumeTask = async () => {
  try {
    await resumeTask(taskId)
    ElMessage.success('任务已恢复')
    fetchTaskDetail()
  } catch (error) {
    ElMessage.error('任务恢复失败')
    console.error(error)
  }
}

const deleteTask = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务 "${task.value.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteTaskApi(taskId)
    ElMessage.success('任务删除成功')
    router.push('/unified/scheduler')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('任务删除失败')
      console.error(error)
    }
  }
}

const refreshLogs = () => {
  logPage.value = 1
  fetchExecutionLogs()
}

const handleLogPageChange = () => {
  fetchExecutionLogs()
}

const viewLogDetail = (log) => {
  currentLog.value = log
  showLogDetail.value = true
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

const getLogStatusType = (status) => {
  const types = {
    RUNNING: 'primary',
    SUCCESS: 'success',
    FAILED: 'danger',
    CANCELLED: 'info'
  }
  return types[status] || 'info'
}

const getLogStatusText = (status) => {
  const texts = {
    RUNNING: '运行中',
    SUCCESS: '成功',
    FAILED: '失败',
    CANCELLED: '已取消'
  }
  return texts[status] || status
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  fetchTaskDetail()
  fetchExecutionLogs()
})
</script>

<style scoped>
.task-detail {
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-content h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.info-card,
.logs-card,
.statistics-card,
.notification-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.status-text {
  margin-left: 12px;
  color: #909399;
  font-size: 14px;
}

pre {
  margin: 0;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow-x: auto;
}
</style>
