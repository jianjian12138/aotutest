<template>
  <BasePage title="环境管理">
    <template #actions><el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建环境
        </el-button></template>
    
   

    <div class="main-content">
      <div class="card-container">
        <el-tabs v-model="activeTab" @tab-change="onTabChange">
          <el-tab-pane label="全局环境变量" name="GLOBAL">
            <EnvironmentTable 
              :data="globalEnvironments" 
              :loading="loading"
              scope="GLOBAL"
              @edit="editEnvironment"
              @delete="deleteEnvironment"
              @activate="activateEnvironment"
              @duplicate="duplicateEnvironment"
            />
          </el-tab-pane>
          <el-tab-pane label="局部环境变量" name="LOCAL">
            <div class="local-env-header">
              <el-select 
                v-model="selectedProject" 
                placeholder="选择项目"
                @change="loadLocalEnvironments"
                class="filter-select"
              >
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
            </div>
            <EnvironmentTable 
              :data="localEnvironments" 
              :loading="loading"
              scope="LOCAL"
              @edit="editEnvironment"
              @delete="deleteEnvironment"
              @activate="activateEnvironment"
              @duplicate="duplicateEnvironment"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 创建/编辑环境对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingEnvironment ? '编辑环境' : '新建环境'"
      width="800px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
      >
        <el-form-item label="环境名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入环境名称" />
        </el-form-item>
        
        <el-form-item label="作用域" prop="scope">
          <el-radio-group v-model="form.scope" @change="onScopeChange">
            <el-radio value="GLOBAL">全局环境变量</el-radio>
            <el-radio value="LOCAL">局部环境变量</el-radio>
          </el-radio-group>
          <div class="scope-help">
            <el-text size="small" type="info">
              全局环境变量对所有项目生效，局部环境变量仅对关联项目生效
            </el-text>
          </div>
        </el-form-item>
        
        <el-form-item 
          v-if="form.scope === 'LOCAL'" 
          label="关联项目" 
          prop="project"
        >
          <el-select v-model="form.project" placeholder="请选择关联项目">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="环境变量" prop="variables">
          <div class="variables-editor">
            <div class="variables-header">
              <div class="column">变量名</div>
              <div class="column">初始值</div>
              <div class="column">当前值</div>
              <div class="column">操作</div>
            </div>
            
            <div class="variables-body">
              <div
                v-for="(variable, index) in form.variables"
                :key="index"
                class="variable-row"
              >
                <div class="column">
                  <el-input
                    v-model="variable.key"
                    placeholder="变量名"
                    size="small"
                  />
                </div>
                <div class="column">
                  <el-input
                    v-model="variable.initialValue"
                    placeholder="初始值"
                    size="small"
                  />
                </div>
                <div class="column">
                  <el-input
                    v-model="variable.currentValue"
                    placeholder="当前值"
                    size="small"
                  />
                </div>
                <div class="column">
                  <el-button
                    size="small"
                    type="danger"
                    :icon="Delete"
                    @click="removeVariable(index)"
                    :disabled="form.variables.length <= 1"
                  />
                </div>
              </div>
            </div>
            
            <div class="variables-footer">
              <el-button size="small" @click="addVariable">
                <el-icon><Plus /></el-icon>
                添加变量
              </el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ editingEnvironment ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看变量对话框 -->
    <el-dialog
      v-model="showViewDialog"
      title="环境变量详情"
      width="600px"
    >
      <div v-if="viewingEnvironment" class="view-variables">
        <el-table :data="viewVariables" style="width: 100%">
          <el-table-column prop="key" label="变量名" width="150" />
          <el-table-column prop="initialValue" label="初始值" />
          <el-table-column prop="currentValue" label="当前值" />
        </el-table>
      </div>
      
      <template #footer>
        <el-button @click="showViewDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Setting } from '@element-plus/icons-vue'
import api from '@/utils/api'
import EnvironmentTable from './components/EnvironmentTable.vue'
import '@/assets/css/global.scss'

const activeTab = ref('GLOBAL')
const globalEnvironments = ref([])
const localEnvironments = ref([])
const projects = ref([])
const selectedProject = ref(null)
const loading = ref(false)
const showCreateDialog = ref(false)
const showViewDialog = ref(false)
const editingEnvironment = ref(null)
const viewingEnvironment = ref(null)
const submitting = ref(false)
const formRef = ref()

const form = reactive({
  name: '',
  scope: 'GLOBAL',
  project: null,
  variables: [
    {
      key: '',
      initialValue: '',
      currentValue: ''
    }
  ]
})

const rules = {
  name: [
    { required: true, message: '请输入环境名称', trigger: 'blur' }
  ],
  scope: [
    { required: true, message: '请选择作用域', trigger: 'change' }
  ],
  project: [
    { 
      validator: (rule, value, callback) => {
        if (form.scope === 'LOCAL' && !value) {
          callback(new Error('请选择关联项目'))
        } else {
          callback()
        }
      }, 
      trigger: 'change' 
    }
  ]
}

const viewVariables = computed(() => {
  if (!viewingEnvironment.value?.variables) return []
  
  const vars = viewingEnvironment.value.variables
  return Object.keys(vars).map(key => ({
    key,
    initialValue: vars[key]?.initialValue || vars[key] || '',
    currentValue: vars[key]?.currentValue || vars[key] || ''
  }))
})

const loadProjects = async () => {
  try {
    const response = await api.get('/api-testing/projects/')
    projects.value = response.data.results || response.data
    if (projects.value.length > 0 && !selectedProject.value) {
      selectedProject.value = projects.value[0].id
    }
  } catch (error) {
    ElMessage.error('加载项目列表失败')
  }
}

const loadGlobalEnvironments = async () => {
  loading.value = true
  try {
    const response = await api.get('/api-testing/environments/', {
      params: { scope: 'GLOBAL' }
    })
    globalEnvironments.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('加载全局环境失败')
  } finally {
    loading.value = false
  }
}

const loadLocalEnvironments = async () => {
  if (!selectedProject.value) return
  
  loading.value = true
  try {
    const response = await api.get('/api-testing/environments/', {
      params: { 
        scope: 'LOCAL',
        project: selectedProject.value
      }
    })
    localEnvironments.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('加载局部环境失败')
  } finally {
    loading.value = false
  }
}

const onTabChange = (tab) => {
  if (tab === 'GLOBAL') {
    loadGlobalEnvironments()
  } else {
    loadLocalEnvironments()
  }
}

const onScopeChange = () => {
  if (form.scope === 'GLOBAL') {
    form.project = null
  }
}

const addVariable = () => {
  form.variables.push({
    key: '',
    initialValue: '',
    currentValue: ''
  })
}

const removeVariable = (index) => {
  if (form.variables.length > 1) {
    form.variables.splice(index, 1)
  }
}

const editEnvironment = (environment) => {
  editingEnvironment.value = environment
  form.name = environment.name
  form.scope = environment.scope
  form.project = environment.project
  
  // 转换变量格式
  const variables = environment.variables || {}
  form.variables = Object.keys(variables).map(key => {
    const value = variables[key]
    if (typeof value === 'object') {
      return {
        key,
        initialValue: value.initialValue || '',
        currentValue: value.currentValue || ''
      }
    } else {
      return {
        key,
        initialValue: value || '',
        currentValue: value || ''
      }
    }
  })
  
  if (form.variables.length === 0) {
    form.variables.push({
      key: '',
      initialValue: '',
      currentValue: ''
    })
  }
  
  showCreateDialog.value = true
}

const deleteEnvironment = async (environment) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除环境 "${environment.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await api.delete(`/api-testing/environments/${environment.id}/`)
    ElMessage.success('删除成功')
    
    if (activeTab.value === 'GLOBAL') {
      await loadGlobalEnvironments()
    } else {
      await loadLocalEnvironments()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const activateEnvironment = async (environment) => {
  try {
    await api.post(`/api-testing/environments/${environment.id}/activate/`)
    ElMessage.success('环境已激活')
    
    if (activeTab.value === 'GLOBAL') {
      await loadGlobalEnvironments()
    } else {
      await loadLocalEnvironments()
    }
  } catch (error) {
    ElMessage.error('激活失败')
  }
}

const duplicateEnvironment = async (environment) => {
  const newEnv = {
    name: `${environment.name} - 副本`,
    scope: environment.scope,
    project: environment.scope === 'LOCAL' ? 
      (typeof environment.project === 'object' ? environment.project.id : environment.project) : 
      null,
    variables: environment.variables || {}
  }
  
  try {
    await api.post('/api-testing/environments/', newEnv)
    ElMessage.success('复制成功')
    
    if (activeTab.value === 'GLOBAL') {
      await loadGlobalEnvironments()
    } else {
      await loadLocalEnvironments()
    }
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitting.value = true
  try {
    // 转换变量格式
    const variables = {}
    form.variables.forEach(variable => {
      if (variable.key) {
        variables[variable.key] = {
          initialValue: variable.initialValue || '',
          currentValue: variable.currentValue || variable.initialValue || ''
        }
      }
    })
    
    const data = {
      name: form.name,
      scope: form.scope,
      project: form.scope === 'LOCAL' ? form.project : null,
      variables
    }
    
    if (editingEnvironment.value) {
      await api.put(`/api-testing/environments/${editingEnvironment.value.id}/`, data)
      ElMessage.success('环境更新成功')
    } else {
      await api.post('/api-testing/environments/', data)
      ElMessage.success('环境创建成功')
    }
    
    showCreateDialog.value = false
    
    if (activeTab.value === 'GLOBAL') {
      await loadGlobalEnvironments()
    } else {
      await loadLocalEnvironments()
    }
  } catch (error) {
    ElMessage.error(editingEnvironment.value ? '更新环境失败' : '创建环境失败')
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  editingEnvironment.value = null
  Object.assign(form, {
    name: '',
    scope: 'GLOBAL',
    project: null,
    variables: [
      {
        key: '',
        initialValue: '',
        currentValue: ''
      }
    ]
  })
  formRef.value?.resetFields()
}

onMounted(async () => {
  await loadProjects()
  await loadGlobalEnvironments()
  if (selectedProject.value) {
    await loadLocalEnvironments()
  }
})
</script>

<style scoped>
/* 页面特定样式 */






  

/* Tabs样式调整 */
:deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0 !important;
}

:deep(.el-tabs__header) {
  margin-bottom: 15px;
}

.local-env-header {
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.scope-help {
  margin-top: 5px;
}

.variables-editor {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: white;
}

.variables-header {
  display: flex;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  padding: 8px;
  font-weight: 500;
  font-size: 12px;
  color: #606266;
}

.variables-body {
  max-height: 300px;
  overflow-y: auto;
}

.variable-row {
  display: flex;
  border-bottom: 1px solid #f5f7fa;
  padding: 8px;
  min-height: 40px;
  align-items: center;
}

.variable-row:hover {
  background: #fafbfc;
}

.column {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
}

.column:last-child {
  flex: 0 0 60px;
  justify-content: center;
}

.variables-footer {
  padding: 8px;
  border-top: 1px solid #f5f7fa;
  background: #fafbfc;
}

.view-variables {
  max-height: 400px;
  overflow-y: auto;
}
</style>
