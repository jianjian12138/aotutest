<template>
  <div class="wharttest-integration-log-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">集成日志管理</h2>
        </div>
      </template>
      
      <div class="table-container">
        <el-table :data="logs" border stripe style="width: 100%">
          <el-table-column prop="id" label="日志ID" width="150" />
          <el-table-column prop="project_id" label="所属项目" width="150" />
          <el-table-column prop="execution_id" label="执行ID" width="150" />
          <el-table-column prop="log_type" label="日志类型" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.log_type === 'error' ? 'danger' : scope.row.log_type === 'warning' ? 'warning' : 'info'">
                {{ scope.row.log_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="日志消息" min-width="400" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleViewLog(scope.row)">
                查看详情
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
import { ElMessage } from 'element-plus'
import { getWHartTestIntegrationLogs } from '@/api/wharttest'

const logs = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 从API获取日志数据
const fetchLogs = async () => {
  try {
    const response = await getWHartTestIntegrationLogs({
      page: currentPage.value,
      page_size: pageSize.value
    })
    logs.value = response.data.results || response.results || []
    total.value = response.data.count || response.count || 0
  } catch (error) {
    console.error('获取日志数据失败:', error)
    ElMessage.error('获取日志数据失败')
    logs.value = []
    total.value = 0
  }
}

const handleViewLog = (log) => {
  ElMessage.info(`查看日志详情: ${log.id}`)
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchLogs()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchLogs()
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped lang="scss">
.wharttest-integration-log-management {
  padding: 0;
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
    font-size: 24px;
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