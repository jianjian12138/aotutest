<template>
  <BasePage title="智能用例生成">

    <div class="card-container main-content">
      <!-- 输入方式选择 + 手动输入需求描述 -->
      <div v-if="!isGenerating && !showResults" class="manual-input-card">

        <!-- 输入方式 Tab -->
        <el-tabs v-model="inputMode" class="input-mode-tabs">
          <el-tab-pane label="✍️ 手动输入需求" name="manual">
            <div class="form-group" style="margin-top:16px">
              <label>需求标题 <span class="required">*</span></label>
              <el-input 
                v-model="manualTitle" 
                placeholder="请输入需求标题，如：用户登录功能需求"
                :class="{ 'is-error': errors.title }"
              />
              <span v-if="errors.title" class="error-message">{{ errors.title }}</span>
            </div>
            
            <div class="form-group">
              <label>需求描述 <span class="required">*</span></label>
              <el-input 
                v-model="manualDescription" 
                type="textarea"
                :rows="10"
                placeholder="请详细描述您的需求，包括功能描述、使用场景、业务流程等。"
                :class="{ 'is-error': errors.description }"
              />
              <span v-if="errors.description" class="error-message">{{ errors.description }}</span>
              <div class="char-count">{{ manualDescription.length }}/2000</div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="📋 从需求管理选择" name="from_requirement">
            <div style="margin-top:16px">
              <!-- 过滤条件 -->
              <div class="req-filter-row">
                <el-input
                  v-model="reqSearchKeyword"
                  placeholder="搜索需求名称或编号..."
                  clearable
                  style="width:260px"
                  @input="onReqSearch"
                >
                  <template #prefix><el-icon><Search /></el-icon></template>
                </el-input>
                <el-select v-model="reqFilterProject" placeholder="按项目筛选" clearable style="width:200px" @change="fetchRequirements">
                  <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
                </el-select>
                <el-select v-model="reqFilterType" placeholder="按类型筛选" clearable style="width:160px" @change="fetchRequirements">
                  <el-option label="功能需求" value="functional" />
                  <el-option label="性能需求" value="performance" />
                  <el-option label="安全需求" value="security" />
                  <el-option label="接口需求" value="interface" />
                  <el-option label="其他需求" value="other" />
                </el-select>
              </div>

              <!-- 需求列表 -->
              <el-table
                v-loading="reqLoading"
                :data="requirementList"
                border
                style="width:100%; margin-top:12px"
                height="340"
                @row-click="onReqRowClick"
                :row-class-name="reqRowClassName"
                highlight-current-row
              >
                <el-table-column width="44" align="center">
                  <template #default="scope">
                    <el-radio
                      :model-value="selectedRequirementId"
                      :label="scope.row.id"
                      @change="selectRequirement(scope.row)"
                    ></el-radio>
                  </template>
                </el-table-column>
                <el-table-column prop="requirement_id" label="编号" width="110" />
                <el-table-column prop="requirement_name" label="需求名称" min-width="200" show-overflow-tooltip />
                <el-table-column prop="module" label="模块" width="120" show-overflow-tooltip />
                <el-table-column label="类型" width="100">
                  <template #default="scope">
                    <el-tag size="small" type="info">{{ reqTypeLabel(scope.row.requirement_type) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="优先级" width="80" align="center">
                  <template #default="scope">
                    <el-tag size="small" :type="scope.row.requirement_level === 'high' ? 'danger' : scope.row.requirement_level === 'medium' ? 'warning' : 'success'">
                      {{ scope.row.requirement_level === 'high' ? '高' : scope.row.requirement_level === 'medium' ? '中' : '低' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>

              <!-- 分页 -->
              <div style="margin-top:10px; display:flex; justify-content:flex-end">
                <el-pagination
                  small
                  layout="total, prev, pager, next"
                  :total="reqTotal"
                  :page-size="reqPageSize"
                  :current-page="reqPage"
                  @current-change="onReqPageChange"
                />
              </div>

              <!-- 已选需求预览 -->
              <div v-if="selectedRequirement" class="selected-req-preview">
                <div class="preview-header">
                  <el-icon style="color:#409eff"><CircleCheck /></el-icon>
                  <span>已选需求：<strong>{{ selectedRequirement.requirement_id }} {{ selectedRequirement.requirement_name }}</strong></span>
                </div>
                <div class="preview-desc">
                  <label>需求描述：</label>
                  <p>{{ selectedRequirement.description }}</p>
                </div>
                <div v-if="selectedRequirement.acceptance_criteria" class="preview-desc">
                  <label>验收标准：</label>
                  <p>{{ selectedRequirement.acceptance_criteria }}</p>
                </div>
              </div>
              <el-empty v-else description="请在上方列表选择一条需求" :image-size="60" style="padding:20px 0" />
            </div>
          </el-tab-pane>
        </el-tabs>
        
        <div class="form-row" style="margin-top:20px">
          <div class="form-group half">
            <label>关联项目 (可选)</label>
            <el-select v-model="selectedProject" placeholder="请选择项目" style="width: 100%" clearable>
              <el-option 
                v-for="project in projects" 
                :key="project.id" 
                :label="project.name" 
                :value="project.id"
              />
            </el-select>
          </div>
          <div class="form-group half">
            <label>提示词模板 (可选)</label>
            <el-select v-model="selectedPromptConfig" placeholder="默认提示词" style="width: 100%" clearable>
              <el-option 
                v-for="config in promptConfigs" 
                :key="config.id" 
                :label="config.name" 
                :value="config.id"
              />
            </el-select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>选择模型 (可选)</label>
            <el-select v-model="selectedModelConfig" placeholder="选择 AI 模型" style="width: 100%" clearable>
              <el-option 
                v-for="model in modelConfigs" 
                :key="model.id" 
                :label="model.name" 
                :value="model.id"
              >
                <span>{{ model.name }}</span>
                <span style="float: right; color: #8492a6; font-size: 13px">{{ model.model_type }}</span>
              </el-option>
            </el-select>
          </div>
        </div>

        <div class="form-group">
          <label>关联知识库文档 (增强生成准确性，可选)</label>
          <el-select
            v-model="selectedKnowledgeDocs"
            multiple
            filterable
            remote
            reserve-keyword
            placeholder="请输入文档名称搜索"
            :remote-method="searchKnowledgeDocs"
            :loading="knowledgeDocsLoading"
            style="width: 100%"
          >
            <el-option
              v-for="doc in knowledgeDocs"
              :key="doc.id"
              :label="doc.name"
              :value="doc.id"
            >
              <span>{{ doc.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ formatFileSize(doc.size) }}</span>
            </el-option>
          </el-select>
          <div class="help-text">选中知识库文档将作为生成的参考上下文。</div>
        </div>

        <div class="form-actions">
          <el-button type="primary" size="large" @click="startGeneration" :loading="isGenerating" style="width: 100%">
            🚀 生成测试用例
          </el-button>
        </div>
      </div>

      <!-- 生成进度 -->
      <div v-if="isGenerating" class="generation-progress">
        <div class="progress-card">
          <h3>🤖 AI正在为您生成测试用例</h3>
          <div class="progress-info">
            <div class="progress-item">
              <span class="label">任务ID:</span>
              <span class="value">{{ currentTaskId || '准备中...' }}</span>
            </div>
            <div class="progress-item">
              <span class="label">当前状态:</span>
              <span class="value">{{ progressText }}</span>
            </div>
          </div>
          <div class="progress-steps">
            <div class="step" :class="{ active: currentStep >= 1 }">
              <span class="step-number">1</span>
              <span class="step-text">需求分析</span>
            </div>
            <div class="step" :class="{ active: currentStep >= 2 }">
              <span class="step-number">2</span>
              <span class="step-text">用例编写</span>
            </div>
            <div class="step" :class="{ active: currentStep >= 3 }">
              <span class="step-number">3</span>
              <span class="step-text">用例评审</span>
            </div>
            <div class="step" :class="{ active: currentStep >= 4 }">
              <span class="step-number">4</span>
              <span class="step-text">完成</span>
            </div>
          </div>
          <el-button type="danger" @click="cancelGeneration">取消生成</el-button>
        </div>
      </div>

      <!-- 生成结果 -->
      <div v-if="showResults && generationResult" class="generation-result">
        <div class="result-header">
          <h2>✅ 测试用例生成完成</h2>
          <div class="header-buttons">
            <el-button type="success" @click="downloadTestCases">📥 下载用例</el-button>
            <el-button type="primary" @click="saveToTestCaseRecords">💾 保存用例</el-button>
            <el-button @click="resetGeneration">📝 重新生成</el-button>
          </div>
        </div>
        
        <div class="result-summary-bar">
          <span class="summary-item">📊 任务ID: {{ generationResult.task_id }}</span>
          <span class="summary-item">⏱️ 生成时间: {{ formatDateTime(generationResult.completed_at) }}</span>
        </div>

        <div class="generated-testcases-section">
          <h3>📋 生成的测试用例</h3>
          <div class="testcase-content" v-html="generationResult.generated_test_cases"></div>
        </div>

        <div v-if="generationResult.review_feedback" class="review-feedback-section">
          <h3>🔍 AI评审意见</h3>
          <div class="review-content">
            <pre>{{ generationResult.review_feedback }}</pre>
          </div>
        </div>

        <div v-if="generationResult.final_test_cases" class="final-testcases-section">
          <h3>🎯 最终测试用例</h3>
          <div class="testcase-content" v-html="generationResult.final_test_cases"></div>
        </div>
      </div>
    </div>

  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, CircleCheck } from '@element-plus/icons-vue'
import api from '@/utils/api'

// State
const isGenerating = ref(false)
const showResults = ref(false)
const currentStep = ref(0)
const progressText = ref('')
const currentTaskId = ref('')
const generationResult = ref(null)
const pollInterval = ref(null)

// 输入方式：manual | from_requirement
const inputMode = ref('manual')

// Manual Input
const manualTitle = ref('')
const manualDescription = ref('')
const selectedProject = ref('')
const selectedPromptConfig = ref('')
const selectedModelConfig = ref('')
const selectedKnowledgeDocs = ref([])
const errors = reactive({
  title: '',
  description: ''
})

// 从需求选择
const reqLoading = ref(false)
const requirementList = ref([])
const reqTotal = ref(0)
const reqPage = ref(1)
const reqPageSize = ref(10)
const reqSearchKeyword = ref('')
const reqFilterProject = ref('')
const reqFilterType = ref('')
const selectedRequirementId = ref(null)
const selectedRequirement = ref(null)
let reqSearchTimer = null

// Data Sources
const projects = ref([])
const promptConfigs = ref([])
const modelConfigs = ref([])
const knowledgeDocs = ref([])
const knowledgeDocsLoading = ref(false)

// Lifecycle
onMounted(async () => {
  await fetchProjects()
  await fetchPromptConfigs()
  await fetchModelConfigs()
  await searchKnowledgeDocs('')
  await fetchRequirements()
})

onBeforeUnmount(() => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }
})

// API Calls
const fetchProjects = async () => {
  try {
    const res = await api.get('/projects/')
    projects.value = res.data.results || res.data
  } catch (err) {
    console.error('Failed to fetch projects', err)
  }
}

const fetchPromptConfigs = async () => {
  try {
    const res = await api.get('/requirement-analysis/api/prompts/')
    const results = res.data.results || res.data
    promptConfigs.value = results.filter(p => p.is_active && p.prompt_type === 'writer')
  } catch (err) {
    console.error('Failed to fetch prompt configs', err)
  }
}

const fetchModelConfigs = async () => {
  try {
    const res = await api.get('/requirement-analysis/api/ai-models/', { params: { is_active: true } })
    modelConfigs.value = res.data.results || res.data
    if (modelConfigs.value.length > 0) {
      const defaultModel = modelConfigs.value.find(m => m.model_type === 'deepseek') || modelConfigs.value[0]
      selectedModelConfig.value = defaultModel.id
    }
  } catch (err) {
    console.error('Failed to fetch model configs', err)
  }
}

const searchKnowledgeDocs = async (query) => {
  knowledgeDocsLoading.value = true
  try {
    const params = { page_size: 20 }
    if (query) {
      params.search = query
    }
    const res = await api.get('/knowledge-graph/api/documents/', { 
      params: params
    })
    knowledgeDocs.value = res.data.results || res.data
  } catch (err) {
    console.error('Failed to search knowledge docs', err)
    knowledgeDocs.value = [] 
  } finally {
    knowledgeDocsLoading.value = false
  }
}

// 需求列表
const fetchRequirements = async () => {
  reqLoading.value = true
  try {
    const params = {
      page: reqPage.value,
      page_size: reqPageSize.value,
    }
    if (reqSearchKeyword.value) params.search = reqSearchKeyword.value
    if (reqFilterProject.value) params.project = reqFilterProject.value
    if (reqFilterType.value) params.requirement_type = reqFilterType.value
    const res = await api.get('/requirement-analysis/api/requirements/', { params })
    const data = res.data
    requirementList.value = data.results || data
    reqTotal.value = data.count || requirementList.value.length
  } catch (err) {
    console.error('Failed to fetch requirements', err)
    ElMessage.error('获取需求列表失败')
  } finally {
    reqLoading.value = false
  }
}

const onReqSearch = () => {
  clearTimeout(reqSearchTimer)
  reqSearchTimer = setTimeout(() => {
    reqPage.value = 1
    fetchRequirements()
  }, 400)
}

const onReqPageChange = (page) => {
  reqPage.value = page
  fetchRequirements()
}

const selectRequirement = (row) => {
  selectedRequirementId.value = row.id
  selectedRequirement.value = row
}

const onReqRowClick = (row) => {
  selectRequirement(row)
}

const reqRowClassName = ({ row }) => {
  return row.id === selectedRequirementId.value ? 'selected-row' : ''
}

const reqTypeLabel = (type) => {
  const map = {
    functional: '功能需求',
    performance: '性能需求',
    security: '安全需求',
    usability: '可用性需求',
    interface: '接口需求',
    other: '其他需求',
  }
  return map[type] || type
}

// Actions
const startGeneration = async () => {
  let title = ''
  let description = ''

  if (inputMode.value === 'manual') {
    errors.title = !manualTitle.value ? '请输入需求标题' : ''
    errors.description = !manualDescription.value ? '请输入需求描述' : ''
    if (errors.title || errors.description) return
    title = manualTitle.value
    description = manualDescription.value
  } else {
    if (!selectedRequirement.value) {
      ElMessage.warning('请在需求列表中选择一条需求')
      return
    }
    title = selectedRequirement.value.requirement_name
    description = [
      selectedRequirement.value.description,
      selectedRequirement.value.acceptance_criteria
        ? `验收标准：${selectedRequirement.value.acceptance_criteria}`
        : ''
    ].filter(Boolean).join('\n\n')
  }

  isGenerating.value = true
  showResults.value = false
  currentStep.value = 1
  progressText.value = '正在创建生成任务...'

  try {
    const payload = {
      title,
      requirement_text: description,
      project: selectedProject.value || null,
      prompt_config_id: selectedPromptConfig.value || null,
      knowledge_base_ids: selectedKnowledgeDocs.value,
      writer_model_config_id: selectedModelConfig.value || null,
      use_writer_model: true,
      use_reviewer_model: true
    }

    const res = await api.post('/requirement-analysis/api/testcase-generation/generate/', payload)
    currentTaskId.value = res.data.task_id
    startPolling(res.data.task_id)
  } catch (err) {
    console.error('Generation failed', err)
    ElMessage.error('创建任务失败: ' + (err.response?.data?.error || err.message))
    isGenerating.value = false
  }
}

const startPolling = (taskId) => {
  pollInterval.value = setInterval(async () => {
    try {
      const res = await api.get(`/requirement-analysis/api/testcase-generation/${taskId}/progress/`)
      const data = res.data
      
      if (data.status === 'generating') {
        currentStep.value = 2
        progressText.value = `正在编写测试用例... (${data.progress}%)`
      } else if (data.status === 'reviewing') {
        currentStep.value = 3
        progressText.value = '正在评审测试用例...'
      } else if (data.status === 'completed') {
        currentStep.value = 4
        progressText.value = '生成完成！'
        generationResult.value = data
        clearInterval(pollInterval.value)
        setTimeout(() => {
          isGenerating.value = false
          showResults.value = true
        }, 1000)
      } else if (data.status === 'failed') {
        clearInterval(pollInterval.value)
        isGenerating.value = false
        ElMessage.error('生成失败: ' + data.error_message)
      }
    } catch (err) {
      console.error('Poll failed', err)
    }
  }, 3000)
}

const cancelGeneration = () => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }
  isGenerating.value = false
  ElMessage.info('已取消生成任务')
}

const resetGeneration = () => {
  showResults.value = false
  manualTitle.value = ''
  manualDescription.value = ''
  selectedProject.value = ''
  selectedPromptConfig.value = ''
  selectedKnowledgeDocs.value = []
  selectedRequirement.value = null
  selectedRequirementId.value = null
}

const downloadTestCases = () => {
  if (!generationResult.value?.task_id) return
  window.open(`${api.defaults.baseURL}/requirement-analysis/api/testcase-generation/${generationResult.value.task_id}/export_cases/`, '_blank')
}

const saveToTestCaseRecords = async () => {
  if (!generationResult.value?.task_id) return
  try {
    await api.post(`/requirement-analysis/api/testcase-generation/${generationResult.value.task_id}/save_to_records/`, {
      project_id: selectedProject.value
    })
    ElMessage.success('保存成功')
  } catch (err) {
    ElMessage.error('保存失败')
  }
}

// Utils
const formatDateTime = (val) => {
  if (!val) return '-'
  return new Date(val).toLocaleString()
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>

.manual-input-card {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
}
.form-group {
  margin-bottom: 20px;
}
.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}
.form-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}
.half {
  flex: 1;
}
.error-message {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 5px;
  display: block;
}
.char-count {
  text-align: right;
  font-size: 12px;
  color: #909399;
}
.help-text {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
.required {
  color: #f56c6c;
}
.generation-progress {
  text-align: center;
  padding: 50px 0;
}
.progress-steps {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin: 30px 0;
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  opacity: 0.3;
}
.step.active {
  opacity: 1;
}
.step-number {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #409eff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 5px;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.result-summary-bar {
  margin-bottom: 20px;
  color: #606266;
}


.summary-item {
  margin-right: 20px;
}
.testcase-content {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-top: 10px;
}
.review-content pre {
  white-space: pre-wrap;
  background: #fef0f0;
  padding: 15px;
  border-radius: 8px;
  color: #f56c6c;
}

.input-mode-tabs {
  margin-bottom: 0;
}

.req-filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.selected-req-preview {
  margin-top: 16px;
  background: #f0f7ff;
  border: 1px solid #b3d8ff;
  border-radius: 8px;
  padding: 14px 18px;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  margin-bottom: 10px;
}

.preview-desc {
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}

.preview-desc label {
  font-weight: 600;
  color: #303133;
  display: inline;
}

.preview-desc p {
  margin: 4px 0 0 0;
  line-height: 1.6;
  white-space: pre-wrap;
}

:deep(.el-table .selected-row) {
  background: #ecf5ff !important;
}

:deep(.el-table tr) {
  cursor: pointer;
}
</style>
