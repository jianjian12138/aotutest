<template>
  <BasePage title="数据看板">
    
    
    <template v-if="!notImplemented">
    <el-row :gutter="20">
      <el-col :span="6" v-for="card in cards" :key="card.title">
        <el-card shadow="hover" class="dashboard-card" @click="router.push(card.path)">
          <div class="card-content">
            <el-icon :class="card.iconClass" :size="40"><component :is="card.icon" /></el-icon>
            <div class="text-content">
              <h3>{{ card.title }}</h3>
              <p>{{ card.desc }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-divider content-position="left">最近任务</el-divider>

    <el-table :data="recentTasks" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="config_name" label="任务名称" />
      <el-table-column prop="protocol" label="类型" width="120">
        <template #default="scope">
          <el-tag>{{ scope.row.protocol }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" />
    </el-table>
    </template>

    <NotImplementedPlaceholder
      v-else
      module-name="专项测试"
      :message="niMessage"
      :planned="niPlanned"
    />

  </BasePage>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/utils/request'
import { Connection, Cellphone, DataLine, Files } from '@element-plus/icons-vue'
import NotImplementedPlaceholder from '@/components/NotImplementedPlaceholder.vue'

const router = useRouter()
const recentTasks = ref([])
const loading = ref(false)
const notImplemented = ref(false)
const niMessage = ref('')
const niPlanned = ref([])

const cards = [
  { title: 'MQTT 测试', desc: 'IoT 设备通信测试', icon: Connection, iconClass: 'icon-mqtt', path: '/special-testing/mqtt' },
  { title: 'Monkey 压测', desc: 'Android 稳定性测试', icon: Cellphone, iconClass: 'icon-monkey', path: '/special-testing/monkey' },
  { title: 'Redis 工具', desc: '缓存读写验证', icon: DataLine, iconClass: 'icon-redis', path: '/special-testing/redis' },
  { title: 'Kafka 工具', desc: '消息队列验证', icon: Files, iconClass: 'icon-kafka', path: '/special-testing/kafka' }
]

const fetchRecent = async () => {
  loading.value = true
  try {
    const res = await request.get('/special-testing/tasks/')
    const data = res.data || {}
    if (data.status === 'not_implemented') {
      notImplemented.value = true
      niMessage.value = data.message || ''
      niPlanned.value = data.planned || []
      return
    }
    recentTasks.value = (data.results || data).slice(0, 5)
  } catch (e) {
    // 兜底：即便接口异常也不弹「服务器错误」，直接展示规划占位
    notImplemented.value = true
    niPlanned.value = cards.map((c) => ({ name: c.title, desc: c.desc }))
  } finally {
    loading.value = false
  }
}

const getStatusType = (status) => {
  const map = {
    'PENDING': 'info',
    'RUNNING': 'warning',
    'SUCCESS': 'success',
    'FAILED': 'danger'
  }
  return map[status] || 'info'
}

onMounted(() => {
  fetchRecent()
})
</script>

<style scoped>
.dashboard-card {
  cursor: pointer;
  transition: all 0.3s;
  height: 120px;
}
.dashboard-card:hover {
  transform: translateY(-5px);
}
.card-content {
  display: flex;
  align-items: center;
}
.text-content {
  margin-left: 20px;
}
.text-content h3 {
  margin: 0 0 5px 0;
  font-size: 16px;
}
.text-content p {
  margin: 0;
  color: #909399;
  font-size: 12px;
}
.icon-mqtt { color: #3498db; }
.icon-monkey { color: #2ecc71; }
.icon-redis { color: #e74c3c; }
.icon-kafka { color: #9b59b6; }
/* 页面特定样式 */









.test-report {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.left-filters {
  display: flex;
  gap: 16px;
}

.dashboard-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
  position: relative;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.1);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  font-size: 24px;
}

.total-plans .card-icon { background: #e8f3ff; color: #409EFF; }
.total-cases .card-icon { background: #f0f9eb; color: #67C23A; }
.pass-rate .card-icon { background: #fdf6ec; color: #E6A23C; }
.defects .card-icon { background: #fef0f0; color: #F56C6C; }

.card-content {
  flex: 1;
}

.card-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.card-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.card-extra {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.chart-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}

.chart-header {
  margin-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 10px;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
  font-weight: 600;
}

.chart-body {
  height: 300px;
  width: 100%;
}

.chart-body-small {
  height: 150px;
  width: 100%;
}

.table-body {
  overflow-y: auto;
}

.ai-metrics-container {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
}

.ai-metric-item {
  text-align: center;
  width: 30%;
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.analysis-content {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  line-height: 1.6;
  white-space: pre-wrap;
  margin-top: 10px;
}

.suggestion {
  background: #e1f3d8;
  color: #67c23a;
}
</style>
