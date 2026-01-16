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
                <div class="stat-label">接口项目</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-green">
                <el-icon><Link /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ interfaceCount }}</div>
                <div class="stat-label">接口数量</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-purple">
                <el-icon><Collection /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ suiteCount }}</div>
                <div class="stat-label">测试套件</div>
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
                <div class="stat-value">{{ historyCount }}</div>
                <div class="stat-label">执行记录</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 最近活动和快速操作 -->
    <el-row :gutter="20" class="content-section">
      <!-- 最近活动 -->
      <el-col :span="12">
      <el-card class="recent-activities" title="操作日志" shadow="hover">
        <div v-if="loading" class="loading-container">
          <el-empty description="加载中..." />
        </div>
        <div v-else-if="operationLogs.length === 0" class="activities-list">
          <el-empty description="暂无操作记录" />
        </div>
        <div v-else class="activities-list">
          <div v-for="log in operationLogs" :key="log.id" class="activity-item">
            <div class="activity-icon">
              <el-icon v-if="log.operation_type === 'create'" color="#52c41a"><Plus /></el-icon>
              <el-icon v-else-if="log.operation_type === 'edit'" color="#1890ff"><Edit /></el-icon>
              <el-icon v-else-if="log.operation_type === 'delete'" color="#ff4d4f"><Delete /></el-icon>
              <el-icon v-else-if="log.operation_type === 'execute'" color="#722ed1"><VideoPlay /></el-icon>
              <el-icon v-else color="#666"><Operation /></el-icon>
            </div>
            <div class="activity-content">
              <div class="activity-description">{{ log.description }}</div>
              <div class="activity-meta">
                <span class="activity-user">{{ log.user_name || '系统' }}</span>
                <span class="activity-time">{{ formatTime(log.created_at) }}</span>
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
            <div class="action-item" @click="goToInterfaces">
              <div class="action-icon bg-green">
                <el-icon><Link /></el-icon>
              </div>
              <div class="action-label">接口管理</div>
            </div>
            <div class="action-item" @click="goToAutomation">
              <div class="action-icon bg-cyan">
                <el-icon><VideoPlay /></el-icon>
              </div>
              <div class="action-label">自动化测试</div>
            </div>
            <div class="action-item" @click="goToHistory">
              <div class="action-icon bg-purple">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="action-label">请求历史</div>
            </div>
            <div class="action-item" @click="goToEnvironments">
              <div class="action-icon bg-orange">
                <el-icon><Setting /></el-icon>
              </div>
              <div class="action-label">环境管理</div>
            </div>
            <div class="action-item" @click="goToReports">
              <div class="action-icon bg-indigo">
                <el-icon><DataAnalysis /></el-icon>
              </div>
              <div class="action-label">测试报告</div>
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
            <h3 class="feature-title">接口管理</h3>
            <p class="feature-description">支持HTTP/HTTPS协议，快速导入Swagger/Postman数据，实现接口统一管理。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><VideoPlay /></el-icon>
            </div>
            <h3 class="feature-title">自动化测试</h3>
            <p class="feature-description">可视化的测试流程编排，支持断言、提取变量、前置/后置脚本等高级功能。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><Timer /></el-icon>
            </div>
            <h3 class="feature-title">定时任务</h3>
            <p class="feature-description">灵活的定时任务配置，支持Crontab表达式，实现无人值守的自动化回归测试。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <h3 class="feature-title">多维报告</h3>
            <p class="feature-description">生成详细的测试报告，包含成功率、响应时间趋势等多维度数据分析。</p>
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
  Folder, Link, Collection, Timer,
  VideoPlay, Setting, DataAnalysis,
  Plus, Edit, Delete, Operation
} from '@element-plus/icons-vue'
import router from '@/router'
import {
  getDashboardStats,
  getOperationLogs
} from '@/api/api-testing'

// 统计数据
const projectCount = ref(0)
const interfaceCount = ref(0)
const suiteCount = ref(0)
const historyCount = ref(0)

const loading = ref(false)
const operationLogs = ref([])

// 加载数据
const loadDashboardData = async () => {
  loading.value = true
  try {
    // 并行加载统计数据和操作日志
    const [statsRes, logsRes] = await Promise.all([
      getDashboardStats(),
      getOperationLogs({ page_size: 20, ordering: '-created_at' })
    ])

    // 更新统计数据
    const stats = statsRes.data
    projectCount.value = stats.project_count || 0
    interfaceCount.value = stats.interface_count || 0
    suiteCount.value = stats.suite_count || 0
    historyCount.value = stats.history_count || 0
    
    // 更新操作日志
    operationLogs.value = logsRes.data.results || []

  } catch (error) {
    // ElMessage.error('加载仪表板数据失败')
    console.error('加载仪表板数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 导航到各功能页面
const goToProjects = () => {
  router.push('/api-testing/projects')
}

const goToInterfaces = () => {
  router.push('/api-testing/interfaces')
}

const goToAutomation = () => {
  router.push('/api-testing/automation')
}

const goToHistory = () => {
  router.push('/api-testing/history')
}

const goToEnvironments = () => {
  router.push('/api-testing/environments')
}

const goToReports = () => {
  router.push('/api-testing/reports')
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
}

.activity-user {
  margin-right: 12px;
}

.activity-time {
  color: #bbb;
}
</style>
