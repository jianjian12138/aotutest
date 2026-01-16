<template>
  <div class="reports">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>测试报告</h2>
          <el-button type="primary" @click="handleGenerateReport">
            <el-icon><Plus /></el-icon>
            生成报告
          </el-button>
        </div>
      </template>
      
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
          :total="totalReports"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { Search, View, Download, Share, Plus } from '@element-plus/icons-vue'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const reportTypeFilter = ref('')
const dateRange = ref([])

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20
})
const totalReports = ref(25)

// 报告数据
const reports = ref([
  {
    id: 1,
    name: '电商网站安全扫描报告',
    type: 'scan',
    status: 'completed',
    generated_by: 'admin',
    generated_at: '2026-01-10 15:45:00',
    scan_task_id: 1,
    vulnerability_count: 15
  },
  {
    id: 2,
    name: '测试网站快速扫描报告',
    type: 'scan',
    status: 'completed',
    generated_by: 'testuser',
    generated_at: '2026-01-11 09:30:00',
    scan_task_id: 2,
    vulnerability_count: 8
  },
  {
    id: 3,
    name: '内部系统安全合规报告',
    type: 'compliance',
    status: 'completed',
    generated_by: 'admin',
    generated_at: '2026-01-11 16:00:00',
    scan_task_id: 3,
    vulnerability_count: 5
  },
  {
    id: 4,
    name: 'API服务漏洞报告',
    type: 'vulnerability',
    status: 'completed',
    generated_by: 'testuser',
    generated_at: '2026-01-12 10:20:00',
    scan_task_id: 4,
    vulnerability_count: 12
  },
  {
    id: 5,
    name: '管理后台安全审计报告',
    type: 'scan',
    status: 'completed',
    generated_by: 'admin',
    generated_at: '2026-01-12 15:45:00',
    scan_task_id: 5,
    vulnerability_count: 7
  }
])

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
  ElMessage.info('搜索功能开发中')
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewReport(row)
}

// 查看报告
const handleViewReport = (row) => {
  router.push(`/strix-security/reports/${row.id}`)
}

// 下载报告
const handleDownloadReport = (row) => {
  ElNotification({
    title: '提示',
    message: `开始下载报告：${row.name}`,
    type: 'success'
  })
}

// 分享报告
const handleShareReport = (row) => {
  ElMessage.success('报告分享功能开发中')
}

// 生成报告
const handleGenerateReport = () => {
  ElMessage.success('报告生成功能开发中')
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
.reports {
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

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>