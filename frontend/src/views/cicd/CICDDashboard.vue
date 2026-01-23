<template>
  <div class="cicd-dashboard">
    <div class="page-header">
      <h1>🔄 CI/CD管理</h1>
      <p>CI/CD流程配置与执行管理</p>
    </div>

    <div class="main-content">
      <!-- 统计卡片 -->
      <div class="stats-section">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon servers-icon">
                  <el-icon><Monitor /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-number">{{ serverCount }}</div>
                  <div class="stat-label">CI/CD服务器</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon jobs-icon">
                  <el-icon><DocumentChecked /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-number">{{ jobCount }}</div>
                  <div class="stat-label">CI/CD任务</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon executions-icon">
                  <el-icon><VideoPlay /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-number">{{ executionCount }}</div>
                  <div class="stat-label">执行记录</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon trend-icon">
                  <el-icon><DataAnalysis /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-number">{{ successRate }}%</div>
                  <div class="stat-label">成功率</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 最近执行记录 -->
      <div class="recent-executions-section">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>📋 最近执行记录</span>
              <el-button type="primary" @click="navigateToExecutions">
                <el-icon><View /></el-icon>
                查看全部
              </el-button>
            </div>
          </template>
          <div v-if="recentExecutions.length === 0" class="empty-state">
            <el-empty description="暂无执行记录" />
          </div>
          <el-table v-else :data="recentExecutions" stripe style="width: 100%">
            <el-table-column prop="job.name" label="任务名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="build_number" label="构建编号" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getStatusTagType(scope.row.status)">
                  {{ getStatusText(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="开始时间" width="180" :formatter="formatDateTime" />
            <el-table-column prop="duration" label="执行时长" width="120">
              <template #default="scope">
                <span>{{ formatDuration(scope.row.duration) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="triggered_by.username" label="触发者" width="120" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="scope">
                <el-button size="small" type="primary" @click="viewExecutionLog(scope.row.id)">
                  <el-icon><Document /></el-icon>
                  查看日志
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <!-- 任务列表 -->
      <div class="jobs-section">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>📋 CI/CD任务列表</span>
              <el-button type="primary" @click="navigateToJobs">
                <el-icon><View /></el-icon>
                管理任务
              </el-button>
            </div>
          </template>
          <div v-if="jobs.length === 0" class="empty-state">
            <el-empty description="暂无任务" />
          </div>
          <el-table v-else :data="jobs" stripe style="width: 100%">
            <el-table-column prop="name" label="任务名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="server.name" label="服务器" width="150" />
            <el-table-column prop="server.server_type" label="类型" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.server.server_type === 'JENKINS' ? 'primary' : 'success'">
                  {{ scope.row.server.get_server_type_display || scope.row.server.server_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status === 'ACTIVE' ? 'success' : 'warning'">
                  {{ scope.row.get_status_display || scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="scope">
                <el-button size="small" type="success" @click="triggerJob(scope.row.id)" :disabled="scope.row.status !== 'ACTIVE'">
                  <el-icon><VideoPlay /></el-icon>
                  触发执行
                </el-button>
                <el-button size="small" type="primary" @click="viewJobExecutions(scope.row.id)">
                  <el-icon><Clock /></el-icon>
                  执行记录
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor, DocumentChecked, VideoPlay, DataAnalysis, Document, Clock } from '@element-plus/icons-vue'
import api from '@/utils/api'

const router = useRouter()

// 状态管理
const serverCount = ref(0)
const jobCount = ref(0)
const executionCount = ref(0)
const successRate = ref(0)
const jobs = ref([])
const recentExecutions = ref([])

// 生命周期钩子
onMounted(() => {
  loadStats()
  loadJobs()
  loadRecentExecutions()
})

// 加载统计数据
const loadStats = async () => {
  try {
    const serversResponse = await api.get('/cicd/servers/')
    serverCount.value = serversResponse.data.length || 0

    const jobsResponse = await api.get('/cicd/jobs/')
    jobCount.value = jobsResponse.data.length || 0

    const executionsResponse = await api.get('/cicd/executions/')
    executionCount.value = executionsResponse.data.length || 0

    // 计算成功率
    if (executionCount.value > 0) {
      const successExecutions = executionsResponse.data.filter(exec => exec.status === 'SUCCESS')
      successRate.value = Math.round((successExecutions.length / executionCount.value) * 100)
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  }
}

// 加载任务列表
const loadJobs = async () => {
  try {
    const response = await api.get('/cicd/jobs/')
    // 确保response.data是一个数组，如果是分页结果，可能在results字段中
    const data = Array.isArray(response.data) ? response.data : (response.data.results || [])
    jobs.value = data.slice(0, 5) // 只显示前5个任务
  } catch (error) {
    console.error('加载任务列表失败:', error)
    ElMessage.error('加载任务列表失败')
  }
}

// 加载最近执行记录
const loadRecentExecutions = async () => {
  try {
    const response = await api.get('/cicd/executions/?ordering=-created_at')
    // 确保response.data是一个数组，如果是分页结果，可能在results字段中
    const data = Array.isArray(response.data) ? response.data : (response.data.results || [])
    recentExecutions.value = data.slice(0, 5) // 只显示前5条记录
  } catch (error) {
    console.error('加载最近执行记录失败:', error)
    ElMessage.error('加载最近执行记录失败')
  }
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    'SUCCESS': 'success',
    'FAILURE': 'danger',
    'RUNNING': 'warning',
    'PENDING': 'info',
    'CANCELLED': 'info'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    'SUCCESS': '成功',
    'FAILURE': '失败',
    'RUNNING': '执行中',
    'PENDING': '待执行',
    'CANCELLED': '已取消'
  }
  return textMap[status] || status
}

// 格式化日期时间
const formatDateTime = (row, column, cellValue) => {
  if (!cellValue) return '无'
  const date = new Date(cellValue)
  return date.toLocaleString()
}

// 格式化执行时长
const formatDuration = (duration) => {
  if (!duration || duration === 0) return '0秒'
  if (duration < 60) return `${duration.toFixed(1)}秒`
  return `${(duration / 60).toFixed(1)}分钟`
}

// 查看执行日志
const viewExecutionLog = (executionId) => {
  router.push(`/cicd/executions/${executionId}/logs`)
}

// 触发任务执行
const triggerJob = async (jobId) => {
  try {
    await api.post(`/cicd/jobs/${jobId}/trigger/`)
    ElMessage.success('任务触发成功')
    loadRecentExecutions() // 刷新最近执行记录
  } catch (error) {
    console.error('触发任务失败:', error)
    ElMessage.error('触发任务失败: ' + (error.response?.data?.error || error.message))
  }
}

// 查看任务执行记录
const viewJobExecutions = (jobId) => {
  router.push(`/cicd/jobs/${jobId}/executions`)
}

// 导航到任务管理页面
const navigateToJobs = () => {
  router.push('/cicd/jobs')
}

// 导航到执行记录页面
const navigateToExecutions = () => {
  router.push('/cicd/executions')
}
</script>

<style scoped>
/* 页面特定样式 */
.page-container {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}
.cicd-dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-header p {
  color: #666;
  font-size: 1.1rem;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 统计卡片样式 */
.stats-section {
  margin-bottom: 30px;
}

.stat-card {
  border-radius: 12px;
  overflow: hidden;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px 0;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  margin-left: 15px;
}

.servers-icon {
  background: #e8f4ff;
  color: #409eff;
}

.jobs-icon {
  background: #f0f9eb;
  color: #67c23a;
}

.executions-icon {
  background: #fff6ec;
  color: #e6a23c;
}

.success-rate-icon {
  background: #f0f0ff;
  color: #909399;
}

.stat-info {
  flex: 1;
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  color: #606266;
  font-size: 0.9rem;
}

/* 列表区域样式 */
.recent-executions-section,
.jobs-section {
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}
</style>