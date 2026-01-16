<template>
  <div class="wharttest-config-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>WHartTest 配置管理</h2>
          <el-button type="primary" @click="handleAddConfig">
            <el-icon><Plus /></el-icon> 新建配置
          </el-button>
        </div>
      </template>
      
      <div class="table-container">
        <el-table :data="configs" border stripe style="width: 100%">
          <el-table-column prop="name" label="配置名称" min-width="200" />
          <el-table-column prop="key" label="配置键" min-width="200" />
          <el-table-column prop="value" label="配置值" min-width="300" show-overflow-tooltip />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'active' ? 'success' : 'info'">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleViewConfig(scope.row)">
                查看
              </el-button>
              <el-button type="warning" size="small" @click="handleEditConfig(scope.row)">
                编辑
              </el-button>
              <el-button type="danger" size="small" @click="handleDeleteConfig(scope.row)">
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

const configs = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 从API获取配置数据
const fetchConfigs = async () => {
  try {
    const response = await api.get('/configs/', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    configs.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    console.error('获取配置数据失败:', error)
    ElMessage.error('获取配置数据失败')
    configs.value = []
    total.value = 0
  }
}

const handleAddConfig = () => {
  ElMessage.info('新建配置功能开发中')
}

const handleViewConfig = (config) => {
  ElMessage.info(`查看配置: ${config.name}`)
}

const handleEditConfig = (config) => {
  ElMessage.info(`编辑配置: ${config.name}`)
}

const handleDeleteConfig = (config) => {
  ElMessageBox.confirm('确定要删除此配置吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('配置已删除')
    fetchConfigs()
  }).catch(() => {})
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchConfigs()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchConfigs()
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped lang="scss">
.wharttest-config-management {
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