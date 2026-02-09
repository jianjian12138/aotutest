<template>
  <div class="page-container">
    <div class="page-header">
      <h3 class="page-title">Skills 技能管理</h3>
      <div class="header-actions">
        <el-button type="primary" @click="prepareAddConfig">
          <el-icon><Plus /></el-icon> 新增测试技能
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <div class="card-container">
        <p class="description-text">定义自定义 Python 技能，扩展自动化测试的边界</p>
        
        <el-table :data="skillsConfigs" style="width: 100%; flex: 1;" v-loading="loading">
          <el-table-column prop="name" label="技能名称" width="180" />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
             <template #default="scope">
               {{ scope.row.additional_config?.description || '暂无描述' }}
             </template>
          </el-table-column>
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
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="editConfig(scope.row)">编辑代码</el-button>
              <el-button size="small" type="success" plain @click="debugSkill(scope.row)">测试</el-button>
              <el-button size="small" type="danger" @click="deleteConfig(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 代码编辑对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="isEditing ? '编辑测试技能' : '新增测试技能'"
      width="800px"
      top="5vh"
    >
      <el-form :model="currentForm" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="技能名称" prop="name">
          <el-input v-model="currentForm.name" placeholder="例如：生成订单签名" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="currentForm.description" type="textarea" placeholder="技能用途说明" />
        </el-form-item>
        <el-form-item label="Python 代码" prop="code">
          <div class="code-editor-container">
            <el-input
              v-model="currentForm.code"
              type="textarea"
              :rows="15"
              font-family="monospace"
              placeholder="# 编写 Python 代码... 结果请赋值给 result 变量"
            />
          </div>
        </el-form-item>
        <el-form-item label="是否激活">
          <el-switch v-model="currentForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveConfig" :loading="saving">保存技能</el-button>
      </template>
    </el-dialog>

    <!-- 调试结果对话框 -->
    <el-dialog
      v-model="showDebugDialog"
      title="技能执行调试"
      width="600px"
    >
      <div class="debug-content">
        <div v-if="debugResult">
          <el-alert
            :title="debugResult.success ? '执行成功' : '执行失败'"
            :type="debugResult.success ? 'success' : 'error'"
            show-icon
            :closable="false"
          />
          <div class="mt-4">
            <strong>输出日志:</strong>
            <pre class="log-box">{{ debugResult.output || '无输出' }}</pre>
          </div>
          <div class="mt-2" v-if="debugResult.result">
            <strong>返回值 (result):</strong>
            <pre class="result-box">{{ formatJson(debugResult.result) }}</pre>
          </div>
          <div class="mt-2" v-if="debugResult.error">
            <strong>错误详情:</strong>
            <pre class="error-box">{{ debugResult.error }}</pre>
          </div>
        </div>
        <div v-else class="loading-box">
          <el-icon class="is-loading"><Loading /></el-icon> 正在执行...
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Loading } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const skillsConfigs = ref([])
const loading = ref(false)
const showEditDialog = ref(false)
const showDebugDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const formRef = ref(null)
const debugResult = ref(null)

const currentForm = ref({
  id: null,
  name: '',
  provider: 'skills',
  api_url: 'local://skills',
  description: '',
  code: '',
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入技能名称', trigger: 'blur' }],
  code: [{ required: true, message: '代码不能为空', trigger: 'blur' }]
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const formatJson = (val) => {
  if (typeof val === 'object') return JSON.stringify(val, null, 2)
  return val
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const response = await api.get('/assistant/config/workflow/', { params: { provider: 'skills' } })
    skillsConfigs.value = response.data.filter(c => c.provider === 'skills')
  } catch (error) {
    ElMessage.error('加载技能列表失败')
  } finally {
    loading.value = false
  }
}

const prepareAddConfig = () => {
  isEditing.value = false
  currentForm.value = {
    id: null,
    name: '',
    provider: 'skills',
    api_url: 'local://skills',
    description: '',
    code: 'print("Hello Skills")\nresult = {"status": "ok"}',
    is_active: true
  }
  showEditDialog.value = true
}

const editConfig = (row) => {
  isEditing.value = true
  currentForm.value = { 
    ...row, 
    code: row.additional_config?.code || '',
    description: row.additional_config?.description || ''
  }
  showEditDialog.value = true
}

const saveConfig = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = { ...currentForm.value }
      payload.additional_config = { 
        code: payload.code,
        description: payload.description
      }
      
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

const debugSkill = async (row) => {
  debugResult.value = null
  showDebugDialog.value = true
  try {
    const response = await api.post(`/assistant/config/workflow/${row.id}/run_skill/`, {
      context: { test_mode: true }
    })
    debugResult.value = response.data
  } catch (error) {
    ElMessage.error('调试请求失败')
    showDebugDialog.value = false
  }
}

const deleteConfig = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该测试技能吗？', '警告', { type: 'warning' })
    await api.delete(`/assistant/config/workflow/${row.id}/`)
    loadConfigs()
    ElMessage.success('删除成功')
  } catch (e) {}
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
.log-box, .result-box, .error-box {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  margin-top: 8px;
  overflow-x: auto;
}
.error-box {
  color: #f44336;
}
.loading-box {
  text-align: center;
  padding: 40px;
  color: #909399;
}
</style>
