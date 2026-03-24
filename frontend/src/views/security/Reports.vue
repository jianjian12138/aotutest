<template>
  <BasePage title="测试报告">
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入报告名称或描述"
              prefix-icon="Search"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="reportTypeFilter"
              placeholder="报告类型"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option label="扫描报告" value="scan" />
              <el-option label="漏洞报告" value="vulnerability" />
              <el-option label="合规报告" value="compliance" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
            />
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
          </el-col>
        </el-row>
      </div>
      
      <!-- 报告列表 -->
      <el-table
        :data="reports"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="报告ID" width="100" />
        <el-table-column prop="name" label="报告名称" />
        <el-table-column prop="type" label="报告类型" width="120">
          <template #default="scope">
            <el-tag
              :type="getTypeTagType(scope.row.type)"
              size="small"
            >
              {{ getTypeText(scope.row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag
              :type="getStatusTagType(scope.row.status)"
              size="small"
            >
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="generated_by" label="生成人" width="120" />
        <el-table-column prop="generated_at" label="生成时间" width="180" />
        <el-table-column prop="scan_task_id" label="关联任务" width="120" />
        <el-table-column prop="vulnerability_count" label="漏洞数" width="120" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewReport(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="primary" @click="handleDownloadReport(scope.row)">
              <el-icon><Download /></el-icon>
              下载
            </el-button>
            <el-button size="small" type="warning" @click="handleShareReport(scope.row)">
              <el-icon><Share /></el-icon>
              分享
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
          :total="pagination.total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>

      <!-- 报告详情对话框 -->
      <el-dialog
        v-model="detailVisible"
        title="报告详情"
        width="700px"
      >
        <el-descriptions border :column="1">
          <el-descriptions-item label="报告名称">{{ currentReport.name }}</el-descriptions-item>
          <el-descriptions-item label="报告类型">
            <el-tag :type="getTypeTagType(currentReport.type)">
              {{ getTypeText(currentReport.type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(currentReport.status)">
              {{ getStatusText(currentReport.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="关联任务ID">{{ currentReport.scan_task_id }}</el-descriptions-item>
          <el-descriptions-item label="漏洞数量">{{ currentReport.vulnerability_count }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ currentReport.generated_at }}</el-descriptions-item>
          <el-descriptions-item label="详细结果">
            <div style="max-height: 300px; overflow-y: auto;">
              <pre>{{ JSON.stringify(currentReport.result, null, 2) }}</pre>
            </div>
          </el-descriptions-item>
        </el-descriptions>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="detailVisible = false">关闭</el-button>
            <el-button type="primary" @click="handleDownloadReport(currentReport)">下载</el-button>
          </span>
        </template>
      </el-dialog>
  </BasePage>
</template>
<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { Search, View, Download, Share, Plus } from '@element-plus/icons-vue'
import { getSecurityReports, getSecurityReportDetail, downloadSecurityReport } from '@/api/security'
import api from '@/utils/api'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const reportTypeFilter = ref('')
const dateRange = ref([])

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 数据
const reports = ref([])
const loading = ref(false)

// 详情对话框
const detailVisible = ref(false)
const currentReport = ref({})

// 获取报告列表
const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value,
      type: reportTypeFilter.value,
      start_date: dateRange.value?.[0],
      end_date: dateRange.value?.[1]
    }
    // Using security executions as reports
    const response = await getSecurityReports(params)
    reports.value = response.data?.results || []
    pagination.total = response.data?.count || 0
  } catch (error) {
    ElMessage.error('获取报告列表失败')
  } finally {
    loading.value = false
  }
}

// 获取报告类型标签类型
const getTypeTagType = (type) => {
  const typeMap = {
    scan: 'primary',
    vulnerability: 'danger',
    compliance: 'success'
  }
  return typeMap[type] || 'info'
}

// 获取报告类型文本
const getTypeText = (type) => {
  const textMap = {
    scan: '扫描报告',
    vulnerability: '漏洞报告',
    compliance: '合规报告'
  }
  return textMap[type] || type
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    completed: 'success',
    generating: 'warning',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    completed: '已完成',
    generating: '生成中',
    failed: '失败'
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
  handleViewReport(row)
}

// 查看报告
const handleViewReport = async (row) => {
  try {
    const response = await getSecurityReportDetail(row.id)
    currentReport.value = response
    detailVisible.value = true
  } catch (error) {
    ElMessage.error('获取报告详情失败')
  }
}

// 下载报告
const handleDownloadReport = async (row) => {
  try {
    ElNotification({
      title: '提示',
      message: `开始下载报告：${row.name || row.id}`,
      type: 'info'
    })
    
    const response = await downloadSecurityReport(row.id)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `security_report_${row.id}.pdf`) // 假设是PDF
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

// 分享报告
const handleShareReport = (row) => {
  // 复制报告链接到剪贴板
  const reportUrl = `${window.location.origin}/security/reports/${row.id}`
  navigator.clipboard.writeText(reportUrl).then(() => {
    ElMessage.success('报告链接已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制链接失败')
  })
}

// 生成报告
const handleGenerateReport = () => {
  ElMessage.info('请在扫描任务中执行扫描以生成报告')
  router.push('/security/scan-tasks')
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
})
</script>

<style scoped>

.reports {
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

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>