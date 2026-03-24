<template>
  <BasePage title="测试套件">
    
    
    <div class="card-container">
      <el-card shadow="hover">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchQuery"
            placeholder="搜索套件ID或名称"
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

        <!-- 套件列表 -->
        <el-table
          v-loading="loading"
          :data="testSuites"
          style="width: 100%"
          border
          stripe
        >
          <el-table-column prop="id" label="套件ID" width="100" />
          <el-table-column prop="name" label="套件名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column prop="created_by" label="创建人" width="120" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="handleViewTestSuite(scope.row)">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button size="small" type="primary" @click="handleEditTestSuite(scope.row)">
                <el-icon><EditPen /></el-icon>
                编辑
              </el-button>
              <el-button size="small" type="danger" @click="handleDeleteTestSuite(scope.row)">
                <el-icon><Delete /></el-icon>
                删除
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
  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, View, EditPen, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
const testSuites = ref([])
const loading = ref(false)

// 获取套件列表
const fetchTestSuites = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value
    }
    const response = await api.get('/testsuites/', { params })
    testSuites.value = response.data.results || []
    pagination.total = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取测试套件列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchTestSuites()
}

// 查看
const handleViewTestSuite = (row) => {
  router.push(`/testsuites/${row.id}`)
}

// 编辑
const handleEditTestSuite = (row) => {
  router.push(`/testsuites/${row.id}/edit`)
}

// 新建
const handleCreateTestSuite = () => {
  router.push('/testsuites/create')
}

// 删除
const handleDeleteTestSuite = (row) => {
  ElMessageBox.confirm('确定要删除这个测试套件吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/testsuites/${row.id}/`)
      ElMessage.success('删除成功')
      fetchTestSuites()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchTestSuites()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchTestSuites()
}

onMounted(() => {
  fetchTestSuites()
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