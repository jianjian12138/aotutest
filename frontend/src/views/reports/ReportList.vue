<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">测试报告</h1>
    </div>
    
    <div class="card-container">
      <el-card shadow="hover">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchQuery"
            placeholder="搜索报告名称"
            clearable
            class="search-input"
            style="width: 240px"
            @change="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>

        <!-- 报告列表 -->
        <el-table
          v-loading="loading"
          :data="reports"
          style="width: 100%"
          border
          stripe
        >
          <el-table-column prop="id" label="报告ID" width="100" />
          <el-table-column prop="name" label="报告名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="created_at" label="生成时间" width="180" />
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
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
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
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, View, Download } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import api from '@/utils/api'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 数据
const reports = ref([])
const loading = ref(false)

// 获取报告列表
const fetchReports = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value
    }
    const response = await api.get('/reports/', { params })
    reports.value = response.data.results || []
    pagination.total = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取报告列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchReports()
}

// 查看报告
const handleViewReport = (row) => {
  router.push(`/reports/${row.id}`)
}

// 下载报告
const handleDownloadReport = async (row) => {
  try {
    // Assuming download endpoint
    // await api.get(`/reports/${row.id}/download/`)
    ElNotification({
      title: '提示',
      message: `开始下载报告：${row.name}`,
      type: 'success'
    })
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchReports()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchReports()
}

onMounted(() => {
  fetchReports()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}
.page-header {
  margin-bottom: 20px;
}
.search-filter {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>