<template>
  <div class="task-detail">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>任务详情</h2>
          <el-button type="primary" @click="handleExecuteTask">
            <el-icon><VideoPlay /></el-icon>
            执行任务
          </el-button>
        </div>
      </template>
      
      <!-- 任务基本信息 -->
      <div class="task-info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ task.id }}</el-descriptions-item>
          <el-descriptions-item label="任务名称">{{ task.name }}</el-descriptions-item>
          <el-descriptions-item label="任务描述">{{ task.description }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag
              :type="getStatusTagType(task.status)"
              size="small"
            >
              {{ getStatusText(task.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ task.created_at }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ task.updated_at }}</el-descriptions-item>
          <el-descriptions-item label="执行人">{{ task.executed_by }}</el-descriptions-item>
          <el-descriptions-item label="执行时间">{{ task.execution_time || '未执行' }}</el-descriptions-item>
        </el-descriptions>
      </div>
      
      <!-- 配置信息 -->
      <div class="config-info" style="margin-top: 20px;">
        <h3>配置信息</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="配置名称">{{ config.name }}</el-descriptions-item>
          <el-descriptions-item label="浏览器类型">{{ config.browser_type }}</el-descriptions-item>
          <el-descriptions-item label="配置参数">{{ JSON.stringify(config.params, null, 2) }}</el-descriptions-item>
        </el-descriptions>
      </div>
      
      <!-- 执行结果 -->
      <div class="execution-result" style="margin-top: 20px;">
        <h3>执行结果</h3>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="执行日志" name="logs">
            <el-scrollbar style="height: 400px;">
              <div class="logs-container">
                <div
                  v-for="(log, index) in executionLogs"
                  :key="index"
                  class="log-item"
                  :class="{'log-error': log.level === 'error', 'log-success': log.level === 'success'}"
                >
                  <span class="log-time">{{ log.timestamp }}</span>
                  <span class="log-level">{{ log.level.toUpperCase() }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </el-scrollbar>
          </el-tab-pane>
          <el-tab-pane label="执行报告" name="report">
            <el-card shadow="hover">
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-statistic title="总执行步数" :value="executionReport.total_steps" />
                </el-col>
                <el-col :span="8">
                  <el-statistic title="成功步数" :value="executionReport.success_steps" :suffix="'%'" />
                </el-col>
                <el-col :span="8">
                  <el-statistic title="失败步数" :value="executionReport.failed_steps" :suffix="'%'" />
                </el-col>
              </el-row>
              <div style="margin-top: 20px;">
                <h4>执行摘要</h4>
                <p>{{ executionReport.summary }}</p>
              </div>
            </el-card>
          </el-tab-pane>
          <el-tab-pane label="截图记录" name="screenshots">
            <div class="screenshots-container">
              <el-image
                v-for="(screenshot, index) in screenshots"
                :key="index"
                :src="screenshot.url"
                :fit="'contain'"
                style="width: 300px; height: 200px; margin: 10px; cursor: pointer;"
                @click="handlePreviewImage(screenshot.url)"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
    
    <!-- 图片预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      title="执行截图"
      width="80%"
    >
      <img :src="previewImageUrl" style="width: 100%; height: auto;" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { VideoPlay } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 任务ID
const taskId = computed(() => route.params.id)

// 激活的标签页
const activeTab = ref('logs')

// 任务数据
const task = ref({
  id: 1,
  name: '电商网站首页测试',
  description: '使用自然语言指令测试电商网站首页功能',
  status: 'completed',
  created_at: '2026-01-10 14:30:00',
  updated_at: '2026-01-10 14:45:00',
  executed_by: 'admin',
  execution_time: '00:01:23',
  config_id: 1
})

// 配置信息
const config = ref({
  id: 1,
  name: 'Chrome浏览器配置',
  browser_type: 'chrome',
  params: {
    width: 1920,
    height: 1080,
    headless: false,
    slowMo: 0
  }
})

// 执行日志
const executionLogs = ref([
  {
    timestamp: '2026-01-10 14:30:01',
    level: 'info',
    message: '任务开始执行'
  },
  {
    timestamp: '2026-01-10 14:30:02',
    level: 'info',
    message: '初始化Chrome浏览器'
  },
  {
    timestamp: '2026-01-10 14:30:05',
    level: 'info',
    message: '打开网页：https://www.example.com'
  },
  {
    timestamp: '2026-01-10 14:30:10',
    level: 'success',
    message: '成功加载首页'
  },
  {
    timestamp: '2026-01-10 14:30:15',
    level: 'info',
    message: '点击搜索框'
  },
  {
    timestamp: '2026-01-10 14:30:20',
    level: 'info',
    message: '输入搜索关键词：测试商品'
  },
  {
    timestamp: '2026-01-10 14:30:25',
    level: 'success',
    message: '搜索成功，显示结果列表'
  },
  {
    timestamp: '2026-01-10 14:31:23',
    level: 'info',
    message: '任务执行完成'
  }
])

// 执行报告
const executionReport = ref({
  total_steps: 10,
  success_steps: 80,
  failed_steps: 20,
  summary: '任务执行完成，共执行10个步骤，其中8个步骤成功，2个步骤失败。主要问题是商品详情页加载超时。'
})

// 截图记录
const screenshots = ref([
  { id: 1, url: 'https://via.placeholder.com/800x600?text=Step+1', description: '首页加载完成' },
  { id: 2, url: 'https://via.placeholder.com/800x600?text=Step+2', description: '搜索结果页' },
  { id: 3, url: 'https://via.placeholder.com/800x600?text=Step+3', description: '商品详情页' }
])

// 图片预览
const previewVisible = ref(false)
const previewImageUrl = ref('')

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    pending: 'warning',
    running: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}

// 执行任务
const handleExecuteTask = () => {
  ElNotification({
    title: '提示',
    message: `开始执行任务：${task.value.name}`,
    type: 'success'
  })
}

// 预览图片
const handlePreviewImage = (url) => {
  previewImageUrl.value = url
  previewVisible.value = true
}
</script>

<style scoped>
.task-detail {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logs-container {
  padding: 10px;
}

.log-item {
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 4px;
  background-color: #f5f5f5;
}

.log-time {
  color: #909399;
  margin-right: 10px;
  font-size: 12px;
}

.log-level {
  margin-right: 10px;
  font-weight: bold;
  font-size: 12px;
}

.log-error {
  background-color: #fff1f0;
}

.log-error .log-level {
  color: #f56c6c;
}

.log-success {
  background-color: #f0f9eb;
}

.log-success .log-level {
  color: #67c23a;
}

.screenshots-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>