<template>
  <el-dialog
    v-model="visible"
    title="AI 执行报告"
    width="900px"
    destroy-on-close
    :close-on-click-modal="false"
    class="ai-report-dialog"
  >
    <div v-loading="loading" class="report-container">
      <div v-if="report" class="report-content">
        <!-- 基本信息 -->
        <div class="report-section">
          <h3>基本信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用例名称">{{ report.case_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="执行状态">
              <el-tag :type="getStatusTag(report.status)">{{ getStatusText(report.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ formatDate(report.start_time) }}</el-descriptions-item>
            <el-descriptions-item label="耗时">{{ report.duration ? report.duration.toFixed(2) + ' 秒' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="执行人">{{ report.executed_by?.username || '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 任务描述 -->
        <div class="report-section" v-if="report.task_description">
          <h3>任务描述</h3>
          <div class="text-block">{{ report.task_description }}</div>
        </div>

        <!-- 执行步骤 -->
        <div class="report-section" v-if="report.steps && report.steps.length > 0">
          <h3>执行步骤</h3>
          <el-timeline>
            <el-timeline-item
              v-for="(step, index) in report.steps"
              :key="index"
              :type="getStepStatusType(step.status)"
              :color="getStepStatusColor(step.status)"
              :timestamp="formatDate(step.timestamp)"
            >
              <div class="step-card">
                <div class="step-header">
                  <span class="step-action">{{ step.action }}</span>
                  <el-tag size="small" :type="getStepStatusType(step.status)" class="step-status">
                    {{ step.status }}
                  </el-tag>
                </div>
                <div v-if="step.description" class="step-desc">{{ step.description }}</div>
                <div v-if="step.screenshot" class="step-screenshot">
                  <el-image 
                    :src="step.screenshot" 
                    :preview-src-list="[step.screenshot]" 
                    fit="contain"
                    hide-on-click-modal
                  />
                </div>
                <div v-if="step.error" class="step-error">{{ step.error }}</div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>

        <!-- 执行日志 -->
        <div class="report-section" v-if="report.logs">
          <h3>执行日志</h3>
          <div class="log-block">
            <pre>{{ report.logs }}</pre>
          </div>
        </div>
        
        <!-- 错误信息 -->
        <div class="report-section" v-if="report.error_message">
          <h3>错误信息</h3>
          <el-alert :title="report.error_message" type="error" :closable="false" show-icon />
        </div>
      </div>
      
      <div v-else-if="!loading" class="empty-state">
        <el-empty description="暂无报告数据" />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="handleExport" :loading="exportLoading">导出 PDF</el-button>
        <el-button @click="visible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { getAIExecutionReport, exportAIExecutionReportPDF } from '@/api/ui_automation'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  recordId: {
    type: [String, Number],
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const exportLoading = ref(false)
const report = ref(null)

watch(() => props.modelValue, (val) => {
  if (val && props.recordId) {
    fetchReport()
  }
})

const fetchReport = async () => {
  loading.value = true
  report.value = null
  try {
    const response = await getAIExecutionReport(props.recordId)
    report.value = response.data
  } catch (error) {
    console.error('获取报告失败:', error)
    ElMessage.error('获取报告失败')
  } finally {
    loading.value = false
  }
}

const handleExport = async () => {
  if (!props.recordId) return
  
  exportLoading.value = true
  try {
    const response = await exportAIExecutionReportPDF(props.recordId)
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `AI_Report_${props.recordId}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出报告失败:', error)
    ElMessage.error('导出报告失败')
  } finally {
    exportLoading.value = false
  }
}

const getStatusTag = (status) => {
  const map = {
    'passed': 'success',
    'failed': 'danger',
    'running': 'warning',
    'pending': 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'passed': '成功',
    'failed': '失败',
    'running': '执行中',
    'pending': '等待中'
  }
  return map[status] || status
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

const getStepStatusType = (status) => {
  if (status === 'passed') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
}

const getStepStatusColor = (status) => {
  if (status === 'passed') return '#67C23A'
  if (status === 'failed') return '#F56C6C'
  return '#909399'
}
</script>

<style scoped>
.report-container {
  min-height: 300px;
  padding: 10px;
}

.report-section {
  margin-bottom: 24px;
}

.report-section h3 {
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 4px solid #409EFF;
  font-size: 16px;
  font-weight: 600;
}

.text-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.log-block {
  background: #1e1e1e;
  color: #fff;
  padding: 12px;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}

.log-block pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: monospace;
}

.step-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.step-action {
  font-weight: bold;
  font-size: 14px;
}

.step-desc {
  color: #606266;
  font-size: 13px;
  margin-bottom: 8px;
}

.step-screenshot {
  margin-top: 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.step-screenshot .el-image {
  display: block;
  max-height: 200px;
}

.step-error {
  margin-top: 8px;
  color: #F56C6C;
  font-size: 12px;
  background: #fef0f0;
  padding: 8px;
  border-radius: 4px;
}
</style>
