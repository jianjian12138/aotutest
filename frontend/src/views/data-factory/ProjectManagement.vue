<template>
  <div class="project-container">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">数据项目管理</h2>
          <el-button type="primary" @click="handleCreateProject">
            <el-icon><Plus /></el-icon>
            新建项目
          </el-button>
        </div>
      </template>
      
      <div class="content">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索项目名称或描述"
            clearable
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select
            v-model="statusFilter"
            placeholder="筛选项目状态"
            clearable
            class="filter-select"
          >
            <el-option label="全部" value="" />
            <el-option label="启用" value="ACTIVE" />
            <el-option label="禁用" value="INACTIVE" />
            <el-option label="已删除" value="DELETED" />
          </el-select>
        </div>
        
        <!-- 项目列表 -->
        <el-table
          v-loading="loading"
          :data="filteredProjects"
          style="width: 100%"
          border
          stripe
          :default-sort="{ prop: 'created_at', order: 'descending' }"
        >
          <el-table-column prop="name" label="项目名称" min-width="180" />
          <el-table-column prop="description" label="项目描述" min-width="250" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag
                :type="scope.row.status === 'ACTIVE' ? 'success' : (scope.row.status === 'INACTIVE' ? 'warning' : 'danger')"
              >
                {{ scope.row.status === 'ACTIVE' ? '启用' : (scope.row.status === 'INACTIVE' ? '禁用' : '已删除') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_by.username" label="创建人" width="120" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                @click="handleViewProject(scope.row)"
                :disabled="scope.row.status === 'DELETED'"
              >
                查看
              </el-button>
              <el-button
                size="small"
                @click="handleEditProject(scope.row)"
                :disabled="scope.row.status === 'DELETED'"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                :type="scope.row.status === 'ACTIVE' ? 'warning' : 'success'"
                @click="handleToggleStatus(scope.row)"
                :disabled="scope.row.status === 'DELETED'"
              >
                {{ scope.row.status === 'ACTIVE' ? '禁用' : '启用' }}
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
            :total="filteredProjects.length"
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
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import router from '@/router'
import api from '@/utils/api'

// 状态管理
const loading = ref(false)
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// 项目数据
const projects = ref([])

// 过滤后的项目
const filteredProjects = computed(() => {
  let result = [...projects.value]
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(project => 
      project.name.toLowerCase().includes(keyword) ||
      project.description.toLowerCase().includes(keyword)
    )
  }
  
  // 状态过滤
  if (statusFilter.value) {
    result = result.filter(project => project.status === statusFilter.value)
  }
  
  return result
})

// 分页后的项目
const paginatedProjects = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredProjects.value.slice(start, end)
})

// 加载项目数据
const loadProjects = async () => {
  loading.value = true
  
  try {
    // 使用真实API调用
    const response = await api.get('/data-factory/projects/')
    projects.value = response.data.results || response.data
  } catch (error) {
    console.error('加载项目失败:', error)
    ElMessage.error('加载项目失败')
  } finally {
    loading.value = false
  }
}

// 新建项目
const handleCreateProject = () => {
  ElMessage.success('新建项目功能已触发')
  // 这里可以跳转到新建项目页面
  // router.push('/data-factory/projects/create')
}

// 查看项目
const handleViewProject = (project) => {
  ElMessage.success(`查看项目: ${project.name}`)
  // 这里可以跳转到项目详情页面
  // router.push(`/data-factory/projects/${project.id}`)
}

// 编辑项目
const handleEditProject = (project) => {
  ElMessage.success(`编辑项目: ${project.name}`)
  // 这里可以跳转到编辑项目页面
  // router.push(`/data-factory/projects/${project.id}/edit`)
}

// 切换项目状态
const handleToggleStatus = (project) => {
  const newStatus = project.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  project.status = newStatus
  ElMessage.success(`项目${newStatus === 'ACTIVE' ? '已启用' : '已禁用'}`)
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
  loadProjects()
})
</script>

<style scoped>
/* 页面特定样式 */
.page-container {
  padding: 0;
  display: flex;
  flex-direction: column;

  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}
.project-container {
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

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>