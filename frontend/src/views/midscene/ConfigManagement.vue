<template>
  <div class="config-management-container">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header">
          <h2 class="page-title">Midscene配置管理</h2>
          <el-button type="primary" @click="handleCreateConfig">
            <el-icon><Plus /></el-icon>
            新建配置
          </el-button>
        </div>
      </template>
      
      <div class="content">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索配置名称或描述"
            clearable
            class="search-input"
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
          >
            <el-option label="全部" value="" />
            <el-option label="启用" value="ACTIVE" />
            <el-option label="禁用" value="INACTIVE" />
          </el-select>
        </div>
        
        <!-- 配置列表 -->
        <el-table
          v-loading="loading"
          :data="filteredConfigs"
          style="width: 100%"
          border
          stripe
          :default-sort="{ prop: 'name', order: 'ascending' }"
        >
          <el-table-column prop="name" label="配置名称" min-width="180" />
          <el-table-column prop="description" label="配置描述" min-width="250" show-overflow-tooltip />
          <el-table-column prop="browser" label="浏览器" width="120" />
          <el-table-column prop="engine" label="引擎" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag
                :type="scope.row.status === 'ACTIVE' ? 'success' : 'warning'"
              >
                {{ scope.row.status === 'ACTIVE' ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_by.username" label="创建人" width="120" />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
               {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="scope">
              <el-button
                size="small"
                @click="handleEditConfig(scope.row)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                :type="scope.row.status === 'ACTIVE' ? 'warning' : 'success'"
                @click="handleToggleStatus(scope.row)"
              >
                {{ scope.row.status === 'ACTIVE' ? '禁用' : '启用' }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="handleDeleteConfig(scope.row)"
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
            :total="filteredConfigs.length"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑配置' : '新建配置'"
      width="500px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入配置名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="浏览器" prop="browser">
          <el-select v-model="form.browser" placeholder="选择浏览器">
            <el-option label="Chrome" value="chrome" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="Edge" value="edge" />
          </el-select>
        </el-form-item>
        <el-form-item label="引擎" prop="engine">
          <el-select v-model="form.engine" placeholder="选择引擎">
            <el-option label="Playwright" value="playwright" />
            <el-option label="Puppeteer" value="puppeteer" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-switch
            v-model="form.status"
            active-value="ACTIVE"
            inactive-value="INACTIVE"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting">
            {{ isEditing ? '更新' : '创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import router from '@/router'
import { 
  getMidsceneConfigs, 
  createMidsceneConfig, 
  updateMidsceneConfig, 
  deleteMidsceneConfig 
} from '@/api/midscene'

// 状态管理
const loading = ref(false)
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const isEditing = ref(false)
const submitting = ref(false)
const formRef = ref(null)

// 表单数据
const form = ref({
  id: null,
  name: '',
  description: '',
  browser: 'chrome',
  engine: 'playwright',
  status: 'ACTIVE'
})

// 表单规则
const rules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  browser: [{ required: true, message: '请选择浏览器', trigger: 'change' }],
  engine: [{ required: true, message: '请选择引擎', trigger: 'change' }]
}

// 配置数据
const configs = ref([])

// 模拟配置数据 (Fallback)
const mockConfigs = [
  {
    id: 1,
    name: '默认配置',
    description: '默认的Midscene配置',
    browser: 'chrome',
    engine: 'playwright',
    status: 'ACTIVE',
    created_by: { username: 'admin' },
    created_at: '2023-11-15T10:30:00Z',
    updated_at: '2023-11-15T14:20:00Z'
  }
]

// 过滤后的配置
const filteredConfigs = computed(() => {
  let result = [...configs.value]
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(config => 
      config.name.toLowerCase().includes(keyword) ||
      config.description.toLowerCase().includes(keyword)
    )
  }
  
  // 状态过滤
  if (statusFilter.value) {
    result = result.filter(config => config.status === statusFilter.value)
  }
  
  return result
})

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}

// 加载配置数据
const loadConfigs = async () => {
  loading.value = true
  
  try {
    const res = await getMidsceneConfigs().catch(() => ({ data: { results: [] } }))
    configs.value = res.data.results || res.data || mockConfigs
  } catch (error) {
    console.error('加载配置失败:', error)
    configs.value = mockConfigs
  } finally {
    loading.value = false
  }
}

// 新建配置
const handleCreateConfig = () => {
  isEditing.value = false
  form.value = {
    id: null,
    name: '',
    description: '',
    browser: 'chrome',
    engine: 'playwright',
    status: 'ACTIVE'
  }
  dialogVisible.value = true
}

// 编辑配置
const handleEditConfig = (config) => {
  isEditing.value = true
  form.value = { ...config }
  dialogVisible.value = true
}

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      if (isEditing.value) {
        await updateMidsceneConfig(form.value.id, form.value)
        ElMessage.success('配置已更新')
      } else {
        await createMidsceneConfig(form.value)
        ElMessage.success('配置已创建')
      }
      dialogVisible.value = false
      loadConfigs()
    } catch (error) {
      ElMessage.error('保存失败: ' + (error.response?.data?.error || error.message))
    } finally {
      submitting.value = false
    }
  })
}

// 切换配置状态
const handleToggleStatus = async (config) => {
  const newStatus = config.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  try {
    await updateMidsceneConfig(config.id, { ...config, status: newStatus })
    config.status = newStatus
    ElMessage.success(`配置${newStatus === 'ACTIVE' ? '已启用' : '已禁用'}`)
  } catch (error) {
    ElMessage.error('状态更新失败')
  }
}

// 删除配置
const handleDeleteConfig = (config) => {
  ElMessageBox.confirm('确定要删除这个配置吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteMidsceneConfig(config.id)
      ElMessage.success('配置已删除')
      loadConfigs()
    } catch (error) {
      ElMessage.error('删除失败')
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
  loadConfigs()
})
</script>

<style scoped>
.config-management-container {
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
  font-size: 20px;
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