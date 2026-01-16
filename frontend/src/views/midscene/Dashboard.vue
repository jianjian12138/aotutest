<template>
  <div class="dashboard-container">
    <!-- 数据概览 -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-blue">
                <el-icon><Setting /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ configCount }}</div>
                <div class="stat-label">Midscene配置</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-green">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ taskCount }}</div>
                <div class="stat-label">自动化任务</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-purple">
                <el-icon><VideoPlay /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ executedCount }}</div>
                <div class="stat-label">已执行任务</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 快速执行和最近任务 -->
    <el-row :gutter="20" class="content-section">
      <!-- 快速执行区域 -->
      <el-col :span="12">
      <el-card class="quick-execution" title="快速执行" shadow="hover">
        <div class="execution-content">
          <el-form-item label="Midscene 配置">
            <el-select
              v-model="selectedConfig"
              placeholder="选择 Midscene 配置"
              style="width: 100%"
            >
              <el-option
                v-for="config in configs"
                :key="config.id"
                :label="config.name"
                :value="config.id"
              >
                <span>{{ config.name }}</span>
                <span v-if="!config.is_active" style="color: #909399; font-size: 12px; margin-left: 10px;">(已停用)</span>
              </el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="自然语言指令">
            <el-input
              v-model="naturalLanguage"
              type="textarea"
              :rows="4"
              placeholder="请输入自然语言指令，例如：打开百度首页，搜索'测试平台'并点击第一个结果"
              resize="vertical"
            />
          </el-form-item>
          
          <div class="execution-actions">
            <el-button
              type="primary"
              size="large"
              @click="executeQuickTask"
              :disabled="!selectedConfig || !naturalLanguage.trim() || executing"
            >
              <el-icon v-if="executing"><Loading /></el-icon>
              <el-icon v-else><VideoPlay /></el-icon>
              {{ executing ? '执行中...' : '立即执行' }}
            </el-button>
          </div>
        </div>
      </el-card>
      </el-col>
      
      <!-- 最近任务记录 -->
      <el-col :span="12">
        <el-card class="recent-tasks" title="最近任务" shadow="hover">
          <div v-if="loadingTasks" class="loading-container">
            <el-empty description="加载中..." />
          </div>
          <div v-else-if="recentTasks.length === 0" class="tasks-list">
            <el-empty description="暂无任务记录" />
          </div>
          <div v-else class="tasks-list">
            <div v-for="task in recentTasks" :key="task.id" class="task-item">
              <div class="task-header">
                <div class="task-title">{{ task.name }}</div>
                <el-tag
                  :type="task.status === 'SUCCESS' ? 'success' : (task.status === 'FAILED' ? 'danger' : (task.status === 'RUNNING' ? 'primary' : 'warning'))"
                  size="small"
                >
                  {{ task.status === 'SUCCESS' ? '成功' : (task.status === 'FAILED' ? '失败' : (task.status === 'RUNNING' ? '运行中' : (task.status === 'PENDING' ? '等待中' : '已停止'))) }}
                </el-tag>
              </div>
              <div class="task-description">{{ task.natural_language }}</div>
              <div class="task-meta">
                <span class="task-time">{{ formatTime(task.start_time) }}</span>
                <span class="task-actions">
                  <el-button
                    type="primary"
                    size="small"
                    @click="viewTask(task)"
                  >
                    查看
                  </el-button>
                  <el-button
                    type="success"
                    size="small"
                    @click="reuseTask(task)"
                    :disabled="!task.status === 'SUCCESS'"
                  >
                    复用
                  </el-button>
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 核心功能介绍 -->
    <div class="features-section">
      <h2 class="section-title">核心功能</h2>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <h3 class="feature-title">自然语言驱动</h3>
            <p class="feature-description">使用自然语言描述UI操作，Midscene.js自动生成并执行自动化脚本，无需编写代码。</p>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><Monitor /></el-icon>
            </div>
            <h3 class="feature-title">AI视觉识别</h3>
            <p class="feature-description">基于AI视觉识别技术，自动定位页面元素，无需手动编写复杂的定位表达式。</p>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="feature-card">
            <div class="feature-icon">
              <el-icon><VideoCamera /></el-icon>
            </div>
            <h3 class="feature-title">实时录制回放</h3>
            <p class="feature-description">支持实时录制UI操作，并自动生成测试脚本，方便回放和调试。</p>
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
  Setting, Document, VideoPlay, Loading,
  ChatDotRound, Monitor, VideoCamera
} from '@element-plus/icons-vue'
import router from '@/router'
import {
  getMidsceneConfigs,
  getMidsceneTasks,
  executeQuickMidsceneTask
} from '@/api/midscene'

// 配置和快速执行
const configs = ref([])
const selectedConfig = ref('')
const naturalLanguage = ref('')
const executing = ref(false)

// 统计数据
const configCount = ref(0)
const taskCount = ref(0)
const executedCount = ref(0)

// 任务列表
const loadingTasks = ref(false)
const recentTasks = ref([])

// 加载配置和统计数据
const loadConfigs = async () => {
  try {
    const res = await getMidsceneConfigs().catch(() => ({ data: { results: [] } }))
    configs.value = res.data.results || []
    
    // 如果没有配置，添加模拟配置
    if (configs.value.length === 0) {
      configs.value = [
        {
          id: 1,
          name: '默认Midscene配置',
          is_active: true
        }
      ]
      selectedConfig.value = configs.value[0].id
      ElMessage.info('使用模拟Midscene配置')
    } else {
      selectedConfig.value = configs.value[0].id
      ElMessage.success('配置加载成功')
    }
    
    configCount.value = configs.value.length
  } catch (error) {
    console.error('加载配置失败:', error)
    // 使用模拟配置
    configs.value = [
      {
        id: 1,
        name: '默认Midscene配置',
        is_active: true
      }
    ]
    selectedConfig.value = configs.value[0].id
    configCount.value = configs.value.length
    ElMessage.info('加载配置失败，使用模拟配置')
  }
}

// 加载最近任务
const loadRecentTasks = async () => {
  loadingTasks.value = true
  try {
    const res = await getMidsceneTasks({ page_size: 10, ordering: '-start_time' }).catch(() => ({ data: { results: [] } }))
    recentTasks.value = res.data.results || []
    
    // 如果没有任务记录，添加模拟记录
    if (recentTasks.value.length === 0) {
      recentTasks.value = [
        {
          id: 1,
          name: '百度搜索测试',
          natural_language: '打开百度首页，搜索"测试平台"并点击第一个结果',
          status: 'SUCCESS',
          config: 1,
          start_time: new Date().toISOString()
        },
        {
          id: 2,
          name: '淘宝商品浏览',
          natural_language: '打开淘宝首页，搜索"手机"，查看前5个商品',
          status: 'SUCCESS',
          config: 1,
          start_time: new Date(Date.now() - 3600000).toISOString()
        },
        {
          id: 3,
          name: '京东登录测试',
          natural_language: '打开京东首页，点击登录按钮，输入用户名和密码',
          status: 'FAILED',
          config: 1,
          start_time: new Date(Date.now() - 7200000).toISOString()
        }
      ]
      ElMessage.info('使用模拟任务记录')
    } else {
      ElMessage.success('任务记录加载成功')
    }
    
    taskCount.value = recentTasks.value.length
    executedCount.value = recentTasks.value.filter(task => task.status === 'SUCCESS' || task.status === 'FAILED').length
  } catch (error) {
    console.error('加载任务失败:', error)
    // 使用模拟任务记录
    recentTasks.value = [
      {
        id: 1,
        name: '百度搜索测试',
        natural_language: '打开百度首页，搜索"测试平台"并点击第一个结果',
        status: 'SUCCESS',
        config: 1,
        start_time: new Date().toISOString()
      },
      {
        id: 2,
        name: '淘宝商品浏览',
        natural_language: '打开淘宝首页，搜索"手机"，查看前5个商品',
        status: 'SUCCESS',
        config: 1,
        start_time: new Date(Date.now() - 3600000).toISOString()
      }
    ]
    taskCount.value = recentTasks.value.length
    executedCount.value = recentTasks.value.filter(task => task.status === 'SUCCESS' || task.status === 'FAILED').length
    
    ElMessage.info('加载任务失败，使用模拟数据')
  } finally {
    loadingTasks.value = false
  }
}

// 快速执行任务
const executeQuickTask = async () => {
  if (!selectedConfig.value) {
    ElMessage.warning('请选择Midscene配置')
    return
  }
  
  if (!naturalLanguage.value.trim()) {
    ElMessage.warning('请输入自然语言指令')
    return
  }
  
  executing.value = true
  try {
    const res = await executeQuickMidsceneTask({
      config_id: selectedConfig.value,
      natural_language: naturalLanguage.value
    })
    
    ElMessage.success('任务执行成功')
    // 更新最近任务列表
    loadRecentTasks()
    // 清空输入
    naturalLanguage.value = ''
  } catch (error) {
    ElMessage.error('任务执行失败')
    console.error('执行任务失败:', error)
  } finally {
    executing.value = false
  }
}

// 查看任务详情
const viewTask = (task) => {
  router.push(`/midscene/tasks/${task.id}`)
}

// 复用任务
const reuseTask = (task) => {
  selectedConfig.value = task.config
  naturalLanguage.value = task.natural_language
  ElMessage.info('已复用任务指令')
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
  loadConfigs()
  loadRecentTasks()
})
</script>

<style scoped>
.dashboard-container {
  width: 100%;
  padding: 0 20px;
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

.quick-execution {
  height: 100%;
}

.execution-content {
  margin-top: 20px;
}

.execution-actions {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.recent-tasks {
  height: 100%;
}

.loading-container {
  padding: 40px 0;
}

.tasks-list {
  max-height: 400px;
  overflow-y: auto;
}

.task-item {
  padding: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.task-item:last-child {
  border-bottom: none;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-title {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.task-description {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
  line-height: 1.5;
  word-break: break-all;
}

.task-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
}

.task-time {
  color: #bbb;
}

.task-actions {
  display: flex;
  gap: 8px;
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
</style>
