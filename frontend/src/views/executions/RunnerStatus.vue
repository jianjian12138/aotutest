<template>
  <BasePage title="云原生执行池">
    <div class="card-container main-content">
      <el-card class="top-stats" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="title">☁️ V3.4 云原生执行池 (K8s Runner Pool)</span>
            <el-button type="primary" size="small" @click="dispatchRunner">模拟分发新 Runner</el-button>
          </div>
        </template>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="活跃容器总数" :value="stats.total" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="正在运行" :value="stats.running" value-style="color: #67c23a" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="镜像拉取/等候" :value="stats.pending" value-style="color: #e6a23c" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="资源利用率" :value="72" suffix="%" />
          </el-col>
        </el-row>
      </el-card>

      <div class="main-layout">
        <!-- Runner 列表 -->
        <el-card class="list-panel" shadow="never">
          <template #header>
            <div class="card-header">
              <span>活跃 Pod 列表</span>
              <el-button size="small" :loading="loading" plain @click="fetchRunners">刷新列表</el-button>
            </div>
          </template>
          <el-table :data="runners" stripe style="width: 100%" @row-click="showLogs">
            <el-table-column prop="id" label="Pod 名称" min-width="180">
              <template #default="scope">
                <code class="pod-name">{{ scope.row.id }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="scope">
                <el-tag :type="getStatusTag(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cpu" label="CPU" width="100" />
            <el-table-column prop="mem" label="内存" width="100" />
            <el-table-column label="操作" width="100">
              <template #default="scope">
                <el-button type="text" @click.stop="showLogs(scope.row)">日志</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 日志面板 -->
        <el-card class="log-panel" shadow="never">
          <template #header>
            <div class="log-header">
              <span>🚀 容器日志流: {{ selectedPod }}</span>
              <el-button size="small" type="info" plain @click="fetchLogs">刷新</el-button>
            </div>
          </template>
          <div class="log-content" ref="logBox">
            <div v-if="!selectedPod" class="empty-log">请点击左侧列表查看日志...</div>
            <div v-for="(line, idx) in currentLogs" :key="idx" class="log-line">
              {{ line }}
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const runners = ref([])
const selectedPod = ref('')
const currentLogs = ref([])
const logBox = ref(null)
const timer = ref(null)
const loading = ref(false)

const stats = reactive({
  total: 0,
  running: 0,
  pending: 0
})

const getStatusTag = (status) => {
  const map = { 'Running': 'success', 'Pending': 'warning', 'Succeeded': 'info', 'Failed': 'danger' }
  return map[status] || 'info'
}

const fetchRunners = async (isManual = false) => {
  if (isManual) loading.value = true
  try {
    const res = await axios.get('/api/executions/k8s-runners/')
    const body = res.data.data || res.data
    const status = res.data.status || body.status
    if (status === 'SUCCESS') {
      runners.value = body.runners || body.items || []
      stats.total = runners.value.length
      stats.running = runners.value.filter(r => r.status === 'Running').length
      stats.pending = runners.value.filter(r => r.status === 'Pending').length
    }
  } catch (err) {
    console.error('Failed to fetch runners:', err)
  } finally {
    if (isManual) loading.value = false
  }
}

const dispatchRunner = async () => {
  try {
    const res = await axios.post('/api/executions/k8s-runners/', {
      task_id: 'AUTO-EXPLORE-' + Math.floor(Math.random() * 1000)
    })
    const body = res.data.data || res.data
    const status = res.data.status || body.status
    if (status === 'SUCCESS') {
      ElMessage.success('成功申请 K8s 动态执行资源')
      fetchRunners()
    }
  } catch (err) {
    ElMessage.error('分发失败')
  }
}

const showLogs = (row) => {
  selectedPod.value = row.id
  fetchLogs()
}

const fetchLogs = async () => {
  if (!selectedPod.value) return
  try {
    const res = await axios.get('/api/executions/k8s-runners/logs/', {
      params: { pod_name: selectedPod.value }
    })
    const body = res.data.data || res.data
    const status = res.data.status || body.status
    if (status === 'SUCCESS') {
      currentLogs.value = body.logs || []
      scrollToBottom()
    }
  } catch (err) {
    console.error('Failed to fetch logs')
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (logBox.value) {
      logBox.value.scrollTop = logBox.value.scrollHeight
    }
  })
}

onMounted(() => {
  fetchRunners()
  timer.value = setInterval(() => {
    fetchRunners()
    if (selectedPod.value) fetchLogs()
  }, 3000)
})

onUnmounted(() => {
  if (timer.value) clearInterval(timer.value)
})
</script>

<style scoped>
.main-content {
  padding: 20px;
}
.top-stats {
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
.main-layout {
  display: flex;
  gap: 20px;
}
.list-panel {
  flex: 1;
}
.log-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.log-content {
  height: 500px;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  overflow-y: auto;
  border-radius: 4px;
}
.log-line {
  margin-bottom: 4px;
  word-break: break-all;
}
.pod-name {
  color: #409eff;
  font-family: monospace;
}
.empty-log {
  text-align: center;
  color: #666;
  margin-top: 200px;
}
</style>
