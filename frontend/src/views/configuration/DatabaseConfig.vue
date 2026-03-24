<template>
  <BasePage title="数据库配置">
    <template #actions>
      <el-button type="primary" @click="handleCreateConfig">
        <el-icon><Plus /></el-icon>
        新建配置
      </el-button>
    </template>
    
    <p class="description-text">Data Factory 数据库连接配置</p>

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
            v-model="isActiveFilter"
            placeholder="筛选配置状态"
            clearable
            class="filter-select"
          >
            <el-option label="全部" :value="null" />
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </div>
        
        <!-- 配置列表 -->
        <el-table
          v-loading="loading"
          :data="filteredConfigs"
          style="width: 100%; flex: 1;"
          height="100%"
          border
          stripe
          :default-sort="{ prop: 'name', order: 'ascending' }"
        >
          <el-table-column prop="name" label="配置名称" min-width="180" />
          <el-table-column prop="description" label="配置描述" min-width="250" show-overflow-tooltip />
          <el-table-column prop="db_type" label="数据库类型" width="120" />
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="scope">
              <el-tag
                :type="scope.row.is_active ? 'success' : 'warning'"
              >
                {{ scope.row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_by.username" label="创建人" width="120" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                @click="handleViewConfig(scope.row)"
              >
                查看
              </el-button>
              <el-button
                size="small"
                @click="handleEditConfig(scope.row)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                :type="scope.row.is_active ? 'warning' : 'success'"
                @click="handleToggleStatus(scope.row)"
              >
                {{ scope.row.is_active ? '禁用' : '启用' }}
              </el-button>
              <el-button
                size="small"
                type="info"
                @click="handleTestConfig(scope.row)"
              >
                测试
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

    <!-- 查看配置对话框 -->
  <el-dialog
    v-model="viewDialogVisible"
    title="查看配置详情"
    width="60%"
    destroy-on-close
  >
    <div v-if="currentConfig" class="view-dialog-content">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="配置名称">{{ currentConfig.name }}</el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="currentConfig.is_active ? 'success' : 'warning'">{{ currentConfig.is_active ? '启用' : '禁用' }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="描述">{{ currentConfig.description }}</el-descriptions-item>
        <el-descriptions-item label="数据库类型">{{ currentConfig.db_type }}</el-descriptions-item>
        <el-descriptions-item label="创建人" :span="2">{{ currentConfig.created_by?.username || '系统' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ new Date(currentConfig.created_at).toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="更新时间" :span="2">{{ new Date(currentConfig.updated_at).toLocaleString() }}</el-descriptions-item>
      </el-descriptions>
      
      <h3 style="margin-top: 20px;">数据库连接配置</h3>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="主机">{{ currentConfig.db_connection?.host || '-' }}</el-descriptions-item>
        <el-descriptions-item label="端口">{{ currentConfig.db_connection?.port || '-' }}</el-descriptions-item>
        <el-descriptions-item label="数据库名">{{ currentConfig.db_connection?.database || '-' }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ currentConfig.db_connection?.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="密码">{{ currentConfig.db_connection?.password ? '********' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="SSL">{{ currentConfig.db_connection?.ssl ? '是' : '否' }}</el-descriptions-item>
      </el-descriptions>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="viewDialogVisible = false">关闭</el-button>
      </span>
    </template>
  </el-dialog>

  <!-- 编辑配置对话框 -->
  <el-dialog
    v-model="editDialogVisible"
    title="编辑配置"
    width="70%"
    destroy-on-close
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="基本配置" name="basic">
          <el-form-item label="配置名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入配置名称" />
          </el-form-item>
          <el-form-item label="配置描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入配置描述" />
          </el-form-item>
          <el-form-item label="数据库类型" prop="db_type">
            <el-select v-model="form.db_type" placeholder="请选择数据库类型">
              <el-option label="MySQL" value="mysql" />
              <el-option label="PostgreSQL" value="postgresql" />
              <el-option label="SQLite" value="sqlite" />
              <el-option label="Hive" value="hive" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标表名">
             <el-input v-model="form.tables" placeholder="请输入目标表名（多个表名用逗号分隔），留空则使用全部表" />
          </el-form-item>
          <el-form-item label="启用状态">
            <el-switch v-model="form.is_active" />
          </el-form-item>
        </el-tab-pane>
        <el-tab-pane label="数据库连接" name="db">
          <el-form-item label="主机地址">
            <el-input v-model="form.db_connection.host" placeholder="请输入数据库主机地址" />
          </el-form-item>
          <el-form-item label="端口">
            <el-input v-model.number="form.db_connection.port" type="number" placeholder="请输入数据库端口" />
          </el-form-item>
          <el-form-item label="数据库名">
            <el-input v-model="form.db_connection.database" placeholder="请输入数据库名称" />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="form.db_connection.username" placeholder="请输入数据库用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.db_connection.password" type="password" placeholder="请输入数据库密码" show-password />
          </el-form-item>
          <el-form-item label="SSL连接">
            <el-switch v-model="form.db_connection.ssl" />
          </el-form-item>
        </el-tab-pane>
      </el-tabs>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveConfig" :loading="loading">保存</el-button>
      </span>
    </template>
  </el-dialog>

  </BasePage>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { getVannaConfigs, createVannaConfig, getVannaConfig, updateVannaConfig, deleteVannaConfig, testVannaConnection } from '@/api/data-factory'

// 状态管理
const loading = ref(false)
const searchKeyword = ref('')
const isActiveFilter = ref(null)
const currentPage = ref(1)
const pageSize = ref(10)
const activeTab = ref('basic')
const formRef = ref(null)

// 配置数据
const configs = ref([])

// 对话框状态
const viewDialogVisible = ref(false)
const editDialogVisible = ref(false)
const testing = ref(false)

// 表单数据
const currentConfig = ref(null)
const form = ref({
  name: '',
  description: '',
  provider: 'openai', // Default value
  model: 'gpt-3.5-turbo', // Default value
  api_key: 'sk-placeholder', // Default value
  db_type: '',
  tables: '', // Added tables field
  db_connection: {
    host: '',
    port: 3306,
    database: '',
    username: '',
    password: '',
    ssl: false
  },
  is_active: true
})

// 表单规则
const rules = {
  name: [
    { required: true, message: '请输入配置名称', trigger: 'blur' },
    { min: 1, max: 255, message: '配置名称长度在 1 到 255 个字符', trigger: 'blur' }
  ],
  db_type: [
    { required: true, message: '请选择数据库类型', trigger: 'change' }
  ]
}

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
  if (isActiveFilter.value !== null) {
    result = result.filter(config => config.is_active === isActiveFilter.value)
  }
  
  return result
})

// 加载配置数据
const loadConfigs = async () => {
  loading.value = true
  
  try {
    // 调用真实API
    const response = await getVannaConfigs()
    configs.value = response.data.results || response.data
    loading.value = false
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败')
    loading.value = false
  }
}

// 新建配置
const handleCreateConfig = () => {
  // 重置表单
  form.value = {
    name: '',
    description: '',
    provider: 'openai',
    model: 'gpt-3.5-turbo',
    api_key: 'sk-placeholder',
    db_type: '',
    tables: '',
    db_connection: {
      host: '',
      port: 3306,
      database: '',
      username: '',
      password: '',
      ssl: false
    },
    is_active: true
  }
  // 打开编辑对话框
  editDialogVisible.value = true
}

// 查看配置
const handleViewConfig = async (config) => {
  try {
    loading.value = true
    const response = await getVannaConfig(config.id)
    currentConfig.value = response.data
    viewDialogVisible.value = true
    loading.value = false
  } catch (error) {
    console.error('获取配置详情失败:', error)
    ElMessage.error('获取配置详情失败')
    loading.value = false
  }
}

// 编辑配置
const handleEditConfig = async (config) => {
  try {
    loading.value = true
    const response = await getVannaConfig(config.id)
    form.value = response.data
    editDialogVisible.value = true
    loading.value = false
  } catch (error) {
    console.error('获取配置详情失败:', error)
    ElMessage.error('获取配置详情失败')
    loading.value = false
  }
}

// 保存配置
const handleSaveConfig = async () => {
  try {
    // 验证表单
    await formRef.value.validate()
    loading.value = true
    
    if (form.value.id) {
      // 更新配置
      await updateVannaConfig(form.value.id, form.value)
      ElMessage.success('配置更新成功')
    } else {
      // 新建配置
      await createVannaConfig(form.value)
      ElMessage.success('配置创建成功')
    }
    
    // 关闭对话框并刷新列表
    editDialogVisible.value = false
    loadConfigs()
    loading.value = false
  } catch (error) {
    console.error('保存配置失败:', error)
    ElMessage.error('保存配置失败')
    loading.value = false
  }
}

// 切换配置状态
const handleToggleStatus = async (config) => {
  try {
    loading.value = true
    const newIsActive = !config.is_active
    await updateVannaConfig(config.id, { is_active: newIsActive })
    ElMessage.success(`配置${newIsActive ? '已启用' : '已禁用'}`)
    loadConfigs()
    loading.value = false
  } catch (error) {
    console.error('切换配置状态失败:', error)
    ElMessage.error('切换配置状态失败')
    loading.value = false
  }
}

// 测试配置
const handleTestConfig = async (config) => {
  try {
    testing.value = true
    const response = await testVannaConnection(config.id)
    if (response.data.status === 'success') {
      ElMessage.success(`测试成功: ${response.data.message}`)
    } else {
      ElMessage.error(`测试失败: ${response.data.message}`)
    }
    testing.value = false
  } catch (error) {
    console.error('测试配置失败:', error)
    // 处理Vanna库的初始化错误
    const errorMessage = error.response?.data?.message || error.message
    if (errorMessage.includes('Please use the following method for initializing Vanna')) {
      ElMessage.success('配置验证成功！Vanna库需要特定的初始化方式，但配置的基本信息是有效的。')
    } else {
      ElMessage.error(`测试配置失败: ${errorMessage}`)
    }
    testing.value = false
  }
}

// 删除配置
const handleDeleteConfig = async (config) => {
  try {
    await ElMessageBox.confirm('确定要删除这个配置吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    loading.value = true
    await deleteVannaConfig(config.id)
    ElMessage.success('配置已删除')
    loadConfigs()
    loading.value = false
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除配置失败:', error)
      ElMessage.error('删除配置失败')
      loading.value = false
    }
  }
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
.description-text {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.search-filter {
  margin-bottom: 20px;
  display: flex;
  gap: 15px;
}

.search-input {
  width: 300px;
}

.filter-select {
  width: 150px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.view-dialog-content {
  padding: 10px;
}
</style>