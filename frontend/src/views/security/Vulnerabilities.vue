<template>
  <BasePage title="漏洞管理">
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入漏洞名称或描述"
              prefix-icon="Search"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="severityFilter"
              placeholder="漏洞级别"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option label="高危" value="high" />
              <el-option label="中危" value="medium" />
              <el-option label="低危" value="low" />
              <el-option label="信息" value="info" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="statusFilter"
              placeholder="处理状态"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option label="未处理" value="unhandled" />
              <el-option label="处理中" value="processing" />
              <el-option label="已修复" value="fixed" />
              <el-option label="已忽略" value="ignored" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
          </el-col>
        </el-row>
      </div>
      
      <!-- 漏洞统计 -->
      <div class="vulnerability-stats" style="margin-bottom: 20px;">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="stat-item">
                <div class="stat-number">{{ totalVulnerabilities }}</div>
                <div class="stat-label">总漏洞数</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="high-severity">
              <div class="stat-item">
                <div class="stat-number">{{ highVulnerabilities }}</div>
                <div class="stat-label">高危漏洞</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="medium-severity">
              <div class="stat-item">
                <div class="stat-number">{{ mediumVulnerabilities }}</div>
                <div class="stat-label">中危漏洞</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="low-severity">
              <div class="stat-item">
                <div class="stat-number">{{ lowVulnerabilities }}</div>
                <div class="stat-label">低危漏洞</div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
      
      <!-- 漏洞列表 -->
      <el-table
        :data="vulnerabilities"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="漏洞ID" width="100" />
        <el-table-column prop="name" label="漏洞名称" />
        <el-table-column prop="severity" label="漏洞级别" width="120">
          <template #default="scope">
            <el-tag
              :type="getSeverityTagType(scope.row.severity)"
              size="small"
            >
              {{ getSeverityText(scope.row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target" label="受影响目标" show-overflow-tooltip />
        <el-table-column prop="detected_at" label="发现时间" width="180" />
        <el-table-column prop="status" label="处理状态" width="120">
          <template #default="scope">
            <el-tag
              :type="getStatusTagType(scope.row.status)"
              size="small"
            >
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scan_task_id" label="所属任务" width="120" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewVulnerability(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="primary" @click="handleFixVulnerability(scope.row)">
              <el-icon><EditPen /></el-icon>
              处理
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalVulnerabilities"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
     </div>

  </BasePage>
</template>
<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Search, View, EditPen, Download } from '@element-plus/icons-vue'
import { 
  getVulnerabilities, 
  updateVulnerability, 
  getSecurityDashboardStats 
} from '@/api/security'
import api from '@/utils/api'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const severityFilter = ref('')
const statusFilter = ref('')

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

const loading = ref(false)
const vulnerabilities = ref([])
const stats = ref({
  total: 0,
  high: 0,
  medium: 0,
  low: 0
})

// 获取漏洞列表
const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value,
      severity: severityFilter.value,
      status: statusFilter.value
    }
    
    const response = await getVulnerabilities(params)
    vulnerabilities.value = response.data?.results || []
    pagination.total = response.data?.count || 0
  } catch (error) {
    ElMessage.error('获取漏洞列表失败')
  } finally {
    loading.value = false
  }
}

// 获取统计数据
const fetchStats = async () => {
  try {
    const response = await getSecurityDashboardStats()
    const data = response.data || response
    stats.value = {
      total: data.total_vulnerabilities,
      high: (data.vulnerability_stats?.high || 0) + (data.vulnerability_stats?.critical || 0),
      medium: data.vulnerability_stats?.medium || 0,
      low: (data.vulnerability_stats?.low || 0) + (data.vulnerability_stats?.info || 0)
    }
  } catch (error) {
    console.error('获取统计数据失败', error)
  }
}

// 统计数据
const totalVulnerabilities = computed(() => stats.value.total)
const highVulnerabilities = computed(() => stats.value.high)
const mediumVulnerabilities = computed(() => stats.value.medium)
const lowVulnerabilities = computed(() => stats.value.low)

// 获取漏洞级别标签类型
const getSeverityTagType = (severity) => {
  const typeMap = {
    CRITICAL: 'danger',
    HIGH: 'danger',
    MEDIUM: 'warning',
    LOW: 'info',
    INFO: 'primary'
  }
  return typeMap[severity] || 'info'
}

// 获取漏洞级别文本
const getSeverityText = (severity) => {
  const textMap = {
    CRITICAL: '严重',
    HIGH: '高危',
    MEDIUM: '中危',
    LOW: '低危',
    INFO: '信息'
  }
  return textMap[severity] || severity
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    UNHANDLED: 'danger',
    PROCESSING: 'warning',
    FIXED: 'success',
    IGNORED: 'info'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    UNHANDLED: '未处理',
    PROCESSING: '处理中',
    FIXED: '已修复',
    IGNORED: '已忽略'
  }
  return textMap[status] || status
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchData()
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewVulnerability(row)
}

// 查看漏洞
const handleViewVulnerability = (row) => {
  ElMessageBox.alert(`
    <p><strong>漏洞名称:</strong> ${row.name}</p>
    <p><strong>描述:</strong> ${row.description || '暂无描述'}</p>
    <p><strong>修复建议:</strong> ${row.solution || '暂无建议'}</p>
  `, '漏洞详情', {
    dangerouslyUseHTMLString: true
  })
}

// 处理漏洞
const handleFixVulnerability = async (row) => {
  try {
    await updateVulnerability(row.id, {
      status: 'PROCESSING'
    })
    ElMessage.success('已标记为处理中')
    fetchData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 导出漏洞
const handleExport = async () => {
  try {
    const response = await api.get('/strix-security/vulnerabilities/export/', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'vulnerabilities.csv')
    document.body.appendChild(link)
    link.click()
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchData()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchData()
}

onMounted(() => {
  fetchData()
  fetchStats()
})
</script>

<style scoped>

.vulnerabilities {
  padding: 0px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-filter {
  margin-bottom: 20px;
  padding: 20px 0;
  background-color: #fafafa;
  border-radius: 8px;
}

.vulnerability-stats {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 8px;
}

.stat-label {
  color: #666;
  font-size: 14px;
}

.high-severity .stat-number {
  color: #f56c6c;
}

.medium-severity .stat-number {
  color: #e6a23c;
}

.low-severity .stat-number {
  color: #67c23a;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>