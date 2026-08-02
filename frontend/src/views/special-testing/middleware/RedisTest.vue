<template>
  <BasePage title="Redis 工具">
    <template #actions>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>
        新建任务
      </el-button>
    </template>
    <el-table :data="tasks" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="config_name" label="任务名称" />
      <el-table-column label="配置信息">
        <template #default="scope">
          <div>Host: {{ scope.row.config_snapshot?.redis_host }}:{{ scope.row.config_snapshot?.redis_port }}</div>
          <div>模式: {{ scope.row.config_snapshot?.redis_test_mode === 'BENCHMARK' ? '基准测试' : '命令执行' }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" />
      <el-table-column label="操作" width="250">
        <template #default="scope">
          <el-button size="small" @click="viewLog(scope.row)">日志</el-button>
          <el-button size="small" type="primary" @click="runTask(scope.row.id)" :disabled="scope.row.status === 'RUNNING'">执行</el-button>
          <el-popconfirm title="确定删除吗？" @confirm="deleteTask(scope.row)">
            <template #reference>
               <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建 Redis 测试" width="600px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="任务名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="Host">
          <el-input v-model="form.redis_host" placeholder="localhost" />
        </el-form-item>
        <el-form-item label="Port">
          <el-input-number v-model="form.redis_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="Password">
          <el-input v-model="form.redis_password" type="password" show-password />
        </el-form-item>
        
        <el-form-item label="测试模式">
          <el-radio-group v-model="form.redis_test_mode">
            <el-radio label="COMMAND">命令执行</el-radio>
            <el-radio label="BENCHMARK">基准测试</el-radio>
          </el-radio-group>
        </el-form-item>

        <template v-if="form.redis_test_mode === 'COMMAND'">
           <el-form-item label="Command">
             <el-input 
               v-model="form.redis_command" 
               type="textarea" 
               :rows="3"
               placeholder="PING\nSET key val\nGET key" 
             />
             <div style="font-size: 12px; color: #999">支持多行命令</div>
           </el-form-item>
        </template>

        <template v-else>
           <el-form-item label="并发数">
             <el-input-number v-model="form.redis_benchmark_concurrency" :min="1" :max="200" />
           </el-form-item>
           <el-form-item label="总请求数">
             <el-input-number v-model="form.redis_benchmark_requests" :min="100" :step="100" />
           </el-form-item>
        </template>

      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTask">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="logVisible" title="执行日志" width="60%">
      <pre class="log-content">{{ currentLog }}</pre>
    </el-dialog>

  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const loading = ref(false)
const tasks = ref([])
const dialogVisible = ref(false)
const logVisible = ref(false)
const currentLog = ref('')

const form = reactive({
  name: '',
  protocol: 'REDIS',
  redis_host: 'localhost',
  redis_port: 6379,
  redis_password: '',
  redis_test_mode: 'COMMAND',
  redis_command: 'PING',
  redis_benchmark_concurrency: 10,
  redis_benchmark_requests: 1000
})

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await request.get('/special-testing/tasks/', { params: { protocol: 'REDIS' } })
    tasks.value = res.data.results || res.data
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  dialogVisible.value = true
}

const createTask = async () => {
  try {
    const configRes = await request.post('/special-testing/configs/', form)
    await request.post('/special-testing/tasks/', { config: configRes.data.id })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchTasks()
  } catch (e) {
    ElMessage.error('创建失败')
  }
}

const runTask = async (id) => {
  try {
    await request.post(`/special-testing/tasks/${id}/run/`)
    ElMessage.success('开始执行')
    fetchTasks()
  } catch (e) {
    ElMessage.error('执行失败')
  }
}

const deleteTask = async (row) => {
  try {
    await request.delete(`/special-testing/tasks/${row.id}/`)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const viewLog = (row) => {
  currentLog.value = row.result_log || '暂无日志'
  logVisible.value = true
}

const getStatusType = (status) => {
  return { 'PENDING': 'info', 'RUNNING': 'warning', 'SUCCESS': 'success', 'FAILED': 'danger' }[status] || 'info'
}

onMounted(() => {
  fetchTasks()
})
</script>

<style scoped>
.log-content { background: #f5f7fa; padding: 10px; max-height: 400px; overflow: auto; }
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
