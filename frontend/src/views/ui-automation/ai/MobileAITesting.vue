<template>
  <BasePage title="AI 智能测试实验室">
    
    <div class="card-container">
      <!-- App 移动端测试内容 -->
      <div v-if="activeTab === 'app'">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="section-title">设备选择</div>
              <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                 <el-select v-model="selectedDeviceId" placeholder="选择设备" style="width: 100%">
                    <el-option 
                      v-for="dev in devices" 
                      :key="dev?.device_id" 
                      :label="dev ? `${dev.name || 'Unknown'} (${dev.device_id})` : ''" 
                      :value="dev?.device_id" 
                      :disabled="dev?.status === 'offline'" 
                    />
                 </el-select>
                 <el-button @click="handleRefreshDevices" :loading="refreshingDevices">刷新设备</el-button>
              </div>

              <div class="section-title">任务输入</div>
              <el-form :model="appTaskForm" label-position="top">
                <el-form-item label="AI 模型配置" required>
                  <el-select v-model="selectedModelConfigId" placeholder="选择 AI 模型 (建议使用多模态模型)" style="width: 100%">
                    <el-option
                      v-for="config in modelConfigs"
                      :key="config.id"
                      :label="`${config.name} (${config.model_name})`"
                      :value="config.id"
                    >
                      <span style="float: left">{{ config.name }}</span>
                      <span style="float: right; color: #8492a6; font-size: 13px">{{ config.model_name }}</span>
                    </el-option>
                  </el-select>
                </el-form-item>

                <el-form-item label="任务描述" required>
                  <el-input
                    v-model="appTaskForm.description"
                    type="textarea"
                    :rows="10"
                    placeholder="请用自然语言描述要执行的任务，例如：&#10;1. 打开抖音&#10;2. 搜索 '测试'&#10;3. 点击第一个视频"
                    maxlength="2000"
                    show-word-limit
                  />
                </el-form-item>
                
                <el-form-item>
                  <el-button 
                    type="primary" 
                    @click="handleRun" 
                    :loading="running"
                    :disabled="!appTaskForm.description || !projectId || !selectedDeviceId || !selectedModelConfigId"
                  >
                    <el-icon><Cellphone /></el-icon>
                    开始执行 (Mobile)
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
                    :disabled="!appTaskForm.description"
                  >
                    <el-icon><DocumentAdd /></el-icon>
                    保存用例
                  </el-button>
                </el-form-item>
              </el-form>
              
              <el-alert
                title="Mobile Agent 智能化模式"
                type="success"
                :closable="false"
                style="margin-top: 20px;"
                show-icon
              >
                <template #default>
                  <div>已升级至 Mobile Agent v3.5 架构。支持：</div>
                  <div style="margin-top: 5px;">• <b>多代理协作</b>：Planning (规划) + Execution (执行)</div>
                  <div>• <b>GUI-Critic</b>：自动诊断并修正幻觉点击</div>
                  <div>• <b>操作记忆</b>：高频路径自动学习与复用</div>
                </template>
              </el-alert>
              
              <div class="section-title" style="margin-top: 20px;">
                执行状态
                <el-tag v-if="currentPlan" type="warning" size="small" style="margin-left: 10px;">当前目标: {{ currentPlan }}</el-tag>
              </div>
              <div class="log-container" ref="appLogContainer">
                <div v-if="!logs && !running" class="empty-logs">
                  暂无执行日志
                </div>
                <div v-else class="rich-logs">
                  <div v-for="(log, index) in parsedLogs" :key="index" :class="['log-line', log.type]">
                    <span class="log-time">{{ log.time }}</span>
                    <span class="log-tag" v-if="log.tag">{{ log.tag }}</span>
                    <span class="log-text">{{ log.content }}</span>
                  </div>
                </div>
              </div>
            </el-col>
            
            <el-col :span="12">
               <div class="section-title">屏幕预览</div>
               <div class="preview-container">
                  <div v-if="!selectedDeviceId" class="empty-preview">
                     <el-icon style="font-size: 48px; margin-bottom: 20px;"><Cellphone /></el-icon>
                     <div>请先选择设备以开启投屏</div>
                  </div>
                  <div v-else class="screen-mirror">
                      <img :src="previewUrl" alt="Screen Mirror" @error="handleImageError" />
                      <div class="refresh-badge">Live</div>
                  </div>
               </div>
            </el-col>
          </el-row>
      </div>

      <!-- Web 浏览器测试内容 -->
      <div v-if="activeTab === 'web'">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="section-title">任务输入</div>
              <el-form :model="webTaskForm" label-position="top">
                <el-form-item label="AI 模型配置" required>
                  <el-select v-model="selectedModelConfigId" placeholder="选择 AI 模型" style="width: 100%">
                    <el-option
                      v-for="config in modelConfigs"
                      :key="config.id"
                      :label="`${config.name} (${config.model_name})`"
                      :value="config.id"
                    >
                      <span style="float: left">{{ config.name }}</span>
                      <span style="float: right; color: #8492a6; font-size: 13px">{{ config.model_name }}</span>
                    </el-option>
                  </el-select>
                </el-form-item>
                
                <el-form-item label="任务描述" required>
                  <el-input
                    v-model="webTaskForm.description"
                    type="textarea"
                    :rows="8"
                    placeholder="请用自然语言描述要执行的任务，例如：&#10;1. 访问 https://www.baidu.com&#10;2. 搜索 'Testing'&#10;3. 点击第一条搜索结果"
                    maxlength="2000"
                    show-word-limit
                  />
                </el-form-item>

                <el-form-item label="参考图片 (可选)">
                  <el-upload
                    class="upload-demo"
                    drag
                    action="#"
                    :auto-upload="false"
                    :limit="1"
                    :on-change="(file) => webTaskForm.referenceImage = file.raw"
                    :on-remove="() => webTaskForm.referenceImage = null"
                    list-type="picture"
                  >
                    <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                    <div class="el-upload__text">
                      将文件拖到此处或 <em>点击上传</em>
                    </div>
                  </el-upload>
                </el-form-item>

                <el-row :gutter="20">
                    <el-col :span="12">
                         <el-form-item label="执行模式">
                            <el-select v-model="webTaskForm.executionMode" style="width: 100%" @change="handleWebModeChange">
                                <el-option label="Vision Web (多模态视觉)" value="vision_web" />
                                <el-option label="Standard Web (文本生成脚本)" value="text" />
                            </el-select>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="GIF录制">
                          <el-switch
                            v-model="webTaskForm.enableGif"
                            active-text="开启"
                            inactive-text="关闭"
                          />
                        </el-form-item>
                    </el-col>
                </el-row>

                <!-- GIF生成参数配置 -->
                <el-form-item label="GIF生成参数" v-if="webTaskForm.enableGif">
                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="帧率" label-width="60px">
                        <el-select v-model="webTaskForm.gifParams.frameRate" style="width: 100%">
                          <el-option label="10fps" value="10" />
                          <el-option label="15fps" value="15" />
                          <el-option label="20fps" value="20" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="分辨率" label-width="60px">
                        <el-select v-model="webTaskForm.gifParams.resolution" style="width: 100%">
                          <el-option label="1280x720" value="1280x720" />
                          <el-option label="1024x768" value="1024x768" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-form-item>

                <el-form-item>
                  <el-button 
                    type="primary" 
                    @click="handleRun" 
                    :loading="running"
                    :disabled="!webTaskForm.description || !projectId || !selectedModelConfigId"
                  >
                    <el-icon><VideoPlay /></el-icon>
                    开始执行 (Web)
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
                    :disabled="!webTaskForm.description"
                  >
                    <el-icon><DocumentAdd /></el-icon>
                    保存用例
                  </el-button>
                </el-form-item>
              </el-form>
              
              <el-alert
                v-if="webTaskForm.executionMode === 'vision_web'"
                title="Vision Web 模式 (实验性)"
                type="success"
                :closable="false"
                style="margin-top: 20px;"
                show-icon
              >
                <template #default>
                  <div>使用多模态大模型 (Vision LLM) 实时理解页面截图并执行操作。</div>
                  <div>适合复杂动态页面、Canvas 游戏或非标准控件。</div>
                </template>
              </el-alert>
              <el-alert
                v-else
                title="Browser Use 模式"
                type="info"
                :closable="false"
                style="margin-top: 20px;"
                show-icon
              >
                <template #default>
                  <div>通过 LLM 将自然语言转换为 Playwright 脚本执行。</div>
                  <div>适合标准 Web 应用，执行速度快。</div>
                </template>
              </el-alert>
              
              <div class="section-title" style="margin-top: 20px;">执行日志</div>
              <div class="log-container" ref="webLogContainer">
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
          <el-checkbox v-model="saveCaseForm.save_as_script">同时保存为 UI 自动化脚本 (Playwright)</el-checkbox>
          <div class="form-tip">
            勾选后，系统将自动把自然语言描述转换为 Playwright Python 代码。
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

  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Cellphone, SwitchButton, VideoPlay, CircleCheckFilled, CircleCheck, Loading, DocumentAdd, UploadFilled } from '@element-plus/icons-vue'
import request from '@/utils/api'
import { 
  getUiProjects, 
  runAdhocAITask, 
  getAIExecutionRecordDetail,
  stopAITask,
  getDeviceList,
  refreshDeviceList,
  createAICase
} from '@/api/ui_automation'

const route = useRoute()
const activeTab = ref('app')
const projects = ref([])
const projectId = ref('')
const devices = ref([])
const selectedDeviceId = ref('')
const refreshingDevices = ref(false)
const modelConfigs = ref([])
const selectedModelConfigId = ref('')
const previewUrl = ref('')
const previewInterval = ref(null)

const running = ref(false)
const analyzing = ref(false)
const logs = ref('')
const currentExecutionId = ref(null)
const appLogContainer = ref(null)
const webLogContainer = ref(null)
const plannedTasks = ref([])
const currentPlan = ref('')

const parsedLogs = computed(() => {
  if (!logs.value) return []
  return logs.value.split('\n').filter(line => line.trim()).map(line => {
    // 匹配类似 Step 1: [Planner] ... 或 [System] ...
    const timeMatch = line.match(/^(\d{2}:\d{2}:\d{2})/)
    const time = timeMatch ? timeMatch[1] : ''
    let content = time ? line.substring(time.length).trim() : line
    
    let type = 'default'
    let tag = ''
    
    if (content.includes('[Planner]')) {
      type = 'planner'
      tag = '规划'
      // 提取 Plan
      const planMatch = content.match(/阶段目标: (.*)/)
      if (planMatch) currentPlan.value = planMatch[1]
    } else if (content.includes('[Critic]')) {
      type = 'critic'
      tag = '诊断'
    } else if (content.includes('[Executor]')) {
      type = 'executor'
      tag = '执行'
    } else if (content.includes('[System]')) {
      type = 'system'
      tag = '系统'
    }
    
    return { time, tag, content, type }
  })
})

// 保存用例相关
const saveCaseDialogVisible = ref(false)
const savingCase = ref(false)
const saveCaseForm = reactive({
  name: '',
  project: '',
  description: '',
  save_as_script: false
})

const appTaskForm = reactive({
  description: '',
})

const webTaskForm = reactive({
  description: '',
  browserType: 'chrome',
  executionMode: 'text', // text, vision_web
  enableGif: true,
  referenceImage: null,
  gifParams: {
    frameRate: '15',
    resolution: '1280x720',
    quality: 75,
    maxDuration: 30
  }
})

const handleWebModeChange = (val) => {
    // 切换模式时自动选择合适的模型
    if (val === 'vision_web') {
        const match = modelConfigs.value.find(c => c.model_type.includes('gpt-4') || c.model_type.includes('claude-3') || c.name.toLowerCase().includes('vision'))
        if (match) selectedModelConfigId.value = match.id
    }
}

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
    
    // 自动选择一个推荐的模型
    if (modelConfigs.value.length > 0) {
      // 优先选择 role 匹配当前 Tab 的模型
      autoSelectModel()
    }
  } catch (error) {
    console.error('加载模型配置失败:', error)
    ElMessage.error('加载模型配置失败')
  }
}

// 根据当前 Tab 自动选择模型
const autoSelectModel = () => {
  if (modelConfigs.value.length === 0) return

  let preferredRole = activeTab.value === 'app' ? 'mobile_agent' : 'browser_use_text'
  
  const match = modelConfigs.value.find(c => c.role === preferredRole)
  if (match) {
    selectedModelConfigId.value = match.id
  } else {
    // Fallback: 如果没有专用的 mobile_agent，尝试找 autoglm 或 vision 模型
    const fallback = modelConfigs.value.find(c => 
      c.role === 'autoglm' || 
      c.name.toLowerCase().includes('vision') || 
      c.model_name.toLowerCase().includes('gpt-4o')
    )
    selectedModelConfigId.value = fallback ? fallback.id : modelConfigs.value[0].id
  }
}

// 监听 Tab 切换，自动调整推荐模型
watch(activeTab, () => {
  autoSelectModel()
})

// 监听路由变化，自动切换 Tab
watch(() => route.path, (newPath) => {
  if (newPath.includes('web-testing')) {
    activeTab.value = 'web'
  } else {
    activeTab.value = 'app'
  }
})

// 投屏相关逻辑
const startPreview = () => {
  stopPreview()
  if (!selectedDeviceId.value) return

  // 初始加载
  updatePreviewUrl()
  
  // 定时刷新 (1秒刷新一次，避免后端压力过大)
  previewInterval.value = setInterval(updatePreviewUrl, 1000)
}

const stopPreview = () => {
  if (previewInterval.value) {
    clearInterval(previewInterval.value)
    previewInterval.value = null
  }
}

const updatePreviewUrl = () => {
  // Find the database ID for the selected device serial
  const device = devices.value.find(d => d.device_id === selectedDeviceId.value)
  if (!device) return

  // Use the database ID (pk) for the API URL
  previewUrl.value = `/api/ui-automation/devices/${device.id}/screenshot/?t=${Date.now()}`
}

const handleImageError = () => {
  // 图片加载失败（可能是设备离线或请求超时），不处理或显示占位符
  console.warn('Screenshot load failed')
}

// 监听设备选择变化
watch(selectedDeviceId, (newVal) => {
  if (newVal) {
    startPreview()
  } else {
    stopPreview()
  }
})

// 组件销毁时停止
onUnmounted(() => {
  stopPreview()
})

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

// 加载设备列表
const loadDevices = async () => {
  try {
    const response = await getDeviceList({ page_size: 100 })
    if (response.data && Array.isArray(response.data.results)) {
      devices.value = response.data.results
    } else if (Array.isArray(response.data)) {
      devices.value = response.data
    } else {
      devices.value = []
    }
    
    // Auto select first online device
    if (devices.value.length > 0) {
        const onlineDev = devices.value.find(d => d.status !== 'offline')
        if (onlineDev) {
            selectedDeviceId.value = onlineDev.device_id
        }
    }
  } catch (error) {
    console.error('获取设备列表失败:', error)
  }
}

const handleRefreshDevices = async () => {
    refreshingDevices.value = true
    try {
        await refreshDeviceList()
        await loadDevices()
        ElMessage.success('设备列表已刷新')
    } catch (error) {
        ElMessage.error('刷新失败')
    } finally {
        refreshingDevices.value = false
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
  
  const isMobile = activeTab.value === 'app'
  
  if (isMobile && !selectedDeviceId.value) {
    ElMessage.warning('请先选择设备')
    return
  }
  
  const taskDesc = isMobile ? appTaskForm.description : webTaskForm.description
  if (!taskDesc) {
    ElMessage.warning('请输入任务描述')
    return
  }
  
  running.value = true
  analyzing.value = !isMobile // Mobile 模式暂时没有显式的分析阶段 UI
  logs.value = '正在初始化 AI Agent...\n'
  plannedTasks.value = []

  try {
      let payload;
      
      // 如果有图片，使用 FormData
      if (!isMobile && webTaskForm.referenceImage) {
          payload = new FormData();
          payload.append('project_id', projectId.value);
          payload.append('task_description', taskDesc);
          payload.append('execution_mode', webTaskForm.executionMode);
          payload.append('model_config_id', selectedModelConfigId.value);
          if (webTaskForm.browserType) payload.append('browser_type', webTaskForm.browserType);
          payload.append('enable_gif', webTaskForm.enableGif);
          payload.append('reference_image', webTaskForm.referenceImage);
          // GIF Params handling if needed
      } else {
          payload = {
            project_id: projectId.value,
            task_description: taskDesc,
            execution_mode: isMobile ? 'mobile' : webTaskForm.executionMode,
            model_config_id: selectedModelConfigId.value, // 传递模型配置ID
            device_id: isMobile ? selectedDeviceId.value : null,
            browser_type: isMobile ? null : webTaskForm.browserType, // 传递浏览器类型
            enable_gif: isMobile ? false : webTaskForm.enableGif,
            gif_params: isMobile ? null : webTaskForm.gifParams
          }
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
        const container = activeTab.value === 'app' ? appLogContainer.value : webLogContainer.value
        if (container) {
          container.scrollTop = container.scrollHeight
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
  
  const isMobile = activeTab.value === 'app'
  const desc = isMobile ? appTaskForm.description : webTaskForm.description
  
  // 生成默认名称: AI生成用例_YYYYMMDD_HHMM
  const now = new Date()
  const timeStr = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}`
  
  saveCaseForm.name = `AI生成用例_${timeStr}`
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
    const isMobile = activeTab.value === 'app'
    const payload = {
      project_id: saveCaseForm.project,
      name: saveCaseForm.name,
      // saveCaseForm.description 实际上是任务描述（Prompt）
      task_description: saveCaseForm.description,
      description: '', // 可选的备注描述，暂时留空
      execution_mode: isMobile ? 'mobile' : 'web', // 显式传递 execution_mode
      save_as_script: saveCaseForm.save_as_script
    }
    
    await createAICase(payload)
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
  // 根据路由设置初始 Tab
  if (route.path.includes('web-testing')) {
    activeTab.value = 'web'
  } else {
    activeTab.value = 'app'
  }

  loadProjects()
  loadDevices()
  loadModelConfigs()
})
</script>

<style lang="scss" scoped>

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
  padding: 15px;
  height: 400px;
  overflow-y: auto;
  color: #d4d4d4;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;

  .empty-logs {
    color: #909399;
    text-align: center;
    margin-top: 150px;
  }

  .log-content {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 14px;
    line-height: 1.5;
  }

  .rich-logs {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .log-line {
    display: flex;
    gap: 10px;
    align-items: flex-start;

    .log-time { color: #858585; min-width: 60px; }
    .log-tag {
      padding: 0 4px;
      border-radius: 2px;
      font-size: 11px;
      min-width: 40px;
      text-align: center;
      color: #fff;
    }
    
    &.planner .log-tag { background-color: #e6a23c; }
    &.critic .log-tag { background-color: #f56c6c; }
    &.executor .log-tag { background-color: #409eff; }
    &.system .log-tag { background-color: #909399; }
    
    &.planner .log-text { color: #e6a23c; font-weight: bold; }
    &.critic.warning .log-text { color: #f56c6c; }
  }
}

.preview-container {
    background-color: #f5f7fa;
    border-radius: 4px;
    height: 600px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px dashed #dcdfe6;

    .empty-preview {
        text-align: center;
        color: #909399;
    }

    .screen-mirror {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        background-color: #000;

        img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }

        .refresh-badge {
            position: absolute;
            top: 10px;
            right: 10px;
            background-color: rgba(255, 0, 0, 0.7);
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            animation: pulse 2s infinite;
        }
    }
}

@keyframes pulse {
    0% { opacity: 0.5; }
    50% { opacity: 1; }
    100% { opacity: 0.5; }
}

.task-list-container {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 15px;
  height: 400px;
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