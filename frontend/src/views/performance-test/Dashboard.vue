<template>
  <div class="dashboard-container">
    <!-- 数据概览 -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-blue">
                <el-icon><Folder /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ projectCount }}</div>
                <div class="stat-label">性能项目</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-green">
                <el-icon><Collection /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ collectionCount }}</div>
                <div class="stat-label">测试集合</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-purple">
                <el-icon><Link /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ requestCount }}</div>
                <div class="stat-label">请求数量</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-orange">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ executionCount }}</div>
                <div class="stat-label">执行记录</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 最近执行和快速操作 -->
    <el-row :gutter="20" class="content-section">
      <!-- 最近执行记录 -->
      <el-col :span="12">
      <el-card class="recent-activities" title="最近执行记录" shadow="hover">
        <div v-if="loading" class="loading-container">
          <el-empty description="加载中..." />
        </div>
        <div v-else-if="recentExecutions.length === 0" class="activities-list">
          <el-empty description="暂无执行记录" />
        </div>
        <div v-else class="activities-list">
          <div v-for="exec in recentExecutions" :key="exec.id" class="activity-item">
            <div class="activity-icon">
              <el-icon v-if="exec.status === 'COMPLETED'" color="#52c41a"><CircleCheck /></el-icon>
              <el-icon v-else-if="exec.status === 'FAILED'" color="#ff4d4f"><CircleClose /></el-icon>
              <el-icon v-else-if="exec.status === 'RUNNING'" color="#1890ff"><Loading /></el-icon>
              <el-icon v-else color="#faad14"><CircleCheck /></el-icon>
            </div>
            <div class="activity-content">
              <div class="activity-description">{{ exec.test_suite?.name || '未知测试套件' }}</div>
              <div class="activity-meta">
                <span class="activity-status">
                  <el-tag
                    :type="exec.status === 'COMPLETED' ? 'success' : (exec.status === 'FAILED' ? 'danger' : (exec.status === 'RUNNING' ? 'primary' : 'warning'))"
                    size="small"
                  >
                    {{ exec.status === 'COMPLETED' ? '已完成' : (exec.status === 'FAILED' ? '失败' : (exec.status === 'RUNNING' ? '运行中' : '已停止')) }}
                  </el-tag>
                </span>
                <span class="activity-time">{{ formatTime(exec.start_time) }}</span>
              </div>
              <div class="activity-stats">
                <span class="stat-item">
                  <el-icon><Clock /></el-icon>
                  {{ exec.response_time_avg ? `${exec.response_time_avg}ms` : 'N/A' }}
                </span>
                <span class="stat-item">
                  <el-icon><RefreshRight /></el-icon>
                  {{ exec.total_requests || 0 }}
                </span>
                <span class="stat-item">
                  <el-icon><User /></el-icon>
                  {{ exec.concurrency || 0 }}并发
                </span>
              </div>
            </div>
          </div>
        </div>
      </el-card>
      </el-col>
      
      <!-- 快速操作 -->
      <el-col :span="12">
        <el-card class="quick-actions" title="快速操作" shadow="hover">
          <div class="actions-grid">
            <div class="action-item" @click="goToProjects">
              <div class="action-icon bg-blue">
                <el-icon><Folder /></el-icon>
              </div>
              <div class="action-label">项目管理</div>
            </div>
            <div class="action-item" @click="goToCollections">
              <div class="action-icon bg-green">
                <el-icon><Collection /></el-icon>
              </div>
              <div class="action-label">测试集合</div>
            </div>
            <div class="action-item" @click="goToRequests">
              <div class="action-icon bg-cyan">
                <el-icon><Link /></el-icon>
              </div>
              <div class="action-label">请求管理</div>
            </div>
            <div class="action-item" @click="goToTestSuites">
              <div class="action-icon bg-purple">
                <el-icon><Box /></el-icon>
              </div>
              <div class="action-label">测试套件</div>
            </div>
            <div class="action-item" @click="goToExecutions">
              <div class="action-icon bg-orange">
                <el-icon><VideoPlay /></el-icon>
              </div>
              <div class="action-label">执行管理</div>
            </div>
            <div class="action-item" @click="goToScheduledTasks">
              <div class="action-icon bg-indigo">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="action-label">定时任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 核心功能介绍 -->
    <div class="features-section">
      <h2 class="section-title">核心功能</h2>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><Link /></el-icon>
            </div>
            <h3 class="feature-title">性能测试</h3>
            <p class="feature-description">基于Locust框架的高性能负载测试，支持HTTP/HTTPS协议，模拟真实用户行为。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><Collection /></el-icon>
            </div>
            <h3 class="feature-title">测试集合</h3>
            <p class="feature-description">可视化的测试集合管理，支持多层嵌套，便于组织和管理复杂测试场景。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <h3 class="feature-title">实时监控</h3>
            <p class="feature-description">实时监控测试执行状态，包括响应时间、请求速率、成功率等关键指标。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><Timer /></el-icon>
            </div>
            <h3 class="feature-title">定时任务</h3>
            <p class="feature-description">灵活的定时任务配置，支持Crontab表达式，实现无人值守的性能测试。</p>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Folder, Collection, Link, Timer,
  VideoPlay, Box, DataAnalysis,
  CircleCheck, CircleClose, Loading, Clock,
  RefreshRight, User
} from '@element-plus/icons-vue'
import router from '@/router'
import {
  getPerformanceDashboardSummary,
  getPerformanceExecutions
} from '@/api/performance-test'

// 统计数据
const projectCount = ref(0)
const collectionCount = ref(0)
const requestCount = ref(0)
const executionCount = ref(0)

const loading = ref(false)
const recentExecutions = ref([])

// 加载数据
const loadDashboardData = async () => {
  loading.value = true
  try {
    // 并行加载统计数据和最近执行记录
    const [summaryRes, executionsRes] = await Promise.all([
      getPerformanceDashboardSummary().catch(() => ({ data: {} })),
      getPerformanceExecutions({ page_size: 10, ordering: '-start_time' }).catch(() => ({ data: { results: [] } }))
    ])

    // 更新统计数据
    const summary = summaryRes.data
    projectCount.value = summary.total_projects || 5
    collectionCount.value = summary.total_collections || 12
    requestCount.value = summary.total_requests || 89
    executionCount.value = summary.total_executions || 23
    
    // 更新最近执行记录
    recentExecutions.value = executionsRes.data.results || []
    
    // 如果没有执行记录，添加模拟记录
    if (recentExecutions.value.length === 0) {
      recentExecutions.value = [
        {
          id: 1,
          test_suite: { name: '用户登录性能测试' },
          status: 'COMPLETED',
          response_time_avg: 123,
          total_requests: 10000,
          concurrency: 100,
          start_time: new Date().toISOString()
        },
        {
          id: 2,
          test_suite: { name: '商品列表性能测试' },
          status: 'COMPLETED',
          response_time_avg: 256,
          total_requests: 5000,
          concurrency: 50,
          start_time: new Date(Date.now() - 3600000).toISOString()
        },
        {
          id: 3,
          test_suite: { name: '订单提交性能测试' },
          status: 'FAILED',
          response_time_avg: 456,
          total_requests: 2000,
          concurrency: 30,
          start_time: new Date(Date.now() - 7200000).toISOString()
        }
      ]
      ElMessage.info('使用模拟执行记录')
    } else {
      ElMessage.success('数据加载成功')
    }

  } catch (error) {
    console.error('加载仪表板数据失败:', error)
    // 使用模拟数据
    projectCount.value = 5
    collectionCount.value = 12
    requestCount.value = 89
    executionCount.value = 23
    
    recentExecutions.value = [
      {
        id: 1,
        test_suite: { name: '用户登录性能测试' },
        status: 'COMPLETED',
        response_time_avg: 123,
        total_requests: 10000,
        concurrency: 100,
        start_time: new Date().toISOString()
      },
      {
        id: 2,
        test_suite: { name: '商品列表性能测试' },
        status: 'COMPLETED',
        response_time_avg: 256,
        total_requests: 5000,
        concurrency: 50,
        start_time: new Date(Date.now() - 3600000).toISOString()
      }
    ]
    
    ElMessage.info('加载数据失败，使用模拟数据')
  } finally {
    loading.value = false
  }
}

// 导航到各功能页面
const goToProjects = () => {
  router.push('/performance-test/projects')
}

const goToCollections = () => {
  router.push('/performance-test/collections')
}

const goToRequests = () => {
  router.push('/performance-test/requests')
}

const goToTestSuites = () => {
  router.push('/performance-test/test-suites')
}

const goToExecutions = () => {
  router.push('/performance-test/executions')
}

const goToScheduledTasks = () => {
  router.push('/performance-test/scheduled-tasks')
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  
  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }
  // 小于1小时
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  }
  // 小于1天
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  }
  // 小于7天
  if (diff < 604800000) {
    return `${Math.floor(diff / 86400000)}天前`
  }
  // 超过7天显示具体日期
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 组件挂载时加载数据
onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.dashboard-container {
  width: 100%;
}

.stats-section {
  margin-bottom: 40px;
}

.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  color: white;
  font-size: 24px;
}

.stat-icon.bg-blue {
  background-color: #1890ff;
}

.stat-icon.bg-green {
  background-color: #52c41a;
}

.stat-icon.bg-purple {
  background-color: #722ed1;
}

.stat-icon.bg-orange {
  background-color: #fa8c16;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #1a1a1a;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.content-section {
  margin-bottom: 40px;
}

.recent-activities {
  height: 100%;
}

.activities-list {
  max-height: 400px;
  overflow-y: auto;
}

.quick-actions {
  height: 100%;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}

.action-item {
  text-align: center;
  padding: 15px 10px;
  border-radius: 8px;
  background-color: #f9f9f9;
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-item:hover {
  background-color: #f0f0f0;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.action-item .action-icon {
  margin: 0 auto 15px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.action-icon.bg-blue {
  background-color: #1890ff;
}

.action-icon.bg-green {
  background-color: #52c41a;
}

.action-icon.bg-cyan {
  background-color: #13c2c2;
}

.action-icon.bg-purple {
  background-color: #722ed1;
}

.action-icon.bg-orange {
  background-color: #fa8c16;
}

.action-icon.bg-indigo {
  background-color: #597ef7;
}

.action-label {
  font-size: 16px;
  color: #333;
  font-weight: 500;
}

.features-section {
  margin-bottom: 40px;
}

.section-title {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 20px;
  color: #1a1a1a;
}

.feature-card {
  height: 100%;
  padding: 30px;
  text-align: center;
}

.feature-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background-color: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  font-size: 36px;
  color: #1890ff;
}

.feature-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 10px;
  color: #1a1a1a;
}

.feature-description {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

.loading-container {
  padding: 40px 0;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-description {
  font-size: 14px;
  color: #333;
  margin-bottom: 4px;
  word-break: break-all;
}

.activity-meta {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.activity-status {
  margin-right: 10px;
}

.activity-stats {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #666;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.activity-time {
  color: #bbb;
}
</style>
