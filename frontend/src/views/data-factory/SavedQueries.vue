<template>
  <div class="saved-queries-container">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">保存查询管理</h2>
        </div>
      </template>
      
      <div class="content">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索查询名称或描述"
            clearable
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select
            v-model="projectFilter"
            placeholder="筛选项目"
            clearable
            class="filter-select"
          >
            <el-option label="全部" value="" />
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </div>
        
        <!-- 保存查询列表 -->
        <el-table
          v-loading="loading"
          :data="filteredQueries"
          style="width: 100%"
          border
          stripe
          :default-sort="{ prop: 'created_at', order: 'descending' }"
        >
          <el-table-column prop="name" label="查询名称" min-width="180" />
          <el-table-column prop="description" label="查询描述" min-width="250" />
          <el-table-column prop="project.name" label="所属项目" width="180">
            <template #default="scope">
              {{ scope.row.project?.name || '无' }}
            </template>
          </el-table-column>
          <el-table-column prop="natural_language" label="自然语言" min-width="200" show-overflow-tooltip />
          <el-table-column label="SQL语句" min-width="250">
            <template #default="scope">
              <el-tooltip placement="top" :content="scope.row.sql || ''">
                <span class="sql-preview">{{ (scope.row.sql || '').substring(0, 50) }}{{ (scope.row.sql || '').length > 50 ? '...' : '' }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="created_by.username" label="创建人" width="120">
            <template #default="scope">
              {{ scope.row.created_by?.username || '无' }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                @click="handleViewQuery(scope.row)"
              >
                查看
              </el-button>
              <el-button
                size="small"
                @click="handleEditQuery(scope.row)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                type="success"
                @click="handleExecuteQuery(scope.row)"
              >
                执行
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="handleDeleteQuery(scope.row)"
              >
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
            :total="filteredQueries.length"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import router from '@/router'
import { getSavedQueries } from '@/api/data-factory'

// 状态管理
const loading = ref(false)
const searchKeyword = ref('')
const projectFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// 项目数据（用于筛选）
const projects = ref([
  { id: 1, name: '电商平台数据分析' },
  { id: 2, name: '用户行为分析' },
  { id: 3, name: '订单数据仓库' },
  { id: 4, name: '商品库存监控' },
  { id: 5, name: '广告效果分析' }
])

// 查询数据
const queries = ref([])

// 过滤后的查询
const filteredQueries = computed(() => {
  let result = [...queries.value]
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(query => 
      query.name.toLowerCase().includes(keyword) ||
      query.description.toLowerCase().includes(keyword) ||
      query.natural_language.toLowerCase().includes(keyword) ||
      query.sql.toLowerCase().includes(keyword)
    )
  }
  
  // 项目过滤
  if (projectFilter.value) {
    result = result.filter(query => query.project.id === projectFilter.value)
  }
  
  return result
})

// 加载查询数据
const loadQueries = async () => {
  loading.value = true
  
  try {
    // 调用真实API
    const response = await getSavedQueries()
    // 更健壮的响应处理
    if (response && response.data) {
      queries.value = Array.isArray(response.data.results) ? response.data.results : 
                     Array.isArray(response.data) ? response.data : []
    } else {
      queries.value = []
    }
    loading.value = false
  } catch (error) {
    console.error('加载查询失败:', error)
    queries.value = [] // 确保数据是数组格式
    ElMessage.error('加载查询失败')
    loading.value = false
  }
}

// 查看查询
const handleViewQuery = (query) => {
  ElMessage.success(`查看查询: ${query.name}`)
  // 这里可以跳转到查询详情页面
  // router.push(`/data-factory/saved-queries/${query.id}`)
}

// 编辑查询
const handleEditQuery = (query) => {
  ElMessage.success(`编辑查询: ${query.name}`)
  // 这里可以跳转到编辑查询页面
  // router.push(`/data-factory/saved-queries/${query.id}/edit`)
}

// 执行查询
const handleExecuteQuery = (query) => {
  ElMessage.success(`执行查询: ${query.name}`)
  // 这里可以跳转到执行查询页面或弹窗
}

// 删除查询
const handleDeleteQuery = (query) => {
  ElMessageBox.confirm('确定要删除这个查询吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = queries.value.indexOf(query)
    if (index > -1) {
      queries.value.splice(index, 1)
      ElMessage.success('查询已删除')
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

// 分页事件处理
const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
}

const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
}

// 组件挂载时加载数据
onMounted(() => {
  loadQueries()
})
</script>

<style scoped>
/* 页面特定样式 */
.page-container {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}
.saved-queries-container {
  width: 100%;
}

.page-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.content {
  padding: 20px 0;
}

.search-filter {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  align-items: center;
}

.search-input {
  width: 300px;
}

.filter-select {
  width: 180px;
}

.sql-preview {
  color: #1890ff;
  cursor: pointer;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>