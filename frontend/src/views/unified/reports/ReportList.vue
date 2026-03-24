<template>
  <BasePage title="测试报告管理">
    <div class="unified-report-list-wrapper">
      <PremiumCard class="filter-card" padding="16px 24px">
        <div class="filter-section">
          <el-input
            v-model="searchText"
            placeholder="搜索报告名称"
            clearable
            style="width: 250px"
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-select
            v-model="testTypeFilter"
            placeholder="测试类型"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="API测试" value="API" />
            <el-option label="UI自动化" value="UI" />
            <el-option label="性能测试" value="PERFORMANCE" />
            <el-option label="通用测试" value="GENERAL" />
          </el-select>

          <el-select
            v-model="reportTypeFilter"
            placeholder="报告类型"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="测试套件" value="TEST_SUITE" />
            <el-option label="定时任务" value="SCHEDULED_TASK" />
            <el-option label="API请求" value="API_REQUEST" />
          </el-select>

          <el-select
            v-model="statusFilter"
            placeholder="状态"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="通过" value="PASSED" />
            <el-option label="失败" value="FAILED" />
            <el-option label="跳过" value="SKIPPED" />
          </el-select>

          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 260px"
            @change="handleFilter"
          />
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索报告</el-button>
        </div>
      </PremiumCard>

      <PremiumCard class="table-card" padding="0">
        <el-table class="premium-table" :data="reports" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="name" label="报告名称" min-width="200">
        <template #default="{ row }">
          <div style="display:flex;align-items:center;gap:6px">
            <el-link @click="viewReport(row.id)" type="primary">
              {{ row.name }}
            </el-link>
            <el-tooltip v-if="row.ai_analyzed_at" content="已完成 AI 智能分析" placement="top">
              <el-tag type="primary" size="small" effect="plain" style="cursor:default">
                <el-icon style="vertical-align:middle;margin-right:2px"><MagicStick /></el-icon>AI
              </el-tag>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="test_type" label="测试类型" width="120">
        <template #default="{ row }">
          <el-tag :type="getTestTypeTag(row.test_type)" size="small">
            {{ getTestTypeText(row.test_type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="project_name" label="所属项目" width="150" />

      <el-table-column prop="report_type" label="报告类型" width="120">
        <template #default="{ row }">
          {{ getReportTypeText(row.report_type) }}
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="测试结果" width="200">
        <template #default="{ row }">
          <div class="test-result">
            <span class="result-item passed">通过: {{ row.total_cases - row.failed_cases - row.skipped_cases }}</span>
            <span class="result-item failed">失败: {{ row.failed_cases }}</span>
            <span class="result-item skipped">跳过: {{ row.skipped_cases }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="pass_rate" label="通过率" width="100" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="row.pass_rate || 0"
            :color="getPassRateColor(row.pass_rate)"
            :stroke-width="12"
          />
        </template>
      </el-table-column>

      <el-table-column prop="duration" label="耗时(秒)" width="100" align="center">
        <template #default="{ row }">
          {{ row.duration?.toFixed(2) || '-' }}
        </template>
      </el-table-column>

      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-dropdown @command="(cmd) => handleExport(cmd, row)">
            <el-button size="small">
              导出<el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="html">HTML</el-dropdown-item>
                <el-dropdown-item command="pdf">PDF</el-dropdown-item>
                <el-dropdown-item command="excel">Excel</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button size="small" @click="viewReport(row.id)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

        <div class="pagination-footer">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next, jumper"
            @current-change="handlePageChange"
          />
        </div>
      </PremiumCard>
    </div>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { Search, ArrowDown, MagicStick } from '@element-plus/icons-vue'
import {
  getReportList,
  exportReport
} from '@/api/unified/report'

const router = useRouter()

// 数据
const reports = ref([])
const loading = ref(false)
const formRef = ref(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const searchText = ref('')
const testTypeFilter = ref('')
const reportTypeFilter = ref('')
const statusFilter = ref('')
const dateRange = ref([])

// 方法
const fetchReports = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      test_type: testTypeFilter.value,
      report_type: reportTypeFilter.value,
      status: statusFilter.value
    }

    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = formatDateForQuery(dateRange.value[0])
      params.end_date = formatDateForQuery(dateRange.value[1])
    }

    const response = await getReportList(params)
    const data = response.data || response
    reports.value = data.results || data || []
    total.value = data.count || 0
  } catch (error) {
    ElMessage.error('获取报告列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchReports()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchReports()
}

const handlePageChange = () => {
  fetchReports()
}

const viewReport = (id) => {
  router.push(`/unified/reports/${id}`)
}

const handleExport = async (format, row) => {
  try {
    const userStore = useUserStore()
    const token = userStore.accessToken
    
    // 使用原生的 fetch api 完全绕过 axios 拦截器
    const response = await fetch(`/api/reports/reports/${row.id}/fetch_report_file/?file_format=${format}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      throw new Error(`Export failed with status: ${response.status}`)
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // 设置正确的文件扩展名
    const extMap = {
      excel: 'xlsx',
      html: 'html',
      pdf: 'pdf'
    }
    const ext = extMap[format] || format
    link.download = `${row.name}.${ext}`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('报告导出成功')
  } catch (error) {
    ElMessage.error('报告导出失败')
    console.error(error)
  }
}


// 辅助方法
const getTestTypeTag = (type) => {
  const tags = {
    API: 'primary',
    UI: 'success',
    PERFORMANCE: 'warning',
    GENERAL: 'info'
  }
  return tags[type] || 'info'
}

const getTestTypeText = (type) => {
  const texts = {
    API: 'API测试',
    UI: 'UI自动化',
    PERFORMANCE: '性能测试',
    GENERAL: '通用测试'
  }
  return texts[type] || type
}

const getReportTypeText = (type) => {
  const texts = {
    TEST_SUITE: '测试套件',
    SCHEDULED_TASK: '定时任务',
    API_REQUEST: 'API请求'
  }
  return texts[type] || type
}

const getStatusType = (status) => {
  const types = {
    PASSED: 'success',
    FAILED: 'danger',
    SKIPPED: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    PASSED: '通过',
    FAILED: '失败',
    SKIPPED: '跳过'
  }
  return texts[status] || status
}

const getPassRateColor = (rate) => {
  if (rate >= 80) return '#67c23a'
  if (rate >= 60) return '#e6a23c'
  return '#f56c6c'
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const formatDateForQuery = (date) => {
  if (!date) return ''
  return new Date(date).toISOString().split('T')[0]
}

// 生命周期
onMounted(() => {
  fetchReports()
})
</script>

<style scoped>
.unified-report-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-section {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.test-result {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-item {
  font-size: 12px;
}

.result-item.passed {
  color: #67c23a;
}

.result-item.failed {
  color: #f56c6c;
}

.result-item.skipped {
  color: #909399;
}
</style>
