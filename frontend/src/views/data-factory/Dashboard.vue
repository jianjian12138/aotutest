<template>
  <div class="dashboard-container">   
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">数据工厂数据看板</h2>
        </div>
      </template>
    </el-card>
    <!-- 数据概览 -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-blue">
                <el-icon><Setting /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ configCount }}</div>
                <div class="stat-label">Vanna配置</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-green">
                <el-icon><Folder /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ projectCount }}</div>
                <div class="stat-label">数据项目</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-purple">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ queryCount }}</div>
                <div class="stat-label">保存查询</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-orange">
                <el-icon><DataLine /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ generationCount }}</div>
                <div class="stat-label">SQL生成</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 最近活动和快速操作 -->
    <el-row :gutter="20" class="content-section">
      <!-- 最近SQL生成记录 -->
      <el-col :span="12">
      <el-card class="recent-activities" title="最近SQL生成" shadow="hover">
        <div v-if="loading" class="loading-container">
          <el-empty description="加载中..." />
        </div>
        <div v-else-if="recentGenerations.length === 0" class="activities-list">
          <el-empty description="暂无SQL生成记录" />
        </div>
        <div v-else class="activities-list">
          <div v-for="gen in recentGenerations" :key="gen.id" class="activity-item">
            <div class="activity-icon">
              <el-icon v-if="gen.status === 'SUCCESS'" color="#52c41a"><CircleCheck /></el-icon>
              <el-icon v-else-if="gen.status === 'FAILED'" color="#ff4d4f"><CircleClose /></el-icon>
              <el-icon v-else color="#1890ff"><CircleCheck /></el-icon>
            </div>
            <div class="activity-content">
              <div class="activity-description">{{ gen.natural_language }}</div>
              <div class="activity-meta">
                <span class="activity-user">{{ gen.created_by?.username || '系统' }}</span>
                <span class="activity-time">{{ formatTime(gen.created_at) }}</span>
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
            <div class="action-item" @click="goToSqlGeneration">
              <div class="action-icon bg-blue">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              <div class="action-label">SQL生成</div>
            </div>
            <div class="action-item" @click="goToConfig">
              <div class="action-icon bg-green">
                <el-icon><Setting /></el-icon>
              </div>
              <div class="action-label">Vanna配置</div>
            </div>
            <div class="action-item" @click="goToProjects">
              <div class="action-icon bg-cyan">
                <el-icon><Folder /></el-icon>
              </div>
              <div class="action-label">项目管理</div>
            </div>
            <div class="action-item" @click="goToSavedQueries">
              <div class="action-icon bg-purple">
                <el-icon><Document /></el-icon>
              </div>
              <div class="action-label">保存查询</div>
            </div>
            <div class="action-item" @click="goToTableMetadata">
              <div class="action-icon bg-orange">
              <el-icon><DataBoard /></el-icon>
            </div>
              <div class="action-label">表元数据</div>
            </div>
            <div class="action-item" @click="goToQueryHistory">
              <div class="action-icon bg-indigo">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="action-label">查询历史</div>
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
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <h3 class="feature-title">自然语言生成SQL</h3>
            <p class="feature-description">通过Vanna AI，使用自然语言描述需求，自动生成SQL查询语句，无需手动编写复杂SQL。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><DataBoard /></el-icon>
            </div>
            <h3 class="feature-title">智能表元数据管理</h3>
            <p class="feature-description">自动获取和管理数据库表结构，支持多种数据库类型，为AI生成SQL提供准确的表信息。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><Document /></el-icon>
            </div>
            <h3 class="feature-title">查询保存与分享</h3>
            <p class="feature-description">保存常用的自然语言查询和生成的SQL，支持收藏和分享，提高团队协作效率。</p>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <h3 class="feature-title">实时查询执行</h3>
            <p class="feature-description">一键执行生成的SQL，实时获取查询结果，支持结果导出和可视化展示。</p>
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
  Setting, Folder, Document, DataLine,
  ChatDotRound, Timer, DataAnalysis, DataBoard,
  CircleCheck, CircleClose
} from '@element-plus/icons-vue'
import router from '@/router'
import {
  getDashboardSummary,
  getSqlGenerations
} from '@/api/data-factory'

// 统计数据
const configCount = ref(0)
const projectCount = ref(0)
const queryCount = ref(0)
const generationCount = ref(0)

const loading = ref(false)
const recentGenerations = ref([])

// 加载数据
const loadDashboardData = async () => {
  loading.value = true
  try {
    // 并行加载统计数据和最近生成记录
    const [summaryRes, generationsRes] = await Promise.all([
      getDashboardSummary().catch(() => ({ data: {} })),
      getSqlGenerations({ page_size: 10, ordering: '-created_at' }).catch(() => ({ data: { results: [] } }))
    ])

    // 更新统计数据
    const summary = summaryRes.data
    configCount.value = summary.total_configs || 0
    projectCount.value = summary.total_projects || 0
    queryCount.value = summary.total_queries || 0
    
    // 更新最近生成记录
    recentGenerations.value = generationsRes.data.results || []
    generationCount.value = recentGenerations.value.length || 0

    ElMessage.success('数据加载成功')
  } catch (error) {
    console.error('加载仪表板数据失败:', error)
    ElMessage.error('数据加载失败，使用模拟数据')
    // 使用模拟数据
    configCount.value = 1
    projectCount.value = 5
    queryCount.value = 10
    generationCount.value = 15
    recentGenerations.value = [
      {
        id: 1,
        natural_language: '查询最近7天的用户注册数',
        status: 'SUCCESS',
        created_by: { username: 'admin' },
        created_at: new Date().toISOString()
      },
      {
        id: 2,
        natural_language: '查询活跃用户的平均年龄',
        status: 'SUCCESS',
        created_by: { username: 'test' },
        created_at: new Date(Date.now() - 3600000).toISOString()
      }
    ]
  } finally {
    loading.value = false
  }
}

// 导航到各功能页面
const goToSqlGeneration = () => {
  router.push('/data-factory/sql-generation')
}

const goToConfig = () => {
  router.push('/data-factory/config')
}

const goToProjects = () => {
  router.push('/data-factory/projects')
}

const goToSavedQueries = () => {
  router.push('/data-factory/saved-queries')
}

const goToTableMetadata = () => {
  router.push('/data-factory/table-metadata')
}

const goToQueryHistory = () => {
  router.push('/data-factory/query-history')
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
/* 页面特定样式 */
.page-container {
  padding: 0;
  display: flex;
  flex-direction: column;
  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}
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
