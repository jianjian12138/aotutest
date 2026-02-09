<template>
  <div class="page-container">
    <div class="page-header">
      <h3 class="page-title">MCP 管理平台</h3>
      <div class="header-actions">
        <el-button type="primary" @click="prepareAddConfig">
          <el-icon><Plus /></el-icon> 新增 MCP 服务器
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <div class="card-container">
        <p class="description-text">管理 Model Context Protocol (MCP) 服务器，为 AI 提供外部工具和上下文支持</p>
        
        <el-table :data="mcpConfigs" style="width: 100%; flex: 1;" v-loading="loading">
          <el-table-column prop="name" label="服务器名称" width="180" />
          <el-table-column prop="api_url" label="服务器地址" min-width="200" show-overflow-tooltip />
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="scope">
               <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '激活' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="工具数量" width="120">
            <template #default="scope">
              <el-button link type="primary" @click="viewTools(scope.row)">
                {{ scope.row.tools_count || 0 }} 个工具
              </el-button>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="editConfig(scope.row)">编辑</el-button>
              <el-button size="small" type="success" plain @click="testConnection(scope.row)">测试</el-button>
              <el-button size="small" type="danger" @click="deleteConfig(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 编辑/新增对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="isEditing ? '编辑 MCP 配置' : '新增 MCP 配置'"
      width="600px"
    >
      <el-form :model="currentForm" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="服务器名称" prop="name">
          <el-input v-model="currentForm.name" placeholder="例如：文件系统 MCP" />
        </el-form-item>
        <el-form-item :label="currentForm.mcp_type === 'local' ? '执行命令' : '服务器地址'" prop="api_url">
          <el-input v-model="currentForm.api_url" :placeholder="currentForm.mcp_type === 'local' ? 'npx -y @modelcontextprotocol/server-everything' : 'http://localhost:3000'" />
        </el-form-item>
        <el-form-item label="认证 Token" prop="api_key" v-if="currentForm.mcp_type === 'remote'">
          <el-input v-model="currentForm.api_key" type="password" show-password placeholder="如果需要认证请填写" />
        </el-form-item>
        <el-form-item label="连接类型">
          <el-radio-group v-model="currentForm.mcp_type">
            <el-radio label="remote">远程 (HTTP/SSE)</el-radio>
            <el-radio label="local">本地 (Command Line)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="是否激活">
          <el-switch v-model="currentForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveConfig" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 工具列表对话框 -->
    <el-dialog
      v-model="showToolsDialog"
      title="可用工具列表"
      width="900px"
    >
      <el-table :data="toolsList" stripe>
        <el-table-column prop="name" label="工具名称" width="200" />
        <el-table-column prop="description" label="描述" min-width="300" />
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button size="small" type="primary" plain @click="prepareDebug(scope.row)">调试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 工具调试对话框 -->
    <el-dialog
      v-model="showDebugDialog"
      :title="`调试工具: ${selectedTool?.name}`"
      width="700px"
      append-to-body
    >
      <div v-if="selectedTool" class="debug-container">
        <div class="tool-info">
          <p class="description"><strong>描述:</strong> {{ selectedTool.description }}</p>
        </div>

        <el-divider content-position="left">参数输入</el-divider>
        
        <el-form label-position="top" class="debug-form">
          <template v-if="selectedTool.input_schema && selectedTool.input_schema.properties">
            <el-form-item 
              v-for="(prop, name) in selectedTool.input_schema.properties" 
              :key="name" 
              :label="name"
              :required="selectedTool.input_schema.required?.includes(name)"
            >
              <el-input 
                v-if="prop.type === 'string'" 
                v-model="debugArguments[name]" 
                :placeholder="prop.description"
              />
              <el-input-number 
                v-else-if="prop.type === 'number' || prop.type === 'integer'" 
                v-model="debugArguments[name]" 
                style="width: 100%"
              />
              <el-switch 
                v-else-if="prop.type === 'boolean'" 
                v-model="debugArguments[name]" 
              />
              <el-input 
                v-else 
                v-model="debugArguments[name]" 
                type="textarea" 
                placeholder="JSON 格式数据"
                :rows="2"
              />
              <div class="prop-desc" v-if="prop.description">{{ prop.description }}</div>
            </el-form-item>
          </template>
          <div v-else class="no-params">此工具无需参数</div>
        </el-form>

        <div class="debug-actions">
          <el-button type="primary" @click="runToolDebug" :loading="debugging">立即执行</el-button>
        </div>

        <el-divider v-if="debugResult" content-position="left">执行结果</el-divider>
        <div v-if="debugResult" class="result-panel" :class="{ 'is-error': debugResult.isError }">
          <pre class="result-content">{{ formatDebugResult(debugResult) }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const mcpConfigs = ref([])
const loading = ref(false)
const showEditDialog = ref(false)
const showToolsDialog = ref(false)
const showDebugDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const debugging = ref(false)
const formRef = ref(null)
const toolsList = ref([])
const selectedConfig = ref(null)
const selectedTool = ref(null)
const debugArguments = ref({})
const debugResult = ref(null)

const currentForm = ref({
  id: null,
  name: '',
  provider: 'mcp',
  api_url: '',
  api_key: '',
  is_active: true,
  mcp_type: 'remote'
})

const rules = {
  name: [{ required: true, message: '请输入服务器名称', trigger: 'blur' }],
  api_url: [{ required: true, message: '请输入服务器地址', trigger: 'blur' }]
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const response = await api.get('/assistant/config/workflow/', { params: { provider: 'mcp' } })
    mcpConfigs.value = response.data.filter(c => c.provider === 'mcp')
  } catch (error) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

const prepareAddConfig = () => {
  isEditing.value = false
  currentForm.value = {
    id: null,
    name: '',
    provider: 'mcp',
    api_url: '',
    api_key: '',
    is_active: true,
    mcp_type: 'remote'
  }
  showEditDialog.value = true
}

const editConfig = (row) => {
  isEditing.value = true
  currentForm.value = { ...row, api_key: '' }
  showEditDialog.value = true
}

const saveConfig = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = { ...currentForm.value }
      
      if (payload.id) {
        await api.put(`/assistant/config/workflow/${payload.id}/`, payload)
      } else {
        await api.post('/assistant/config/workflow/', payload)
      }
      showEditDialog.value = false
      loadConfigs()
      ElMessage.success('保存成功')
    } catch (error) {
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

const testConnection = async (row) => {
  try {
    const response = await api.post('/assistant/config/workflow/test_connection/', {
      id: row.id,
      provider: 'mcp',
      api_url: row.api_url,
      api_key: row.api_key,
      mcp_type: row.mcp_type
    })
    if (response.data.success) {
      ElMessage.success(`连接成功，发现 ${response.data.tools_count} 个工具`)
      loadConfigs() // 刷新列表以显示最新的工具数量
    } else {
      ElMessage.error('连接失败: ' + response.data.message)
    }
  } catch (error) {
    ElMessage.error('连接超时或失败')
  }
}

const deleteConfig = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该 MCP 配置吗？', '警告', { type: 'warning' })
    await api.delete(`/assistant/config/workflow/${row.id}/`)
    loadConfigs()
    ElMessage.success('删除成功')
  } catch (e) {}
}

const viewTools = async (row) => {
  selectedConfig.value = row
  try {
    const response = await api.get(`/assistant/config/workflow/${row.id}/mcp_tools/`)
    // 后端可能直接返回列表，也可能返回包含 tools 字段的对象
    if (Array.isArray(response.data)) {
      toolsList.value = response.data
    } else if (response.data && Array.isArray(response.data.tools)) {
      toolsList.value = response.data.tools
    } else {
      toolsList.value = []
    }
    showToolsDialog.value = true
  } catch (error) {
    ElMessage.error('获取工具列表失败')
  }
}

const prepareDebug = (tool) => {
  selectedTool.value = tool
  debugArguments.value = {}
  debugResult.value = null
  
  // 初始化默认值
  if (tool.input_schema && tool.input_schema.properties) {
    Object.keys(tool.input_schema.properties).forEach(key => {
      const prop = tool.input_schema.properties[key]
      if (prop.default !== undefined) {
        debugArguments.value[key] = prop.default
      } else if (prop.type === 'boolean') {
        debugArguments.value[key] = false
      }
    })
  }
  
  showDebugDialog.value = true
}

const runToolDebug = async () => {
  if (!selectedConfig.value || !selectedTool.value) return
  
  debugging.value = true
  debugResult.value = null
  
  try {
    const response = await api.post(`/assistant/config/workflow/${selectedConfig.value.id}/call_mcp_tool/`, {
      tool_name: selectedTool.value.name,
      arguments: debugArguments.value
    })
    debugResult.value = response.data
    ElMessage.success('执行完成')
  } catch (error) {
    debugResult.value = { 
      isError: true, 
      content: [{ type: 'text', text: error.response?.data?.error || '请求失败' }] 
    }
    ElMessage.error('工具执行出错')
  } finally {
    debugging.value = false
  }
}

const formatDebugResult = (result) => {
  if (!result) return ''
  
  // 如果是 stdio 模式的 content 结构
  if (result.content && Array.isArray(result.content)) {
    return result.content.map(c => c.text || JSON.stringify(c, null, 2)).join('\n')
  }
  
  // 如果是直接的 JSON
  return JSON.stringify(result, null, 2)
}

onMounted(loadConfigs)
</script>

<style scoped lang="scss">
.page-container {
  padding: 24px;
  background-color: #f5f7fa;
  min-height: 100vh;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.debug-container {
  .tool-info {
    margin-bottom: 20px;
    .description {
      color: #606266;
      line-height: 1.6;
    }
  }
  
  .debug-form {
    max-height: 400px;
    overflow-y: auto;
    padding-right: 10px;
    
    .prop-desc {
      font-size: 12px;
      color: #909399;
      line-height: 1.2;
      margin-top: 4px;
    }
  }

  .debug-actions {
    margin: 24px 0;
    display: flex;
    justify-content: center;
  }

  .result-panel {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 16px;
    border-radius: 4px;
    margin-top: 10px;
    max-height: 300px;
    overflow-y: auto;
    border-left: 4px solid #409eff;

    &.is-error {
      border-left-color: #f56c6c;
      background: #2d1d1d;
    }

    .result-content {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px;
    }
  }

  .no-params {
    text-align: center;
    color: #909399;
    padding: 20px;
  }
}

.card-container {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}
.description-text {
  color: #909399;
  margin-bottom: 16px;
}
</style>
