<template>
  <BasePage title="Agent Browser 自治测试">
    <div class="agent-browser-container">
      <el-row :gutter="20">

        <!-- ═══ 左侧：配置面板 ═══ -->
        <el-col :span="7">
          <PremiumCard class="config-panel" hover-effect>
            <div class="panel-title">
              <el-icon><Setting /></el-icon> 任务配置
            </div>

            <el-form label-position="top" size="default">
              <el-form-item label="AI 模型">
                <el-select v-model="selectedModelConfigId" placeholder="选择 AI 模型（建议多模态）" style="width:100%">
                  <el-option
                    v-for="m in modelConfigs"
                    :key="m.id"
                    :label="`${m.name} (${m.model_name})`"
                    :value="m.id"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="起始 URL *">
                <el-input v-model="startUrl" placeholder="https://example.com" clearable />
              </el-form-item>

              <el-form-item label="任务描述（自然语言）*">
                <el-input
                  v-model="taskDescription"
                  type="textarea"
                  :rows="6"
                  placeholder="用自然语言描述要执行的完整测试任务，例如：
登录账号 admin / admin123，进入用户管理页面，新建用户 testuser，然后验证用户列表中出现 testuser。"
                  maxlength="1000"
                  show-word-limit
                />
              </el-form-item>

              <el-divider content-position="left">高级选项</el-divider>

              <el-form-item>
                <div class="switch-row">
                  <span class="switch-label">
                    <el-icon><Promotion /></el-icon>
                    规划阶段
                    <el-tooltip content="先让 LLM 将任务分解为有序子步骤，再逐步执行（对标 Loadmill E2E 规划）" placement="right">
                      <el-icon class="tip-icon"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </span>
                  <el-switch v-model="enablePlanning" />
                </div>
              </el-form-item>

              <el-form-item>
                <div class="switch-row">
                  <span class="switch-label">
                    <el-icon><Document /></el-icon>
                    生成可回放脚本
                    <el-tooltip content="执行结束后自动生成 Playwright Python 脚本，可直接复用（对标 Loadmill 脚本生成）" placement="right">
                      <el-icon class="tip-icon"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </span>
                  <el-switch v-model="enableScriptGen" />
                </div>
              </el-form-item>

              <el-form-item>
                <div class="switch-row">
                  <span class="switch-label">
                    <el-icon><PictureFilled /></el-icon>
                    视觉回归对比
                    <el-tooltip content="将每步截图与基线截图对比，自动检测布局偏移、颜色偏差等视觉缺陷（对标 Applitools）" placement="right">
                      <el-icon class="tip-icon"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </span>
                  <el-switch v-model="enableVisualDiff" />
                </div>
              </el-form-item>

              <!-- 基线截图上传（仅视觉回归开启时显示） -->
              <el-form-item v-if="enableVisualDiff" label="基线截图">
                <el-upload
                  action="#"
                  :auto-upload="false"
                  :limit="1"
                  accept="image/*"
                  list-type="picture-card"
                  :on-change="handleBaselineChange"
                  :on-remove="() => { baselineB64 = ''; baselinePreview = '' }"
                >
                  <el-icon><Plus /></el-icon>
                  <template #tip>
                    <div class="el-upload__tip">上传基准页面截图用于视觉对比</div>
                  </template>
                </el-upload>
              </el-form-item>

              <el-divider />

              <el-button
                type="primary"
                style="width:100%"
                :loading="running"
                :disabled="!startUrl || !taskDescription"
                @click="runAgent"
              >
                <el-icon><VideoPlay /></el-icon>
                &nbsp;启动 Agent Browser
              </el-button>

              <el-button
                v-if="running"
                type="danger"
                style="width:100%; margin-top:10px"
                @click="stopAgent"
              >
                <el-icon><VideoPause /></el-icon>
                &nbsp;停止执行
              </el-button>

              <el-divider content-position="left">快捷生成</el-divider>
              <el-button
                style="width:100%"
                :loading="generatingScript"
                :disabled="!startUrl || !taskDescription"
                @click="generateScriptOnly"
              >
                <el-icon><MagicStick /></el-icon>
                &nbsp;仅生成脚本（不执行）
              </el-button>
            </el-form>
          </PremiumCard>
        </el-col>

        <!-- ═══ 中间：执行监视器 ═══ -->
        <el-col :span="10">
          <PremiumCard class="monitor-panel" hover-effect>
            <div class="panel-title">
              <el-icon><Monitor /></el-icon>
              执行监视器
              <el-tag v-if="running" type="warning" effect="plain" size="small" style="margin-left:8px">
                <span class="pulse-dot"></span> 运行中
              </el-tag>
              <el-tag v-else-if="finalStatus === 'passed'" type="success" effect="plain" size="small" style="margin-left:8px">完成</el-tag>
              <el-tag v-else-if="finalStatus === 'failed'" type="danger" effect="plain" size="small" style="margin-left:8px">失败</el-tag>
            </div>

            <!-- 规划阶段子步骤 -->
            <div v-if="planSteps.length > 0" class="plan-section">
              <div class="sub-title">
                <el-icon><Promotion /></el-icon> 规划：{{ planSteps.length }} 个子步骤
              </div>
              <div class="plan-steps">
                <div
                  v-for="(step, idx) in planSteps"
                  :key="idx"
                  class="plan-step-item"
                  :class="{ 'done': idx < currentStepCount }"
                >
                  <span class="plan-idx">{{ idx + 1 }}</span>
                  <span>{{ step }}</span>
                </div>
              </div>
            </div>

            <!-- 执行步骤流 -->
            <div v-if="executionSteps.length > 0" class="steps-section">
              <div class="sub-title">
                <el-icon><List /></el-icon> 执行步骤（{{ executionSteps.length }} 步）
              </div>
              <div class="steps-list" ref="stepsListRef">
                <div
                  v-for="(s, idx) in executionSteps"
                  :key="idx"
                  class="step-item"
                >
                  <div class="step-left">
                    <div class="step-num">{{ s.step }}</div>
                    <div class="step-action-badge" :class="s.action?.type">{{ s.action?.type || '?' }}</div>
                  </div>
                  <div class="step-body">
                    <div class="step-desc">{{ s.action?.description || s.content }}</div>
                    <el-image
                      v-if="s.screenshot_url"
                      :src="s.screenshot_url"
                      :preview-src-list="[s.screenshot_url]"
                      fit="cover"
                      class="step-thumb"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- 视觉回归报告 -->
            <div v-if="visualDiffResults.length > 0" class="diff-section">
              <div class="sub-title">
                <el-icon><PictureFilled /></el-icon> 视觉差异报告（{{ visualDiffResults.length }} 处）
              </div>
              <div v-for="(d, idx) in visualDiffResults" :key="idx" class="diff-item">
                <el-alert
                  :title="`步骤 ${d.step || idx+1}：${d.message || d.content}`"
                  :type="d.diff_ratio > 5 ? 'error' : 'warning'"
                  show-icon
                  :closable="false"
                  style="margin-bottom:6px"
                />
                <el-image
                  v-if="d.diff_image_url"
                  :src="d.diff_image_url"
                  :preview-src-list="[d.diff_image_url]"
                  fit="contain"
                  style="width:100%; max-height:120px; border:1px solid #ddd; border-radius:4px;"
                />
              </div>
            </div>

            <!-- 日志 -->
            <div class="log-section">
              <div class="sub-title">
                <el-icon><Tickets /></el-icon> 执行日志
              </div>
              <div class="log-box" ref="logBoxRef">
                <div v-if="logs.length === 0" class="log-empty">等待执行...</div>
                <div v-for="(l, idx) in logs" :key="idx" class="log-line" :class="l.level">
                  <span class="log-time">{{ l.time }}</span>
                  {{ l.text }}
                </div>
              </div>
            </div>
          </PremiumCard>
        </el-col>

        <!-- ═══ 右侧：生成产出 ═══ -->
        <el-col :span="7">
          <PremiumCard class="output-panel" hover-effect>
            <div class="panel-title">
              <el-icon><Document /></el-icon> 生成产出
            </div>

            <!-- 无产出时提示 -->
            <el-empty
              v-if="!generatedScript && !running"
              description="执行完成后，此处将显示生成的 Playwright 脚本"
              :image-size="80"
            />

            <!-- 生成的脚本 -->
            <template v-if="generatedScript">
              <div class="script-header">
                <span class="script-label">Playwright Python 脚本</span>
                <div class="script-actions">
                  <el-button size="small" @click="copyScript">
                    <el-icon><CopyDocument /></el-icon> 复制
                  </el-button>
                  <el-button size="small" type="success" @click="downloadScript">
                    <el-icon><Download /></el-icon> 下载 .py
                  </el-button>
                  <el-button size="small" type="primary" @click="saveScriptToSystem">
                    <el-icon><DocumentAdd /></el-icon> 保存为测试脚本
                  </el-button>
                </div>
              </div>
              <div class="script-block">
                <pre><code>{{ generatedScript }}</code></pre>
              </div>
            </template>

            <!-- 统计信息 -->
            <div v-if="finalStatus" class="stats-block">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="状态">
                  <el-tag :type="finalStatus === 'passed' ? 'success' : 'danger'" size="small">{{ finalStatus }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="执行步骤">{{ executionSteps.length }} 步</el-descriptions-item>
                <el-descriptions-item label="视觉异常">{{ visualDiffResults.length }} 处</el-descriptions-item>
                <el-descriptions-item label="脚本行数">{{ generatedScript ? generatedScript.split('\n').length : 0 }} 行</el-descriptions-item>
              </el-descriptions>
            </div>
          </PremiumCard>
        </el-col>

      </el-row>
    </div>
  </BasePage>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Setting, Monitor, Document, Promotion, PictureFilled, QuestionFilled,
  Plus, VideoPlay, VideoPause, MagicStick, List, Tickets,
  CopyDocument, Download, DocumentAdd
} from '@element-plus/icons-vue'
import request, { authFetch } from '@/utils/api'
import { useUserStore } from '@/stores/user'
import PremiumCard from '@/components/Premium/PremiumCard.vue'

// ── 配置状态 ──────────────────────────────────────────────────
const modelConfigs = ref([])
const selectedModelConfigId = ref(null)
const startUrl = ref('')
const taskDescription = ref('')
const enablePlanning = ref(true)
const enableScriptGen = ref(true)
const enableVisualDiff = ref(false)
const baselineB64 = ref('')
const baselinePreview = ref('')

// ── 执行状态 ──────────────────────────────────────────────────
const running = ref(false)
const finalStatus = ref('')
const planSteps = ref([])
const executionSteps = ref([])
const visualDiffResults = ref([])
const currentStepCount = ref(0)
const logs = ref([])
const generatedScript = ref('')
const generatingScript = ref(false)

// ── DOM refs ───────────────────────────────────────────────────
const stepsListRef = ref(null)
const logBoxRef = ref(null)

let eventSource = null

// ── 生命周期 ───────────────────────────────────────────────────
onMounted(() => {
  loadModelConfigs()
})

// ── 方法 ───────────────────────────────────────────────────────
const loadModelConfigs = async () => {
  try {
    const res = await request.get('/requirement-analysis/api/ai-models/', { params: { is_active: true } })
    modelConfigs.value = res.data.results || res.data
    if (modelConfigs.value.length > 0) {
      const pref = modelConfigs.value.find(m =>
        m.model_name?.toLowerCase().includes('gpt-4') ||
        m.model_name?.toLowerCase().includes('vision') ||
        m.model_type === 'vision'
      ) || modelConfigs.value[0]
      selectedModelConfigId.value = pref.id
    }
  } catch (e) {
    console.error('Failed to load model configs', e)
  }
}

const resetExecution = () => {
  planSteps.value = []
  executionSteps.value = []
  visualDiffResults.value = []
  logs.value = []
  generatedScript.value = ''
  finalStatus.value = ''
  currentStepCount.value = 0
}

const addLog = (text, level = 'info') => {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`
  logs.value.push({ text, time, level })
  nextTick(() => {
    if (logBoxRef.value) {
      logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight
    }
  })
}

const scrollStepsToBottom = () => {
  nextTick(() => {
    if (stepsListRef.value) {
      stepsListRef.value.scrollTop = stepsListRef.value.scrollHeight
    }
  })
}

const runAgent = () => {
  if (!startUrl.value || !taskDescription.value) {
    ElMessage.warning('请填写起始 URL 和任务描述')
    return
  }

  resetExecution()
  running.value = true

  // 使用 POST 触发后端，然后通过 SSE 接收事件
  // 由于 EventSource 不支持 POST body，改用 fetch + ReadableStream
  const payload = {
    url: startUrl.value,
    task_description: taskDescription.value,
    model_config_id: selectedModelConfigId.value,
    enable_planning: enablePlanning.value,
    enable_script_gen: enableScriptGen.value,
    enable_visual_diff: enableVisualDiff.value,
    baseline_screenshot_b64: baselineB64.value || '',
  }

  const token = useUserStore().accessToken || ''
  const apiBase = request.defaults.baseURL || '/api'

  addLog('正在启动 Agent Browser...', 'info')

  authFetch(`${apiBase}/ui-automation/ai-execution-records/run_agent_browser/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify(payload)
  }).then(res => {
    if (!res.ok) {
      res.json().then(d => {
        addLog(`启动失败: ${d.error || res.statusText}`, 'error')
        running.value = false
      })
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const read = () => {
      reader.read().then(({ done, value }) => {
        if (done) {
          running.value = false
          return
        }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()  // 保留不完整的行
        lines.forEach(line => {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              handleSseEvent(data)
            } catch (e) { /* ignore parse error */ }
          }
        })
        read()
      }).catch(err => {
        addLog(`连接断开: ${err.message}`, 'error')
        running.value = false
      })
    }
    read()
  }).catch(err => {
    addLog(`请求失败: ${err.message}`, 'error')
    running.value = false
  })
}

const handleSseEvent = (data) => {
  const type = data.type
  if (type === 'planning') {
    planSteps.value = data.steps || []
    addLog(`规划完成：${planSteps.value.length} 个子步骤`, 'info')
  } else if (type === 'step') {
    executionSteps.value.push(data)
    currentStepCount.value = data.step || executionSteps.value.length
    addLog(`[步骤 ${data.step}] ${data.content}`, 'step')
    scrollStepsToBottom()
  } else if (type === 'visual_diff') {
    visualDiffResults.value.push(data)
    addLog(`视觉差异: ${data.content}`, 'warn')
  } else if (type === 'log') {
    addLog(data.content, 'info')
  } else if (type === 'completed') {
    finalStatus.value = data.status || 'completed'
    if (data.script) {
      generatedScript.value = data.script
    }
    addLog(`任务完成，状态: ${data.status}，共 ${data.steps_count || executionSteps.value.length} 步`, 'success')
    running.value = false
  } else if (type === 'error') {
    addLog(`错误: ${data.content}`, 'error')
    running.value = false
    finalStatus.value = 'failed'
  } else if (type === 'stream_end') {
    running.value = false
  }
}

const stopAgent = () => {
  running.value = false
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  addLog('已手动停止执行', 'warn')
}

const generateScriptOnly = async () => {
  if (!taskDescription.value) {
    ElMessage.warning('请填写任务描述')
    return
  }
  generatingScript.value = true
  addLog('正在生成 Playwright 脚本（无需执行浏览器）...', 'info')
  try {
    const res = await request.post('/ui-automation/ai-execution-records/generate_e2e_script/', {
      url: startUrl.value,
      task_description: taskDescription.value,
      model_config_id: selectedModelConfigId.value
    })
    generatedScript.value = res.data.script || ''
    if (res.data.steps?.length) {
      planSteps.value = res.data.steps
    }
    addLog(`脚本生成完成（${generatedScript.value.split('\n').length} 行）`, 'success')
    ElMessage.success('脚本生成成功')
  } catch (e) {
    addLog(`脚本生成失败: ${e.response?.data?.error || e.message}`, 'error')
    ElMessage.error('脚本生成失败')
  } finally {
    generatingScript.value = false
  }
}

const copyScript = async () => {
  try {
    await navigator.clipboard.writeText(generatedScript.value)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败，请手动选中复制')
  }
}

const downloadScript = () => {
  const blob = new Blob([generatedScript.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `agent_browser_${Date.now()}.py`
  a.click()
  URL.revokeObjectURL(url)
}

const saveScriptToSystem = async () => {
  if (!generatedScript.value) return
  try {
    await request.post('/ui-automation/test-scripts/', {
      name: `AgentBrowser: ${taskDescription.value.slice(0, 40)}`,
      description: `Agent Browser 自动生成 | URL: ${startUrl.value}`,
      script_type: 'CODE',
      content: generatedScript.value,
      language: 'python',
      framework: 'playwright'
    })
    ElMessage.success('已保存为测试脚本')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  }
}

const handleBaselineChange = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target.result
    // 提取 base64 部分（去掉 data:image/xxx;base64, 前缀）
    baselineB64.value = result.split(',')[1] || ''
    baselinePreview.value = result
  }
  reader.readAsDataURL(file.raw)
}
</script>

<style scoped lang="scss">
.agent-browser-container {
  min-height: calc(100vh - 120px);
}

.agent-browser-container {
  min-height: calc(100vh - 120px);
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 12px;
  border-bottom: 2px solid #e4e7ed;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.sub-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin: 12px 0 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 开关行 */
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.switch-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #303133;
}

.tip-icon {
  color: #c0c4cc;
  font-size: 14px;
  cursor: help;
}

/* 规划步骤 */
.plan-section {
  background: #f0f7ff;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.plan-steps {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.plan-step-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: #606266;
  padding: 3px 0;

  &.done {
    color: #67c23a;
    text-decoration: line-through;
    opacity: 0.7;
  }
}

.plan-idx {
  min-width: 18px;
  height: 18px;
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
  flex-shrink: 0;
}

.plan-step-item.done .plan-idx {
  background: #67c23a;
}

/* 执行步骤流 */
.steps-section {
  margin-bottom: 12px;
}

.steps-list {
  max-height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step-item {
  display: flex;
  gap: 10px;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 6px;
  border-left: 3px solid #409eff;
}

.step-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
}

.step-action-badge {
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 3px;
  background: #e4e7ed;
  color: #606266;
  text-transform: uppercase;

  &.click { background: #fdf6ec; color: #e6a23c; }
  &.type { background: #f0f9eb; color: #67c23a; }
  &.navigate { background: #ecf5ff; color: #409eff; }
  &.done { background: #f0f9eb; color: #67c23a; }
  &.fail { background: #fef0f0; color: #f56c6c; }
}

.step-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.step-desc {
  font-size: 12px;
  color: #303133;
  word-break: break-all;
}

.step-thumb {
  width: 80px;
  height: 50px;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  object-fit: cover;
  cursor: pointer;
}

/* 视觉差异 */
.diff-section {
  margin-bottom: 12px;
}

/* 日志 */
.log-section {
  margin-top: 8px;
}

.log-box {
  background: #1e1e1e;
  border-radius: 6px;
  padding: 10px 12px;
  max-height: 180px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 11px;
}

.log-empty {
  color: #666;
  font-size: 12px;
}

.log-line {
  line-height: 1.7;
  color: #d4d4d4;

  &.error { color: #f48771; }
  &.warn { color: #dcdcaa; }
  &.success { color: #4ec9b0; }
  &.step { color: #9cdcfe; }
}

.log-time {
  color: #6a9955;
  margin-right: 6px;
}

/* 脚本区域 */
.script-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 6px;
}

.script-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.script-actions {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.script-block {
  background: #1e1e1e;
  border-radius: 6px;
  padding: 12px;
  max-height: 380px;
  overflow: auto;

  pre {
    margin: 0;
    code {
      font-family: 'Courier New', monospace;
      font-size: 11px;
      color: #d4d4d4;
      white-space: pre;
    }
  }
}

/* 统计 */
.stats-block {
  margin-top: 16px;
}

/* 运行中动画点 */
.pulse-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e6a23c;
  margin-right: 4px;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}
</style>
