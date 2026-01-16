<template>
  <div class="request-history">
    <div class="header">
      <h3>请求历史</h3>
      <div class="filters">
        <el-input
          v-model="searchText"
          placeholder="搜索请求"
          style="width: 200px"
          clearable
          @input="loadHistory"
        />
        <el-button 
          type="danger" 
          :disabled="selectedIds.length === 0"
          @click="handleBatchDelete"
        >
          批量删除
        </el-button>
        <el-button @click="clearHistory" type="danger" plain>
          清空历史
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="HTTP请求" name="HTTP">
        <HistoryTable 
          :data="httpHistory" 
          :loading="loading"
          @view-detail="viewDetail"
          @retry-request="retryRequest"
          @selection-change="handleSelectionChange"
          @delete-item="handleDelete"
        />
      </el-tab-pane>
      <el-tab-pane label="WebSocket请求" name="WEBSOCKET">
        <HistoryTable 
          :data="websocketHistory" 
          :loading="loading"
          @view-detail="viewDetail"
          @retry-request="retryRequest"
          @selection-change="handleSelectionChange"
          @delete-item="handleDelete"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
      class="pagination"
    />

    <!-- 详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="请求详情"
      width="80%"
      :top="'5vh'"
    >
      <div v-if="selectedHistory" class="history-detail">
        <el-descriptions title="基本信息" :column="2" border>
          <el-descriptions-item label="请求名称">
            {{ selectedHistory.request.name }}
          </el-descriptions-item>
          <el-descriptions-item label="请求方法">
            <el-tag :type="getMethodType(selectedHistory.request.method)">
              {{ selectedHistory.request.method }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态码">
            <el-tag :type="getStatusType(selectedHistory.status_code)">
              {{ selectedHistory.status_code || '无响应' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="响应时间">
            {{ selectedHistory.response_time?.toFixed(0) || 0 }}ms
          </el-descriptions-item>
          <el-descriptions-item label="执行时间">
            {{ formatDate(selectedHistory.executed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="执行者">
            {{ selectedHistory.executed_by.username }}
          </el-descriptions-item>
        </el-descriptions>

        <el-tabs v-model="detailTab" class="detail-tabs">
          <el-tab-pane label="请求信息" name="request">
            <div class="detail-section">
              <h4>请求URL</h4>
              <el-input v-model="selectedHistory.request_data.url" readonly />
              
              <h4>请求头</h4>
              <el-table :data="formatHeaders(selectedHistory.request_data.headers)" style="width: 100%">
                <el-table-column prop="key" label="Key" width="200" />
                <el-table-column prop="value" label="Value" />
              </el-table>
              
              <h4 v-if="selectedHistory.request_data.params && Object.keys(selectedHistory.request_data.params).length > 0">
                请求参数
              </h4>
              <el-table 
                v-if="selectedHistory.request_data.params && Object.keys(selectedHistory.request_data.params).length > 0"
                :data="formatHeaders(selectedHistory.request_data.params)" 
                style="width: 100%"
              >
                <el-table-column prop="key" label="Key" width="200" />
                <el-table-column prop="value" label="Value" />
              </el-table>
              
              <h4 v-if="selectedHistory.request_data.body">请求体</h4>
              <pre v-if="selectedHistory.request_data.body" class="json-content">
                {{ JSON.stringify(selectedHistory.request_data.body, null, 2) }}
              </pre>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="响应信息" name="response">
            <div v-if="selectedHistory.response_data" class="detail-section">
              <h4>响应头</h4>
              <el-table :data="formatHeaders(selectedHistory.response_data.headers)" style="width: 100%">
                <el-table-column prop="key" label="Key" width="200" />
                <el-table-column prop="value" label="Value" />
              </el-table>
              
              <h4>响应体</h4>
              <div class="response-actions">
                <el-button size="small" @click="formatResponseBody">格式化</el-button>
                <el-button size="small" @click="copyResponseBody">复制</el-button>
              </div>
              <pre class="json-content">{{ responseBodyText }}</pre>
            </div>
            
            <div v-else-if="selectedHistory.error_message" class="error-section">
              <h4>错误信息</h4>
              <el-alert
                :title="selectedHistory.error_message"
                type="error"
                :closable="false"
                show-icon
              />
            </div>
            
            <div v-else class="empty-response">
              <el-empty description="无响应数据" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button type="primary" @click="retryRequest(selectedHistory)">
          重新发送
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import { deleteRequestHistory, batchDeleteRequestHistory } from '@/api/api-testing'
import dayjs from 'dayjs'
import HistoryTable from './components/HistoryTable.vue'

const activeTab = ref('HTTP')
const httpHistory = ref([])
const websocketHistory = ref([])
const loading = ref(false)
const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showDetailDialog = ref(false)
const selectedHistory = ref(null)
const detailTab = ref('request')
const selectedIds = ref([])

const currentHistory = computed(() => {
  return activeTab.value === 'HTTP' ? httpHistory.value : websocketHistory.value
})

const responseBodyText = computed(() => {
  if (!selectedHistory.value?.response_data) return ''
  
  try {
    if (selectedHistory.value.response_data.json) {
      return JSON.stringify(selectedHistory.value.response_data.json, null, 2)
    } else {
      return selectedHistory.value.response_data.body || ''
    }
  } catch (e) {
    return selectedHistory.value.response_data.body || ''
  }
})

const getMethodType = (method) => {
  const typeMap = {
    'GET': 'success',
    'POST': 'primary',
    'PUT': 'warning',
    'DELETE': 'danger',
    'PATCH': 'info'
  }
  return typeMap[method] || 'info'
}

const getStatusType = (status) => {
  if (!status) return 'info'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'warning'
  if (status >= 400) return 'danger'
  return 'info'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const formatHeaders = (headers) => {
  if (!headers || typeof headers !== 'object') return []
  return Object.keys(headers).map(key => ({
    key,
    value: headers[key]
  }))
}

const loadHistory = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      request__request_type: activeTab.value
    }
    
    if (searchText.value) {
      params.search = searchText.value
    }
    
    const response = await api.get('/api-testing/histories/', { params })
    const data = response.data.results || response.data
    
    if (activeTab.value === 'HTTP') {
      httpHistory.value = data
    } else {
      websocketHistory.value = data
    }
    
    total.value = response.data.count || data.length
  } catch (error) {
    ElMessage.error('加载请求历史失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const onTabChange = () => {
  currentPage.value = 1
  selectedIds.value = []
  loadHistory()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  loadHistory()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  loadHistory()
}

const viewDetail = (history) => {
  selectedHistory.value = history
  detailTab.value = 'request'
  showDetailDialog.value = true
}

const retryRequest = async (history) => {
  try {
    const response = await api.post(`/api-testing/requests/${history.request.id}/execute/`, {
      environment_id: history.environment?.id
    })
    ElMessage.success('请求重新发送成功')
    showDetailDialog.value = false
    await loadHistory()
  } catch (error) {
    ElMessage.error('请求重新发送失败')
    console.error(error)
  }
}

const clearHistory = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有请求历史吗？此操作不可恢复。',
      '确认清空',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 这里需要后端提供批量删除接口
    // 目前先用批量删除当前页的方式模拟，或者需要后端增加清空接口
    // 暂时提示未实现
    ElMessage.warning('清空功能暂未实现，请使用批量删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确认删除该请求历史吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteRequestHistory(row.id)
      ElMessage.success('删除成功')
      loadHistory()
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  })
}

const handleBatchDelete = () => {
  if (selectedIds.value.length === 0) return
  
  ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条记录吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await batchDeleteRequestHistory(selectedIds.value)
      ElMessage.success('批量删除成功')
      selectedIds.value = []
      loadHistory()
    } catch (error) {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  })
}

const formatResponseBody = () => {
  if (selectedHistory.value?.response_data?.json) {
    // 已经格式化了
  }
}

const copyResponseBody = () => {
  if (responseBodyText.value) {
    navigator.clipboard.writeText(responseBodyText.value)
    ElMessage.success('已复制到剪贴板')
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.request-history {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h3 {
  margin: 0;
  color: #303133;
}

.filters {
  display: flex;
  gap: 10px;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.history-detail {
  max-height: 70vh;
  overflow-y: auto;
}

.detail-tabs {
  margin-top: 20px;
}

.detail-section {
  padding: 10px 0;
}

.detail-section h4 {
  margin: 20px 0 10px 0;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.json-content {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  border: 1px solid #e4e7ed;
}

.response-actions {
  margin-bottom: 10px;
}

.error-section {
  padding: 20px 0;
}

.empty-response {
  padding: 40px 0;
  text-align: center;
}
</style>