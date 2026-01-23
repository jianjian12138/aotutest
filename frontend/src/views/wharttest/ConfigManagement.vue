<template>
  <div class="wharttest-config-management">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">配置管理</h2>
          <el-button type="primary" @click="handleAddConfig">
            <el-icon><Plus /></el-icon>
            新建配置
          </el-button>
        </div>
      </template>
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索配置名称或键"
          clearable
          class="search-input"
          style="width: 240px"
          @change="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-select 
          v-model="statusFilter" 
          placeholder="筛选配置状态"
          clearable
          class="filter-select"
          style="width: 160px"
          @change="handleSearch"
        >
          <el-option label="活跃" value="active" />
          <el-option label="非活跃" value="inactive" />
        </el-select>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>
      
      <!-- 配置列表 -->
      <div class="table-container">
        <el-table
          v-loading="loading"
          :data="configs"
          style="width: 100%"
          border
          stripe
        >
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
      
      <!-- 分页 -->
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

      <!-- 创建/编辑配置对话框 -->
      <el-dialog
        v-model="dialogVisible"
        :title="dialogType === 'create' ? '新建配置' : '编辑配置'"
        width="500px"
      >
        <el-form :model="form" label-width="80px">
          <el-form-item label="配置名称" required>
            <el-input v-model="form.name" placeholder="请输入配置名称" />
          </el-form-item>
          <el-form-item label="配置键" required>
            <el-input v-model="form.key" placeholder="请输入配置键" :disabled="dialogType === 'edit'" />
          </el-form-item>
          <el-form-item label="配置值" required>
            <el-input v-model="form.value" type="textarea" placeholder="请输入配置值" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" placeholder="请输入描述" />
          </el-form-item>
          <el-form-item label="状态">
            <el-radio-group v-model="form.status">
              <el-radio label="active">活跃</el-radio>
              <el-radio label="inactive">非活跃</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="submitForm">确定</el-button>
          </span>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  getWHartTestConfigs, 
  createWHartTestConfig, 
  updateWHartTestConfig, 
  deleteWHartTestConfig 
} from '@/api/wharttest'

const configs = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loading = ref(false)
const searchKeyword = ref('')
const statusFilter = ref('')

// 对话框
const dialogVisible = ref(false)
const dialogType = ref('create')
const form = reactive({
  id: null,
  name: '',
  key: '',
  value: '',
  description: '',
  status: 'active'
})

// 从API获取配置数据
const fetchConfigs = async () => {
  loading.value = true
  try {
    const response = await getWHartTestConfigs({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchKeyword.value,
      status: statusFilter.value
    })
    configs.value = response.data.results || response.results || []
    total.value = response.data.count || response.count || 0
  } catch (error) {
    console.error('获取配置数据失败:', error)
    ElMessage.error('获取配置数据失败')
    configs.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handleAddConfig = () => {
  dialogType.value = 'create'
  form.id = null
  form.name = ''
  form.key = ''
  form.value = ''
  form.description = ''
  form.status = 'active'
  dialogVisible.value = true
}

const handleViewConfig = (config) => {
  dialogType.value = 'edit'
  fillForm(config)
  dialogVisible.value = true
}

const handleEditConfig = (config) => {
  dialogType.value = 'edit'
  fillForm(config)
  dialogVisible.value = true
}

const fillForm = (config) => {
  form.id = config.id
  form.name = config.name
  form.key = config.key
  form.value = config.value
  form.description = config.description
  form.status = config.status
}

const handleDeleteConfig = (config) => {
  ElMessageBox.confirm('确定要删除此配置吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteWHartTestConfig(config.id)
      ElMessage.success('配置已删除')
      fetchConfigs()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const submitForm = async () => {
  if (!form.name || !form.key || !form.value) {
    ElMessage.warning('请填写必要信息')
    return
  }

  try {
    const data = {
      name: form.name,
      key: form.key,
      value: form.value,
      description: form.description,
      status: form.status
    }

    if (dialogType.value === 'create') {
      await createWHartTestConfig(data)
      ElMessage.success('配置创建成功')
    } else {
      await updateWHartTestConfig(form.id, data)
      ElMessage.success('配置更新成功')
    }
    dialogVisible.value = false
    fetchConfigs()
  } catch (error) {
    ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
  }
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

// 监听搜索变化
const handleSearch = () => {
  currentPage.value = 1
  fetchConfigs()
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped lang="scss">
.wharttest-config-management {
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

.search-filter {
  margin-bottom: 20px;
  display: flex;
  gap: 15px;
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