<template>
  <div class="wharttest-task-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>WHartTest 任务管理</h2>
          <el-button type="primary" @click="handleAddTask">
            <el-icon><Plus /></el-icon> 新建任务
          </el-button>
        </div>
      </template>
      
      <div class="table-container">
        <el-table :data="tasks" border stripe style="width: 100%">
          <el-table-column prop="name" label="任务名称" min-width="200" />
          <el-table-column prop="project_id" label="所属项目" width="150" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.priority === 'high' ? 'danger' : scope.row.priority === 'medium' ? 'warning' : 'success'">
                {{ scope.row.priority }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleViewTask(scope.row)">
                查看
              </el-button>
              <el-button type="warning" size="small" @click="handleEditTask(scope.row)">
                编辑
              </el-button>
              <el-button type="danger" size="small" @click="handleDeleteTask(scope.row)">
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

const tasks = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 从API获取任务数据
const fetchTasks = async () => {
  try {
    const response = await api.get('/tasks/', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    tasks.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    console.error('获取任务数据失败:', error)
    ElMessage.error('获取任务数据失败')
    tasks.value = []
    total.value = 0
  }
}

const getStatusType = (status) => {
  const statusMap = {
    'active': 'success',
    'pending': 'info',
    'completed': 'success',
    'failed': 'danger',
    'suspended': 'warning'
  }
  return statusMap[status] || 'info'
}

const handleAddTask = () => {
  ElMessage.info('新建任务功能开发中')
}

const handleViewTask = (task) => {
  ElMessage.info(`查看任务: ${task.name}`)
}

const handleEditTask = (task) => {
  ElMessage.info(`编辑任务: ${task.name}`)
}

const handleDeleteTask = (task) => {
  ElMessageBox.confirm('确定要删除此任务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('任务已删除')
    fetchTasks()
  }).catch(() => {})
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchTasks()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchTasks()
}

onMounted(() => {
  fetchTasks()
})
</script>

<style scoped lang="scss">
.wharttest-task-management {
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