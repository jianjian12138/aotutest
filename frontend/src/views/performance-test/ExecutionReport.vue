<template>
  <BasePage :title="'测试报告 - ' + (execution.id || '')">
    <template #actions>
      <div class="header-right">
        <el-tag :type="getStatusTagType(execution.status)" style="margin-right: 10px">
          {{ getStatusText(execution.status) }}
        </el-tag>
        <el-button type="primary" @click="downloadReport" :disabled="!execution.report_html">
          <el-icon><Download /></el-icon> 下载报告
        </el-button>
      </div>
    </template>

    <div class="report-content" v-loading="loading">
      <div v-if="execution.report_html" class="iframe-container">
        <iframe :srcdoc="execution.report_html" frameborder="0" width="100%" height="100%"></iframe>
      </div>
      <div v-else-if="!loading" class="empty-state">
        <el-empty description="暂无报告数据" />
      </div>
    </div>
  </BasePage>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download } from '@element-plus/icons-vue'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const executionId = route.params.id
const execution = ref({})
const loading = ref(false)

const fetchExecution = async () => {
  loading.value = true
  try {
    const response = await api.get(`/performance-testing/executions/${executionId}/`)
    execution.value = response.data
  } catch (error) {
    console.error('获取执行详情失败:', error)
    ElMessage.error('获取执行详情失败')
  } finally {
    loading.value = false
  }
}

const getStatusTagType = (status) => {
  const typeMap = {
    RUNNING: 'primary',
    COMPLETED: 'success',
    FAILED: 'danger',
    STOPPED: 'warning'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    RUNNING: '运行中',
    COMPLETED: '已完成',
    FAILED: '已失败',
    STOPPED: '已停止'
  }
  return textMap[status] || status
}

const downloadReport = () => {
  if (!execution.value.report_html) return
  
  const blob = new Blob([execution.value.report_html], { type: 'text/html' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `performance_report_${executionId}.html`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

onMounted(() => {
  fetchExecution()
})
</script>

<style scoped>
.execution-report {
  height: calc(100vh - 84px); /* 减去顶部导航栏高度 */
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}



.header-left {
  display: flex;
  align-items: center;
}



.report-content {
  flex: 1;
  overflow: hidden;
  padding: 20px;
}

.iframe-container {
  width: 100%;
  height: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 8px;
}
</style>
