<template>
  <div class="wharttest-execution-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>WHartTest 执行管理</h2>
          <el-button type="primary" @click="handleAddExecution">
            <el-icon><Plus /></el-icon> 新建执行
          </el-button>
        </div>
      </template>
      
      <div class="table-container">
        <el-table :data="executions" border stripe style="width: 100%">
          <el-table-column prop="name" label="执行名称" min-width="200" />
          <el-table-column prop="project_id" label="所属项目" width="150" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result" label="执行结果" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.result === 'success' ? 'success' : 'danger'">{{ scope.row.result }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_time" label="开始时间" width="180" />
          <el-table-column prop="end_time" label="结束时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleViewExecution(scope.row)">
                查看
              </el-button>
              <el-button type="warning" size="small" @click="handleRetryExecution(scope.row)">
                重试
              </el-button>
              <el-button type="danger" size="small" @click="handleAbortExecution(scope.row)">
                终止
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

const executions = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 从API获取执行数据
const fetchExecutions = async () => {
  try {
    const response = await api.get('/executions/', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    executions.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    console.error('获取执行数据失败:', error)
    ElMessage.error('获取执行数据失败')
    executions.value = []
    total.value = 0
  }
}

const getStatusType = (status) => {
  const statusMap = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'aborted': 'info'
  }
  return statusMap[status] || 'info'
}

const handleAddExecution = () => {
  ElMessage.info('新建执行功能开发中')
}

const handleViewExecution = (execution) => {
  ElMessage.info(`查看执行: ${execution.name}`)
}

const handleRetryExecution = (execution) => {
  ElMessage.info(`重试执行: ${execution.name}`)
}

const handleAbortExecution = (execution) => {
  ElMessageBox.confirm('确定要终止此执行吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('执行已终止')
    fetchExecutions()
  }).catch(() => {})
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchExecutions()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchExecutions()
}

onMounted(() => {
  fetchExecutions()
})
</script>

<style scoped lang="scss">
.wharttest-execution-management {
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