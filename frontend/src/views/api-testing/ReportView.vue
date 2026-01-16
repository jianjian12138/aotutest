<template>
  <div class="report-view">
    <div class="header">
      <h3>测试报告</h3>
      <div class="actions">
        <el-button type="primary" @click="refreshReports">刷新报告</el-button>
        <el-button @click="openAllureReport">查看Allure报告说明</el-button>
      </div>
    </div>
    
    <div class="content">
      <el-table :data="reports" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="test_suite_name" label="测试套件" min-width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_requests" label="总请求数" width="100" />
        <el-table-column prop="passed_requests" label="通过数" width="100">
          <template #default="scope">
            <span style="color: #67c23a">{{ scope.row.passed_requests }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="failed_requests" label="失败数" width="100">
          <template #default="scope">
            <span style="color: #f56c6c">{{ scope.row.failed_requests }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="executed_by.username" label="执行者" width="120" />
        <el-table-column prop="created_at" label="执行时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button link type="primary" @click="viewReportDetail(scope.row)">生成并查看报告</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'
import dayjs from 'dayjs'

const reports = ref([])
const loading = ref(false)

const loadReports = async () => {
  loading.value = true
  try {
    const response = await api.get('/api-testing/test-executions/')
    reports.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('加载测试报告失败')
  } finally {
    loading.value = false
  }
}

const refreshReports = async () => {
  await loadReports()
}

const generateAndOpenAllureReport = async (executionId) => {
  try {
    // 调用API生成Allure报告数据
    const response = await api.post(`/api-testing/test-executions/${executionId}/generate-allure-report/`)
    ElMessage.success('报告生成成功')
    
    // 通过当前窗口的origin构造完整的URL，确保通过Vite代理访问
    const fullUrl = `${window.location.origin}${response.data.report_url}`;
    window.open(fullUrl, '_blank')
  } catch (error) {
    ElMessage.error('生成报告失败')
  }
}

const openAllureReport = () => {
  // 提示用户需要先选择一个执行记录来生成报告
  ElMessage.info('请先在下方表格中选择一个测试执行记录，然后点击"生成并查看报告"按钮来生成并查看详细的测试报告')
}

const viewReportDetail = (report) => {
  // 生成并打开Allure报告
  generateAndOpenAllureReport(report.id)
}

const getStatusType = (status) => {
  const typeMap = {
    'PENDING': 'info',
    'RUNNING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'CANCELLED': 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'PENDING': '待执行',
    'RUNNING': '执行中',
    'COMPLETED': '已完成',
    'FAILED': '执行失败',
    'CANCELLED': '已取消'
  }
  return textMap[status] || status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.report-view {
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

.header h3 {
  margin: 0;
  color: #303133;
}

.content {
  flex: 1;
  overflow: auto;
}
</style>