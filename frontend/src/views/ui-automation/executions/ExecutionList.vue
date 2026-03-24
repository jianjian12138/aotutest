<template>
  <BasePage title="执行记录">
    <template #actions><el-select v-model="projectId" placeholder="选择项目" style="width: 200px" @change="onProjectChange">
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select></template>
    
    <div class="main-content">
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-form :inline="true" :model="searchForm" class="demo-form-inline">
          <el-form-item>
            <el-input
              v-model="searchForm.keyword"
              placeholder="搜索执行记录..."
              clearable
              style="width: 300px"
              @keyup.enter="handleSearch"
            >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
  
              </el-input>
          </el-form-item>
          <el-form-item>
            <el-select v-model="searchForm.status" placeholder="状态" clearable style="width: 120px">
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
              <el-option label="运行中" value="running" />
              <el-option label="等待中" value="pending" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-date-picker
              v-model="searchForm.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 240px"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="resetSearch">
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="action-buttons">
          <el-button type="danger" :disabled="selectedIds.length === 0" @click="handleBatchDelete">
            <el-icon><Delete /></el-icon>
            批量删除
          </el-button>
        </div>
      </div>

      <!-- 执行记录列表 -->
      <el-table
        v-loading="loading"
        :data="executions"
        style="width: 100%"
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column prop="id" label="ID" width="80" align="center" sortable />
        <el-table-column prop="test_case_name" label="测试用例/套件" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="test-info">
              <el-tag size="small" :type="row.type === 'suite' ? 'warning' : 'info'">
                {{ row.type === 'suite' ? '套件' : '用例' }}
              </el-tag>
              <span class="test-name">{{ row.test_case_name || row.test_suite_name || '未命名' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="browser" label="浏览器" width="100" align="center">
          <template #default="{ row }">
            <div class="browser-info" v-if="row.browser">
              <el-icon><component :is="getBrowserIcon(row.browser)" /></el-icon>
              <span>{{ row.browser }}</span>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100" align="center">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="执行时间" width="180" align="center" sortable>
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="executor" label="执行人" width="120" align="center" />
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button link type="warning" size="small" @click="viewReport(row)" v-if="row.report_url">
              <el-icon><Document /></el-icon>
              报告
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="执行详情"
      width="70%"
      destroy-on-close
    >
      <div v-if="currentExecution" class="execution-detail">
        <el-descriptions border :column="2">
          <el-descriptions-item label="执行ID">{{ currentExecution.id }}</el-descriptions-item>
          <el-descriptions-item label="项目">{{ currentExecution.project_name }}</el-descriptions-item>
          <el-descriptions-item label="测试名称">{{ currentExecution.test_case_name || currentExecution.test_suite_name }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag size="small" :type="currentExecution.type === 'suite' ? 'warning' : 'info'">
              {{ currentExecution.type === 'suite' ? '测试套件' : '测试用例' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentExecution.status)">
              {{ getStatusText(currentExecution.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="浏览器">{{ currentExecution.browser }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(currentExecution.start_time) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatTime(currentExecution.end_time) }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ formatDuration(currentExecution.duration) }}</el-descriptions-item>
          <el-descriptions-item label="执行人">{{ currentExecution.executor }}</el-descriptions-item>
        </el-descriptions>

        <div class="error-info" v-if="currentExecution.error_message">
          <div class="error-header">
            <h3>错误信息</h3>
            <el-tag type="danger">Error</el-tag>
          </div>
          <pre class="error-content">{{ currentExecution.error_message }}</pre>
        </div>

        <div class="logs-section" v-if="currentExecution.logs && currentExecution.logs.length">
          <h3>执行日志</h3>
          <div class="log-container">
            <div v-for="(log, index) in currentExecution.logs" :key="index" class="log-item" :class="log.level">
              <span class="log-time">{{ formatTime(log.timestamp) }}</span>
              <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
              <span class="log-msg">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Delete, View, Document,
  ChromeFilled, Monitor
} from '@element-plus/icons-vue'
import {
  getUiProjects,
  getTestExecutions,
  deleteTestExecution,
  batchDeleteTestExecutions
} from '@/api/ui_automation'

// 响应式数据
const projects = ref([])
const projectId = ref('')
const executions = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const selectedIds = ref([])

const searchForm = reactive({
  keyword: '',
  status: '',
  dateRange: []
})

const detailVisible = ref(false)
const currentExecution = ref(null)

// 方法定义
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    projects.value = response.data.results || response.data
    if (projects.value.length > 0) {
      projectId.value = projects.value[0].id
      loadExecutions()
    }
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  }
}

const loadExecutions = async () => {
  if (!projectId.value) return

  try {
    loading.value = true
    const params = {
      project: projectId.value,
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchForm.keyword,
      status: searchForm.status,
      start_date: searchForm.dateRange?.[0],
      end_date: searchForm.dateRange?.[1]
    }

    const response = await getTestExecutions(params)
    executions.value = response.data.results || response.data
    total.value = response.data.count || executions.value.length
  } catch (error) {
    ElMessage.error('获取执行记录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const onProjectChange = () => {
  currentPage.value = 1
  loadExecutions()
}

const handleSearch = () => {
  currentPage.value = 1
  loadExecutions()
}

const resetSearch = () => {
  searchForm.keyword = ''
  searchForm.status = ''
  searchForm.dateRange = []
  handleSearch()
}

const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

const handleSizeChange = (val) => {
  pageSize.value = val
  loadExecutions()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadExecutions()
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该执行记录吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteTestExecution(row.id)
      ElMessage.success('删除成功')
      loadExecutions()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const handleBatchDelete = () => {
  ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 条记录吗？`, '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await batchDeleteTestExecutions({ ids: selectedIds.value })
      ElMessage.success('批量删除成功')
      selectedIds.value = []
      loadExecutions()
    } catch (error) {
      ElMessage.error('批量删除失败')
    }
  })
}

const viewDetail = (row) => {
  currentExecution.value = row
  detailVisible.value = true
}

const viewReport = (row) => {
  if (row.report_url) {
    window.open(row.report_url, '_blank')
  } else {
    ElMessage.warning('暂无报告')
  }
}

// 辅助方法
const getStatusType = (status) => {
  const map = {
    'success': 'success',
    'failed': 'danger',
    'running': 'primary',
    'pending': 'info',
    'error': 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'success': '成功',
    'failed': '失败',
    'running': '运行中',
    'pending': '等待中',
    'error': '错误'
  }
  return map[status] || status
}

const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString()
}

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.floor(seconds % 60)
  return `${minutes}分${remainingSeconds}秒`
}

const getBrowserIcon = (browser) => {
  if (!browser) return Monitor
  if (browser.toLowerCase().includes('chrome')) return ChromeFilled
  return Monitor
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.main-content {
  padding: 20px;
}

.search-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.test-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.test-name {
  font-weight: 500;
}

.browser-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.execution-detail {
  padding: 10px;
}

.error-info {
  margin-top: 20px;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 15px;
  background-color: #fef0f0;
}

.error-header h3 {
  margin: 0;
  color: #f56c6c;
}

.error-content {
  margin-top: 10px;
  white-space: pre-wrap;
  word-break: break-all;
  color: #f56c6c;
  font-family: monospace;
  background: rgba(255, 255, 255, 0.5);
  padding: 10px;
  border-radius: 4px;
}

.logs-section {
  margin-top: 20px;
}

.log-container {
  margin-top: 10px;
  background-color: #1e1e1e;
  border-radius: 4px;
  padding: 10px;
  height: 300px;
  overflow-y: auto;
  font-family: monospace;
}

.log-item {
  display: flex;
  gap: 10px;
  padding: 2px 0;
  font-size: 12px;
  color: #d4d4d4;
}

.log-item.error {
  color: #f56c6c;
}

.log-item.warning {
  color: #e6a23c;
}

.log-item.info {
  color: #909399;
}

.log-time {
  color: #606266;
  min-width: 140px;
}

.log-level {
  font-weight: bold;
  min-width: 60px;
}

.log-msg {
  white-space: pre-wrap;
  word-break: break-all;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .search-bar {
    flex-direction: column;
    gap: 10px;
  }
  
  .search-bar .el-form-item {
    margin-right: 0;
    margin-bottom: 10px;
    width: 100%;
  }
  
  .search-bar .el-input,
  .search-bar .el-select,
  .search-bar .el-date-editor {
    width: 100% !important;
  }
  
  .action-buttons {
    width: 100%;
    display: flex;
    justify-content: flex-end;
  }
  
  .error-content {
    font-size: 12px;
    padding: 5px;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
  }

  .error-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 15px;
    padding-bottom: 15px;
    border-bottom: 1px solid #f5f5f5;
  }

  .error-header .el-tag {
    font-size: 16px;
    padding: 10px 15px;
    font-weight: 600;
  }
}
</style>