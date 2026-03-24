<template>
  <div class="execution-result-container">
    <div v-if="!executionResult" class="empty-result">
      <el-empty description="暂无执行结果，请先运行测试用例" />
    </div>

    <div v-else class="result-content">
      <div class="result-header">
        <h4>执行结果</h4>
        <div class="header-actions">
          <el-tag :type="getStatusType(executionResult.status)" size="large">
            {{ getStatusText(executionResult.status) }}
          </el-tag>
          <el-button size="small" @click="handleToggleView">
            <el-icon><component :is="showSteps ? 'View' : 'Edit'" /></el-icon>
            {{ showSteps ? '查看执行结果' : '编辑步骤' }}
          </el-button>
          <el-button
            size="small"
            type="success"
            @click="handleRerun"
            :loading="isRunning"
          >
            <el-icon v-if="!isRunning"><Refresh /></el-icon>
            重新运行
          </el-button>
        </div>
      </div>

      <div class="result-info">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="开始时间">
            {{ formatTime(executionResult.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="结束时间">
            {{ formatTime(executionResult.completed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ calculateDuration(executionResult.started_at, executionResult.completed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="总步骤数">
            {{ executionResult.total_steps || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="成功步骤">
            <span style="color: #67c23a">{{ executionResult.passed_steps || 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="失败步骤">
            <span style="color: #f56c6c">{{ executionResult.failed_steps || 0 }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 执行日志 -->
      <div class="logs-container" v-if="executionResult.logs">
        <h5>执行日志</h5>
        <div class="logs-scroll">
          <div v-for="(log, index) in parsedLogs" :key="index" class="log-item">
            <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
            <span :class="['log-level', getLogLevelClass(log.level)]">
              [{{ log.level }}]
            </span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>

      <!-- 截图预览 -->
      <div class="screenshots-container" v-if="executionResult.screenshots && executionResult.screenshots.length > 0">
        <h5>执行截图</h5>
        <div class="screenshots-grid">
          <el-image
            v-for="(screenshot, index) in executionResult.screenshots"
            :key="index"
            :src="screenshot.url"
            :preview-src-list="[screenshot.url]"
            fit="cover"
            class="screenshot-item"
          >
            <template #placeholder>
              <div class="image-loading">加载中...</div>
            </template>
          </el-image>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Refresh, View, Edit } from '@element-plus/icons-vue'
import { formatTime } from '@/utils/helpers'

// Props
const props = defineProps({
  executionResult: {
    type: Object,
    default: null
  },
  showSteps: {
    type: Boolean,
    default: true
  },
  isRunning: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['toggle-view', 'rerun'])

// Computed
const parsedLogs = computed(() => {
  if (!props.executionResult?.logs) return []
  try {
    return typeof props.executionResult.logs === 'string'
      ? JSON.parse(props.executionResult.logs)
      : props.executionResult.logs
  } catch (e) {
    console.error('解析执行日志失败:', e)
    return []
  }
})

// Methods
const getStatusType = (status) => {
  const statusMap = {
    'success': 'success',
    'passed': 'success',
    'failed': 'danger',
    'running': 'warning',
    'pending': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'success': '通过',
    'passed': '通过',
    'failed': '失败',
    'running': '执行中',
    'pending': '等待中'
  }
  return textMap[status] || status
}

const calculateDuration = (start, end) => {
  if (!start || !end) return '0s'
  const duration = new Date(end) - new Date(start)
  if (isNaN(duration)) return '0s'
  
  const seconds = Math.floor(duration / 1000)
  if (seconds < 60) return `${seconds}s`
  
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

const formatLogTime = (timestamp) => {
  if (!timestamp) return ''
  return formatTime(timestamp)
}

const getLogLevelClass = (level) => {
  const levelMap = {
    'INFO': 'level-info',
    'DEBUG': 'level-debug',
    'WARNING': 'level-warning',
    'ERROR': 'level-error',
    'CRITICAL': 'level-critical'
  }
  return levelMap[level] || 'level-info'
}

const handleToggleView = () => {
  emit('toggle-view')
}

const handleRerun = () => {
  emit('rerun')
}
</script>

<style scoped>
.execution-result-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.empty-result {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.result-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
  background: #fafafa;
}

.result-header h4 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.result-info {
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
}

.logs-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 15px;
}

.logs-container h5 {
  margin: 0 0 10px 0;
  font-size: 13px;
  color: #666;
}

.logs-scroll {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 10px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.log-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
  line-height: 1.5;
}

.log-time {
  color: #999;
  white-space: nowrap;
}

.log-level {
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
}

.level-info {
  background: #e6f7ff;
  color: #1890ff;
}

.level-debug {
  background: #f0f5ff;
  color: #722ed1;
}

.level-warning {
  background: #fffbe6;
  color: #faad14;
}

.level-error {
  background: #fff1f0;
  color: #f5222d;
}

.level-critical {
  background: #fff2f0;
  color: #d4380d;
}

.log-message {
  flex: 1;
  color: #333;
  word-break: break-all;
}

.screenshots-container {
  padding: 15px;
  border-top: 1px solid #e6e6e6;
}

.screenshots-container h5 {
  margin: 0 0 10px 0;
  font-size: 13px;
  color: #666;
}

.screenshots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.screenshot-item {
  width: 100%;
  height: 150px;
  border-radius: 6px;
  cursor: pointer;
}

.image-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}
</style>
