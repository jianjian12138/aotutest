<template>
  <BasePage title="自主探索 Agent">
    <div class="card-container main-content">
      <el-card class="control-panel" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="title">🤖 V3.1 自主探索智能体 (Autonomous Crawler)</span>
            <el-tag :type="isRunning ? 'danger' : 'success'">{{ isRunning ? '深度探索中...' : '就绪' }}</el-tag>
          </div>
        </template>
        
        <el-form :inline="true" :model="form" class="crawler-form">
          <el-form-item label="探索起点 URL">
            <el-input v-model="form.start_url" placeholder="http://localhost:5656" style="width: 300px" />
          </el-form-item>
          <el-form-item label="最大步数">
            <el-input-number v-model="form.max_steps" :min="1" :max="100" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="isRunning" @click="startExploration">
              {{ isRunning ? '正在思考并执行...' : '开启全站自主排雷' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <div class="content-layout">
        <!-- 实时日志面板 -->
        <el-card class="log-panel" shadow="never">
          <template #header>
            <div class="card-header">
              <span>🚀 探索轨迹实时日志</span>
              <el-button size="small" @click="logs = []">清空</el-button>
            </div>
          </template>
          <div class="log-content" ref="logContainer">
            <div v-if="logs.length === 0" class="empty-log">暂无探索数据，请点击上方按钮开启...</div>
            <div v-for="(log, index) in logs" :key="index" class="log-item">
              <span class="log-index">#{{ index + 1 }}</span>
              <span class="log-text">{{ log }}</span>
            </div>
          </div>
        </el-card>

        <!-- 状态与异常摘要 -->
        <div class="side-info">
          <el-card class="stats-card" shadow="never">
            <template #header><span>状态摘要</span></template>
            <el-statistic title="已发现路径" :value="discoveredPaths" />
            <el-statistic title="捕获异常" :value="capturedErrors" suffix="项" value-style="color: #cf1322" />
          </el-card>

          <el-card class="tip-card" shadow="never">
            <template #header><span>💡 AI 提示</span></template>
            <p>Agent 正在利用 Playwright + LLM Vision 模式探索 UI 逻辑。它会自动寻找所有可点击的按钮并尝试触发业务闭环。</p>
          </el-card>
        </div>
      </div>
    </div>
  </BasePage>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const isRunning = ref(false)
const logs = ref([])
const discoveredPaths = ref(0)
const capturedErrors = ref(0)
const logContainer = ref(null)

const form = reactive({
  start_url: 'http://localhost:5656',
  max_steps: 10
})

const startExploration = async () => {
  if (!form.start_url) {
    ElMessage.warning('请输入起点的 URL')
    return
  }

  isRunning.value = true
  logs.value.push('🎬 正在初始化 AI 引擎与浏览器环境...')
  
  try {
    const response = await axios.post('/api/assistant/crawler/run-exploration/', form)
    
    if (response.data.status === 'SUCCESS') {
      logs.value.push(...response.data.history)
      discoveredPaths.value = response.data.history.length
      ElMessage.success('自主探索任务圆满完成！')
    } else {
      ElMessage.error('探索任务中断')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('后台服务通信失败，请检查后端状态')
  } finally {
    isRunning.value = false
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.main-content {
  padding: 20px;
}

.control-panel {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 18px;
  font-weight: bold;
}

.content-layout {
  display: flex;
  gap: 20px;
}

.log-panel {
  flex: 2;
  height: 600px;
  display: flex;
  flex-direction: column;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  border-radius: 4px;
}

.log-item {
  margin-bottom: 8px;
  line-height: 1.6;
}

.log-index {
  color: #569cd6;
  margin-right: 10px;
}

.empty-log {
  text-align: center;
  color: #888;
  margin-top: 100px;
}

.side-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.tip-card p {
  font-size: 13px;
  color: #666;
  line-height: 1.8;
}
</style>
