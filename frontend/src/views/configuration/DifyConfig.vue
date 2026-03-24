<template>
  <BasePage title="工作流配置">
    <template #actions>
      <el-button type="primary" @click="prepareAddConfig">
        <el-icon><Plus /></el-icon> 新增配置
      </el-button>
    </template>

    <div class="main-content">
      <div class="card-container">
        <p class="description-text">配置AI工作流引擎以启用自动化功能，支持多引擎管理</p>
        
        <!-- 配置列表卡片 -->
        <el-table :data="workflowConfigs" style="width: 100%; flex: 1;" v-loading="loading">
          <el-table-column prop="name" label="配置名称" width="180" />
          <el-table-column prop="provider" label="提供商" width="120">
             <template #default="scope">
               <el-tag>{{ scope.row.provider }}</el-tag>
            </template>              
          </el-table-column>
          <el-table-column prop="api_url" label="API URL" min-width="200" show-overflow-tooltip />
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="scope">
               <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '激活' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="editConfig(scope.row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteConfig(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 编辑/新增对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="isEditing ? '编辑配置' : '新增配置'"
      width="600px"
    >
      <el-form :model="currentConfigForm" :rules="rules" ref="configFormRef" label-width="100px" :validate-on-rule-change="false">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="currentConfigForm.name" placeholder="例如：Coze生产环境" />
        </el-form-item>
        <el-form-item label="提供商" prop="provider">
          <el-select v-model="currentConfigForm.provider" placeholder="选择提供商" style="width: 100%" @change="handleProviderChange">
            <el-option label="Coze" value="coze" />
            <el-option label="Dify" value="dify" />
            <el-option label="n8n" value="n8n" />
          </el-select>
        </el-form-item>

        <!-- 部署模式选择 -->
        <el-form-item label="部署模式">
          <el-radio-group v-model="currentConfigForm.deploy_mode" @change="handleDeployModeChange">
            <el-radio label="online">线上 (Cloud)</el-radio>
            <el-radio label="local">本地 (Self-hosted)</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 通用配置 -->
        <el-form-item 
          label="API URL" 
          prop="api_url" 
        >
          <el-input v-model="currentConfigForm.api_url" placeholder="API地址" />
        </el-form-item>

        <el-form-item 
          label="API Key" 
          prop="api_key"
        >
          <el-input 
            v-model="currentConfigForm.api_key" 
            type="password" 
            show-password 
            :placeholder="isEditing ? '留空则不修改' : 'API密钥'" 
          />
        </el-form-item>

        <el-form-item label="工作流ID" v-if="['coze', 'dify'].includes(currentConfigForm.provider)">
          <el-input v-model="currentConfigForm.workflow_id" placeholder="Workflow / Bot ID" />
        </el-form-item>
        <el-form-item label="是否激活">
          <el-switch v-model="currentConfigForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditDialog = false">取消</el-button>
          <el-button type="success" plain @click="testConfigConnection" :loading="testing">测试连接</el-button>
          <el-button type="primary" @click="saveConfig" :loading="saving">保存</el-button>
        </span>
      </template>
    </el-dialog>
  

  </BasePage>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Setting } from '@element-plus/icons-vue'
import api from '@/utils/api'

const workflowConfigs = ref([])
const loading = ref(false)
const showEditDialog = ref(false)
const isEditing = ref(false)
const testing = ref(false)
const saving = ref(false)
const configFormRef = ref(null)

const currentConfigForm = ref({
  id: null,
  name: '',
  provider: 'coze',
  api_url: '',
  api_key: '',
  workflow_id: '',
  is_active: true,
  deploy_mode: 'online',
  // MCP fields
  mcp_type: 'sse',
  mcp_command: '',
  mcp_args: '',
  mcp_env: ''
})

const rules = computed(() => {
  const commonRules = {
    name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
    provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
    api_url: [{ required: true, message: '请输入API URL', trigger: 'blur' }]
  }

  return commonRules
})

const handleProviderChange = (val) => {
  // 重置相关字段
  currentConfigForm.value.api_url = ''
  currentConfigForm.value.api_key = ''
  
  currentConfigForm.value.deploy_mode = 'online'
  handleDeployModeChange('online')
  
  // 清除验证状态
  if (configFormRef.value) {
    configFormRef.value.clearValidate()
  }
}

const handleDeployModeChange = (val) => {
  const provider = currentConfigForm.value.provider
  
  if (val === 'online') {
    if (provider === 'dify') {
      currentConfigForm.value.api_url = 'https://api.dify.ai/v1'
    } else if (provider === 'coze') {
      currentConfigForm.value.api_url = 'https://api.coze.com/open_api/v2'
    } else if (provider === 'n8n') {
      currentConfigForm.value.api_url = '' // n8n cloud URL varies
    }
  } else {
    // Local mode defaults
    if (provider === 'dify') {
      currentConfigForm.value.api_url = 'http://localhost/v1'
    } else if (provider === 'n8n') {
      currentConfigForm.value.api_url = 'http://localhost:5678/webhook'
    } else {
      currentConfigForm.value.api_url = ''
    }
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const loadWorkflowConfigs = async () => {
  loading.value = true
  try {
    const response = await api.get('/assistant/config/workflow/')
    workflowConfigs.value = Array.isArray(response.data) ? response.data : (response.data.results || [])
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

const prepareAddConfig = () => {
  isEditing.value = false
  currentConfigForm.value = {
    id: null,
    name: '',
    provider: 'coze',
    api_url: '',
    api_key: '',
    workflow_id: '',
    is_active: true,
    deploy_mode: 'online',
    mcp_type: 'sse',
    mcp_command: '',
    mcp_args: '',
    mcp_env: ''
  }
  showEditDialog.value = true
  // 初始化URL
  handleDeployModeChange('online')
}

const editConfig = (row) => {
  isEditing.value = true
  const additional = row.additional_config || {}
  
  currentConfigForm.value = { 
    ...row, 
    api_key: '',
    deploy_mode: additional.deploy_mode || 'online',
    mcp_type: additional.mcp_type || 'sse',
    mcp_command: additional.mcp_command || '',
    mcp_args: additional.mcp_args || '',
    mcp_env: additional.mcp_env ? JSON.stringify(additional.mcp_env, null, 2) : ''
  } 
  showEditDialog.value = true
}

const saveConfig = async () => {
  if (!configFormRef.value) return
  
  await configFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      const data = { ...currentConfigForm.value }
      
      data.additional_config = data.additional_config || {}
      
      // Handle deploy_mode
      data.additional_config.deploy_mode = data.deploy_mode
      
      // Remove temporary fields
      delete data.deploy_mode
      delete data.mcp_type
      delete data.mcp_command
      delete data.mcp_args
      delete data.mcp_env

      if (!data.api_key) delete data.api_key // 如果为空则不提交（编辑时）
      
      if (data.id) {
        await api.patch(`/assistant/config/workflow/${data.id}/`, data)
        ElMessage.success('更新成功')
      } else {
        await api.post('/assistant/config/workflow/', data)
        ElMessage.success('创建成功')
      }
      showEditDialog.value = false
      loadWorkflowConfigs()
    } catch (error) {
      ElMessage.error('保存失败: ' + (error.response?.data?.error || error.message))
    } finally {
      saving.value = false
    }
  })
}

const deleteConfig = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该配置吗？', '提示', { type: 'warning' })
    await api.delete(`/assistant/config/workflow/${row.id}/`)
    ElMessage.success('删除成功')
    loadWorkflowConfigs()
  } catch (e) {
    // cancel
  }
}

const testConfigConnection = async () => {
  testing.value = true
  try {
    const response = await api.post('/assistant/config/workflow/test_connection/', currentConfigForm.value)
    if (response.data.success) {
      ElMessage.success(response.data.message)
    } else {
      ElMessage.error(response.data.message)
    }
  } catch (error) {
    ElMessage.error('测试连接失败')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadWorkflowConfigs()
})
</script>

<style scoped lang="scss">










.main-content {
  flex: 1;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-container {
  flex: 1;
  background: #fff;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.description-text {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
