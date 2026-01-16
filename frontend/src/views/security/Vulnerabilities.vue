<template>
  <div class="vulnerabilities">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>漏洞管理</h2>
          <el-button type="primary" @click="handleExport">
            <el-icon><Download /></el-icon>
            导出漏洞
          </el-button>
        </div>
      </template>
      
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
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { Search, View, EditPen, Download } from '@element-plus/icons-vue'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const severityFilter = ref('')
const statusFilter = ref('')

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20
})

// 漏洞数据
const vulnerabilities = ref([
  {
    id: 1,
    name: 'SQL注入漏洞',
    severity: 'high',
    target: 'https://example.com/login',
    detected_at: '2026-01-10 14:30:00',
    status: 'unhandled',
    scan_task_id: 1
  },
  {
    id: 2,
    name: 'XSS跨站脚本漏洞',
    severity: 'medium',
    target: 'https://example.com/search',
    detected_at: '2026-01-10 14:35:00',
    status: 'processing',
    scan_task_id: 1
  },
  {
    id: 3,
    name: '弱密码策略',
    severity: 'medium',
    target: 'https://example.com/register',
    detected_at: '2026-01-10 14:40:00',
    status: 'fixed',
    scan_task_id: 1
  },
  {
    id: 4,
    name: '目录遍历漏洞',
    severity: 'high',
    target: 'https://example.com/files',
    detected_at: '2026-01-10 14:45:00',
    status: 'unhandled',
    scan_task_id: 1
  },
  {
    id: 5,
    name: '信息泄露',
    severity: 'low',
    target: 'https://example.com/.git/config',
    detected_at: '2026-01-10 14:50:00',
    status: 'ignored',
    scan_task_id: 1
  },
  {
    id: 6,
    name: 'CSRF漏洞',
    severity: 'medium',
    target: 'https://example.com/account',
    detected_at: '2026-01-11 09:15:00',
    status: 'unhandled',
    scan_task_id: 2
  },
  {
    id: 7,
    name: '服务器版本泄露',
    severity: 'info',
    target: 'https://example.com',
    detected_at: '2026-01-11 09:20:00',
    status: 'ignored',
    scan_task_id: 2
  },
  {
    id: 8,
    name: '不安全的HTTP头',
    severity: 'low',
    target: 'https://example.com',
    detected_at: '2026-01-11 09:25:00',
    status: 'processing',
    scan_task_id: 2
  },
  {
    id: 9,
    name: '命令注入漏洞',
    severity: 'high',
    target: 'https://api.example.com/exec',
    detected_at: '2026-01-12 10:00:00',
    status: 'unhandled',
    scan_task_id: 4
  },
  {
    id: 10,
    name: '未加密的敏感数据传输',
    severity: 'medium',
    target: 'https://api.example.com/user',
    detected_at: '2026-01-12 10:05:00',
    status: 'fixed',
    scan_task_id: 4
  }
])

// 统计数据
const totalVulnerabilities = computed(() => vulnerabilities.value.length)
const highVulnerabilities = computed(() => vulnerabilities.value.filter(v => v.severity === 'high').length)
const mediumVulnerabilities = computed(() => vulnerabilities.value.filter(v => v.severity === 'medium').length)
const lowVulnerabilities = computed(() => vulnerabilities.value.filter(v => v.severity === 'low' || v.severity === 'info').length)

// 获取漏洞级别标签类型
const getSeverityTagType = (severity) => {
  const typeMap = {
    high: 'danger',
    medium: 'warning',
    low: 'info',
    info: 'primary'
  }
  return typeMap[severity] || 'info'
}

// 获取漏洞级别文本
const getSeverityText = (severity) => {
  const textMap = {
    high: '高危',
    medium: '中危',
    low: '低危',
    info: '信息'
  }
  return textMap[severity] || severity
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    unhandled: 'danger',
    processing: 'warning',
    fixed: 'success',
    ignored: 'info'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    unhandled: '未处理',
    processing: '处理中',
    fixed: '已修复',
    ignored: '已忽略'
  }
  return textMap[status] || status
}

// 搜索
const handleSearch = () => {
  ElMessage.info('搜索功能开发中')
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewVulnerability(row)
}

// 查看漏洞
const handleViewVulnerability = (row) => {
  router.push(`/strix-security/vulnerabilities/${row.id}`)
}

// 处理漏洞
const handleFixVulnerability = (row) => {
  ElNotification({
    title: '提示',
    message: `开始处理漏洞：${row.name}`,
    type: 'success'
  })
}

// 导出漏洞
const handleExport = () => {
  ElMessage.success('漏洞导出功能开发中')
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.value.pageSize = size
}

const handleCurrentChange = (current) => {
  pagination.value.currentPage = current
}
</script>

<style scoped>
.vulnerabilities {
  padding: 20px;
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