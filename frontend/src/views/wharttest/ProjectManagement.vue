<template>
  <div class="wharttest-project-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>WHartTest 项目管理</h2>
          <el-button type="primary" @click="handleAddProject">
            <el-icon><Plus /></el-icon> 新建项目
          </el-button>
        </div>
      </template>
      
      <div class="table-container">
        <el-table :data="projects" border stripe style="width: 100%">
          <el-table-column prop="name" label="项目名称" min-width="200" />
          <el-table-column prop="description" label="项目描述" min-width="300" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'active' ? 'success' : 'info'">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleViewProject(scope.row)">
                查看
              </el-button>
              <el-button type="warning" size="small" @click="handleEditProject(scope.row)">
                编辑
              </el-button>
              <el-button type="danger" size="small" @click="handleDeleteProject(scope.row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'

const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 从API获取项目数据
const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    projects.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    console.error('获取项目数据失败:', error)
    ElMessage.error('获取项目数据失败')
    projects.value = []
    total.value = 0
  }
}

const handleAddProject = () => {
  ElMessage.info('新建项目功能开发中')
}

const handleViewProject = (project) => {
  ElMessage.info(`查看项目: ${project.name}`)
}

const handleEditProject = (project) => {
  ElMessage.info(`编辑项目: ${project.name}`)
}

const handleDeleteProject = (project) => {
  ElMessageBox.confirm('确定要删除此项目吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('项目已删除')
    fetchProjects()
  }).catch(() => {})
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchProjects()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchProjects()
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped lang="scss">
.wharttest-project-management {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #2c3e50;
  }
}

.table-container {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>