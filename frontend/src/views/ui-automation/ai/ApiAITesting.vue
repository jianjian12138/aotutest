<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">API 智能测试实验室</h1>
      <div class="header-controls">
        <el-select v-model="projectId" placeholder="选择项目" style="width: 200px" @change="onProjectChange">
          <el-option v-for="project in projects" :key="project?.id" :label="project?.name" :value="project?.id" />
        </el-select>
        
        <el-select v-model="selectedModelConfigId" placeholder="选择 AI 模型" style="width: 250px">
          <el-option 
            v-for="config in modelConfigs" 
            :key="config?.id" 
            :label="`${config?.name} (${config?.model_type})`" 
            :value="config?.id" 
          />
        </el-select>
      </div>
    </div>

    <div class="card-container">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="section-title">任务输入</div>
              <el-form :model="taskForm" label-position="top">
                <el-form-item label="任务描述" required>
                  <el-input
                    v-model="taskForm.description"
                    type="textarea"
                    :rows="10"
                    placeholder="请用自然语言描述要执行的任务，例如：&#10;1. 登录系统获取Token&#10;2. 查询用户列表&#10;3. 检查第一个用户的状态"
                    maxlength="2000"
                    show-word-limit
                  />
                </el-form-item>
                
                <el-form-item>
                  <el-button 
                    type="primary" 
                    @click="handleRun" 
                    :loading="running"
                    :disabled="!taskForm.description || !projectId || !selectedModelConfigId"
                  >
                    <el-icon><Connection /></el-icon>
                    开始执行 (API)
                  </el-button>
                  <el-button 
                    type="danger" 
                    @click="handleStop" 
                    :disabled="!running"
                    v-if="running"
                  >
                    <el-icon><SwitchButton /></el-icon>
                    停止执行
                  </el-button>
                  <el-button 
                    type="success" 
                    @click="handleSaveCase" 
                    :disabled="!taskForm.description"
                  >
                    <el-icon><DocumentAdd /></el-icon>
                    保存用例
                  </el-button>
                </el-form-item>
              </el-form>
              
              <el-alert
                title="API Agent 模式提示"
                type="info"
                :closable="false"
                style="margin-top: 20px;"
                show-icon
              >
                <template #default>
                  <div>通过自然语言驱动 API 测试。Agent 将自动分析任务、生成请求参数并执行。</div>
                  <div>支持多步交互和上下文变量传递。</div>
                </template>
              </el-alert>
              
              <div class="section-title" style="margin-top: 20px;">执行日志</div>
              <div class="log-container" ref="logContainer">
                <div v-if="!logs && !running" class="empty-logs">
                  暂无执行日志
                </div>
                <pre v-else class="log-content">{{ logs }}</pre>
              </div>
            </el-col>
            
            <el-col :span="12">
              <div class="section-title">任务明细</div>
              <div class="task-list-container">
                <div v-if="analyzing" class="analyzing-state">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>任务分析中...</span>
                </div>
                <div v-else-if="plannedTasks && plannedTasks.length > 0">
                  <div 
                    v-for="task in plannedTasks" 
                    :key="task?.id" 
                    class="task-item"
                    :class="task?.status"
                  >
                    <div class="task-status-icon">
                      <el-icon v-if="task?.status === 'completed'" color="#67C23A"><CircleCheckFilled /></el-icon>
                      <el-icon v-else-if="task?.status === 'in_progress'" class="is-loading" color="#409EFF"><Loading /></el-icon>
                      <el-icon v-else-if="task?.status === 'failed'" color="#F56C6C"><CircleCloseFilled /></el-icon>
                      <el-icon v-else color="#909399"><CircleCheck /></el-icon>
                    </div>
                    <div class="task-content">
                      <span class="task-id">{{ task?.id }}.</span>
                      <span class="task-desc">{{ task?.description }}</span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-tasks">
                  暂无任务
                </div>
              </div>
            </el-col>
          </el-row>
    </div>

    <!-- 保存用例对话框 -->
    <el-dialog v-model="saveCaseDialogVisible" title="保存为测试用例" width="500px">
      <el-form :model="saveCaseForm" label-width="80px">
        <el-form-item label="用例名称" required>
          <el-input v-model="saveCaseForm.name" placeholder="请输入用例名称" />
        </el-form-item>
        <el-form-item label="所属项目">
           <el-select v-model="saveCaseForm.project" disabled>
             <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
           </el-select>
        </el-form-item>
        <el-form-item label="用例描述">
          <el-input v-model="saveCaseForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="saveCaseForm.save_as_case">同时保存为 API 测试用例</el-checkbox>
          <div class="form-tip">
            勾选后，系统将自动把自然语言描述转换为结构化的 API 测试用例步骤。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="saveCaseDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmSaveCase" :loading="savingCase">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Connection, SwitchButton, CircleCheckFilled, CircleCheck, CircleCloseFilled, Loading, DocumentAdd } from '@element-plus/icons-vue'
import request from '@/utils/api'
import { 
  getUiProjects, 
  runAdhocAITask, 
  getAIExecutionRecordDetail,
  stopAITask,
  createAICase
} from '@/api/ui_automation'

const route = useRoute()
const projects = ref([])
const projectId = ref('')
const modelConfigs = ref([])
const selectedModelConfigId = ref('')

const running = ref(false)
const analyzing = ref(false)
const logs = ref('')
const currentExecutionId = ref(null)
const logContainer = ref(null)
const plannedTasks = ref([])

// 保存用例相关
const saveCaseDialogVisible = ref(false)
const savingCase = ref(false)
const saveCaseForm = reactive({
  name: '',
  project: '',
  description: '',
  save_as_case: false
})

const taskForm = reactive({
  description: '',
})

// 加载 AI 模型配置
const loadModelConfigs = async () => {
  try {
    const response = await request.get('/requirement-analysis/api/ai-models/')
    let results = []
    if (response.data && Array.isArray(response.data.results)) {
      results = response.data.results
    } else if (Array.isArray(response.data)) {
      results = response.data
    }
    
    modelConfigs.value = results.filter(c => c.is_active)
    
    if (modelConfigs.value.length > 0 && !selectedModelConfigId.value) {
      selectedModelConfigId.value = modelConfigs.value[0].id
    }
  } catch (error) {
    console.error('加载模型配置失败:', error)
    ElMessage.error('加载模型配置失败')
  }
}

// 加载项目列表
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    projects.value = response.data.results || response.data
    if (projects.value.length > 0) {
      projectId.value = projects.value[0].id
    }
  } catch (error) {
    console.error('获取项目列表失败:', error)
  }
}

const onProjectChange = () => {
  // 项目切换逻辑
}

// 执行任务
const handleRun = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!selectedModelConfigId.value) {
    ElMessage.warning('请先选择 AI 模型')
    return
  }
  
  const taskDesc = taskForm.description
  if (!taskDesc) {
    ElMessage.warning('请输入任务描述')
    return
  }
  
  running.value = true
  analyzing.value = true
  logs.value = '正在初始化 API Agent...\n'
  plannedTasks.value = []

  try {
      const payload = {
        project_id: projectId.value,
        task_description: taskDesc,
        execution_mode: 'api', // 关键修改：设置为 api 模式
        model_config_id: selectedModelConfigId.value,
      }

      const response = await runAdhocAITask(payload)

    currentExecutionId.value = response.data.execution_id
    ElMessage.success('任务开始执行')
    
    // 开始轮询日志
    pollLogs()
    
  } catch (error) {
    console.error('执行失败:', error)
    ElMessage.error('执行失败: ' + (error.response?.data?.error || error.message))
    running.value = false
    analyzing.value = false
  }
}

// 停止任务
const handleStop = async () => {
  if (!currentExecutionId.value) return
  
  try {
    await stopAITask(currentExecutionId.value)
    ElMessage.warning('正在停止任务...')
  } catch (error) {
    console.error('停止失败:', error)
    ElMessage.error('停止失败')
  }
}

// 轮询日志
const pollLogs = () => {
  const pollInterval = setInterval(async () => {
    if (!currentExecutionId.value) {
      clearInterval(pollInterval)
      return
    }
    
    try {
      const response = await getAIExecutionRecordDetail(currentExecutionId.value)
      const record = response.data
      
      logs.value = record.logs || ''
      plannedTasks.value = record.planned_tasks || []
      
      if (plannedTasks.value.length > 0) {
        analyzing.value = false
      }
      
      // 滚动到底部
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
      })
      
      if (record.status === 'passed' || record.status === 'failed' || record.status === 'stopped') {
        clearInterval(pollInterval)
        running.value = false
        analyzing.value = false
        if (record.status === 'passed') {
          ElMessage.success('执行成功')
        } else if (record.status === 'stopped') {
          ElMessage.warning('任务已停止')
        } else {
          ElMessage.error('执行失败')
        }
      }
    } catch (error) {
      console.error('获取日志失败:', error)
    }
  }, 2000) 
}

// 打开保存用例对话框
const handleSaveCase = () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  
  const desc = taskForm.description
  
  // 生成默认名称: AI生成API用例_YYYYMMDD_HHMM
  const now = new Date()
  const timeStr = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}`
  
  saveCaseForm.name = `AI生成API用例_${timeStr}`
  saveCaseForm.project = projectId.value
  saveCaseForm.description = desc
  
  saveCaseDialogVisible.value = true
}

// 确认保存用例
const confirmSaveCase = async () => {
  if (!saveCaseForm.name) {
    ElMessage.warning('请输入用例名称')
    return
  }
  
  savingCase.value = true
  try {
    const payload = {
      project_id: saveCaseForm.project,
      name: saveCaseForm.name,
      task_description: saveCaseForm.description,
      description: 'Created via API AI Agent',
      save_as_case: saveCaseForm.save_as_case
    }
    
    if (saveCaseForm.save_as_case) {
        // 使用专门的 API 创建端点
        await request.post('/ui-automation/ai-cases/create_api_case/', payload)
    } else {
        await createAICase(payload)
    }
    ElMessage.success('用例保存成功')
    saveCaseDialogVisible.value = false
  } catch (error) {
    console.error('保存用例失败:', error)
    ElMessage.error('保存用例失败: ' + (error.response?.data?.error || error.message))
  } finally {
    savingCase.value = false
  }
}

onMounted(() => {
  loadProjects()
  loadModelConfigs()
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  .page-title {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
  }
  
  .header-controls {
    display: flex;
    gap: 15px;
  }
}

.card-container {
  background-color: #fff;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  min-height: calc(100vh - 140px);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  padding-left: 10px;
  border-left: 4px solid #409eff;
}

.log-container {
  background-color: #1e1e1e;
  border-radius: 4px;
  height: 500px;
  overflow-y: auto;
  padding: 15px;
  color: #fff;
  font-family: 'Consolas', 'Monaco', monospace;
  
  .empty-logs {
    color: #909399;
    text-align: center;
    margin-top: 200px;
  }
  
  .log-content {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 14px;
    line-height: 1.5;
  }
}

.task-list-container {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 15px;
  height: 500px;
  overflow-y: auto;
  
  .task-item {
    display: flex;
    align-items: flex-start;
    padding: 10px;
    border-bottom: 1px solid #e4e7ed;
    transition: all 0.3s;
    
    &:last-child {
      border-bottom: none;
    }
    
    &.completed {
      background-color: #f0f9eb;
      .task-desc {
        color: #67c23a;
        text-decoration: line-through;
      }
    }
    
    &.in_progress {
      background-color: #ecf5ff;
      .task-desc {
        color: #409eff;
        font-weight: bold;
      }
    }
    
    &.failed {
      background-color: #fef0f0;
      .task-desc {
        color: #f56c6c;
      }
    }
    
    .task-status-icon {
      margin-right: 10px;
      margin-top: 2px;
      font-size: 16px;
    }
    
    .task-content {
      flex: 1;
      line-height: 1.5;
      
      .task-id {
        font-weight: bold;
        margin-right: 5px;
      }
    }
  }
}

.empty-tasks {
  color: #909399;
  text-align: center;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.analyzing-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #409eff;
  
  .el-icon {
    font-size: 24px;
    margin-bottom: 10px;
  }
}
</style>