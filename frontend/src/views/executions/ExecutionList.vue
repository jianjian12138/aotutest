<template>
  <BasePage title="执行记录">
    
    
    <div class="card-container">
      <el-card shadow="hover">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchQuery"
            placeholder="搜索执行ID或名称"
            clearable
            class="search-input"
            style="width: 240px"
            @change="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
  
          </el-input>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>

        <!-- 执行列表 -->
        <el-table
          v-loading="loading"
          :data="executions"
          style="width: 100%"
          border
          stripe
        >
          <el-table-column prop="id" label="执行ID" width="100" />
          <el-table-column prop="name" label="执行名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_by" label="执行人" width="120" />
          <el-table-column prop="start_time" label="开始时间" width="180" />
          <el-table-column prop="end_time" label="结束时间" width="180" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="handleViewExecution(scope.row)">
                <el-icon><View /></el-icon>
                查看
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

  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, View } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
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
const executions = ref([])
const loading = ref(false)

// 获取执行列表
const fetchExecutions = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value
    }
    const response = await api.get('/executions/', { params })
    executions.value = response.data.results || []
    pagination.total = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取执行记录失败')
  } finally {
    loading.value = false
  }
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    stopped: 'warning'
  }
  return typeMap[status?.toLowerCase()] || 'info'
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchExecutions()
}

// 查看执行
const handleViewExecution = (row) => {
  router.push(`/executions/${row.id}`)
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchExecutions()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchExecutions()
}

onMounted(() => {
  fetchExecutions()
})
</script>

<style scoped>


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