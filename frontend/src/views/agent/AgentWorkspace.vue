<template>
  <BasePage title="Agent+Skills 引擎">
    <div class="card-container">
      <el-row :gutter="20">
        <el-col :span="24">
          <el-card class="premium-card agent-chat">
            <template #header>
              <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 16px; display: flex; align-items: center; gap: 8px;">
                  <el-icon color="#409eff"><Cpu /></el-icon> AI 执行引擎配置
                </span>
              <div class="override-selectors" style="display: flex; gap: 10px; align-items: center;">
                <span style="font-size: 13px; color: #606266;">基础画像:</span>
                <el-select v-model="activeAgent" placeholder="请选择基础 Agent" size="small" style="width: 200px;">
                  <el-option v-for="agent in agents" :key="agent.name" :label="agent.display_name" :value="agent.name" />
                </el-select>
                <span style="font-size: 13px; color: #606266; margin-left: 10px;">🧠 LLM覆盖:</span>
                <el-select v-model="overrideLlm" placeholder="使用画像默认LLM" clearable size="small" style="width: 200px;">
                  <el-option v-for="llm in availableLlms" :key="llm.id" :label="llm.name" :value="llm.id" />
                </el-select>
                <span style="font-size: 13px; color: #606266; margin-left: 10px;">🔧 Skills注入:</span>
                <el-select v-model="overrideSkills" multiple collapse-tags placeholder="附加额外技能" clearable size="small" style="width: 250px;">
                  <el-option v-for="s in availableSkills" :key="s.id" :label="s.display_name || s.name" :value="s.id" />
                </el-select>
              </div>
            </div>
          </template>

          <div class="chat-history" ref="chatHistory">
            <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
              <div class="message-content">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                  <strong>{{ msg.role === 'user' ? 'You' : (msg.currentRole || 'Agent') }}:</strong>
                  <el-tag v-if="msg.currentRole && msg.role !== 'user'" type="success" effect="dark" round size="small">
                    <el-icon style="margin-right: 4px;"><Document /></el-icon> {{ msg.currentRole }}
                  </el-tag>
                </div>
                <p style="white-space: pre-wrap;">{{ msg.content }}</p>

                <div v-if="msg.metrics" class="metrics-panel">
                  <span class="status-indicator" v-if="msg.statusText">
                    <el-icon class="is-loading" v-if="msg.statusText !== 'Finished' && msg.statusText !== '全流水线处理完毕。'"><Connection /></el-icon>
                    {{ msg.statusText }}
                  </span>
                  <el-collapse>
                    <el-collapse-item title="View Internal Tool Execution Trace">
                       <el-tag type="info" style="margin-right: 5px">Persona: {{ activeAgentName }}</el-tag>
                       <div v-if="msg.metrics.llm_reasoning" class="llm-trace">
                          <b>专家交流区:</b> {{ msg.metrics.llm_reasoning }}
                       </div>
                       <ul>
                         <li v-for="action in msg.metrics.actions_taken" :key="action.skill">
                           <b>Skill Executed:</b> {{ action.skill }} 
                           <el-tag :type="action.status === 'success' ? 'success' : 'danger'" style="margin-left: 5px">{{ action.status }}</el-tag>
                           <pre>{{ action.output }}</pre>
                         </li>
                       </ul>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </div>
            </div>
          </div>

          <div class="chat-input-area">
              <el-input
                v-model="inputForm.prompt"
                type="textarea"
                :rows="4"
                placeholder="在此输入您的自然语言需求，例如：'帮我规划一个电商登录页的测试用例集'..."
                @keyup.enter.exact="submitTask"
                :disabled="loading"
                resize="none"
                style="flex: 1; font-size: 14px;"
              />
              <el-button type="primary" :loading="loading" @click="submitTask" class="submit-btn" size="large">
                <el-icon style="margin-right: 4px;"><Promotion /></el-icon> Execute
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </BasePage>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { Monitor, Connection, Mouse as Browser, Position as Iphone, Document, Cpu, Promotion } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { authFetch } from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const agents = ref([])
const activeAgent = ref('')
const loading = ref(false)
const inputForm = ref({ prompt: '' })
const availableLlms = ref([])
const availableSkills = ref([])
const overrideLlm = ref('')
const overrideSkills = ref([])

const messages = ref([
  { role: 'assistant', content: 'Hello! I am your AI Agent. Select a persona from the left, configure optional LLM/Skills overrides at the top, and give me a task.' }
])

const activeAgentName = computed(() => {
  const found = agents.value.find(a => a.name === activeAgent.value)
  return found ? found.display_name : 'Unknown Agent'
})

onMounted(async () => {
    try {
        const [aRes, lRes, sRes] = await Promise.all([
            request.get('assistant/config/agent-profiles/'),
            request.get('/requirement-analysis/api/ai-models/'),
            request.get('assistant/config/agent-skills/')
        ])

        let arr = Array.isArray(aRes.data) ? aRes.data : (Array.isArray(aRes) ? aRes : (aRes.data?.results || []))
        agents.value = arr.filter(a => a.is_active)
        if (agents.value.length > 0) {
            activeAgent.value = agents.value[0].name
        }

        availableLlms.value = Array.isArray(lRes.data) ? lRes.data : Array.isArray(lRes) ? lRes : (lRes.data?.results || [])
        availableSkills.value = Array.isArray(sRes.data) ? sRes.data : Array.isArray(sRes) ? sRes : (sRes.data?.results || [])
    } catch (e) {
        ElMessage.error("Failed to load agent profiles and resources")
    }
})

const handleAgentSelect = (index) => {
  activeAgent.value = index
}

const submitTask = async () => {
  if (!inputForm.value.prompt.trim()) {
    ElMessage.warning('Please enter a command')
    return
  }
  
  if (!activeAgent.value) {
    ElMessage.warning('Please select an agent persona')
    return
  }

  const userPrompt = inputForm.value.prompt
  messages.value.push({ role: 'user', content: userPrompt })
  inputForm.value.prompt = ''
  
  loading.value = true
  
  try {
    const payload = {
      agent_type: activeAgent.value,
      action: 'process_text',
      prompt: userPrompt
    }
    
    if (overrideLlm.value) {
      payload.override_llm_id = overrideLlm.value
    }
    if (overrideSkills.value && overrideSkills.value.length > 0) {
      payload.override_skill_ids = overrideSkills.value
    }

    const userStore = useUserStore()
    const token = userStore.accessToken
    
    // Add an empty assistant message bubble to stream into
    const msgIndex = messages.value.length
    messages.value.push({ 
      role: 'assistant', 
      content: '', // Will stream typing here
      statusText: 'Connecting to AI Engine...',
      metrics: {
        llm_reasoning: '',
        actions_taken: []
      }
    })

    const response = await authFetch('/api/assistant/agent/execute/stream/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
       messages.value[msgIndex].content = "Execution failed due to upstream network error."
       messages.value[msgIndex].statusText = "Failed"
       throw new Error(`Execution failed: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let done = false
    let buffer = ''

    while (!done) {
      const { value, done: readerDone } = await reader.read()
      done = readerDone
      if (value) {
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\\n\\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.substring(6)
            if (dataStr === '[DONE]') {
              messages.value[msgIndex].statusText = 'Finished'
              break
            }
            try {
              const chunk = JSON.parse(dataStr)
              if (chunk.type === 'agent_switch') {
                messages.value[msgIndex].currentRole = chunk.agent_role
                messages.value[msgIndex].content += `\\n\\n--- **${chunk.agent_role} 接管思考** ---\\n`
              } else if (chunk.type === 'metadata') {
                messages.value[msgIndex].statusText = chunk.message
              } else if (chunk.type === 'text_chunk') {
                messages.value[msgIndex].metrics.llm_reasoning += chunk.content
                messages.value[msgIndex].content += chunk.content
              } else if (chunk.type === 'skill_result') {
                messages.value[msgIndex].metrics.actions_taken.push({
                  skill: chunk.skill,
                  status: 'success',
                  output: JSON.stringify(chunk.result, null, 2)
                })
                messages.value[msgIndex].content += `\\n\\n✨ **Executed Skill [${chunk.skill}] Successfully**\\n`
              } else if (chunk.type === 'error') {
                messages.value[msgIndex].content += `\\n\\n🚨 **Error:** ${chunk.message}\\n`
                messages.value[msgIndex].statusText = 'Failed'
              }
              
              // Auto-scroll
              nextTick(() => {
                const chatContainer = document.querySelector('.chat-history')
                if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight
              })
            } catch (e) {
              console.error("SSE Parse Error", e)
            }
          }
        }
      }
    }
  } catch (err) {
    ElMessage.error(err.message || 'Execution failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.card-container {
  background-color: #fff;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  min-height: calc(100vh - 140px);
}
.agent-chat {
  border: none;
  box-shadow: none !important;
}
.chat-history {
  height: 50vh;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  padding: 20px;
  margin-bottom: 20px;
  border-radius: 8px;
  background-color: #fcfcfd;
}
.message {
  margin-bottom: 20px;
}
.message.user .message-content {
  background-color: #f0f9eb;
  padding: 15px;
  border-radius: 12px;
  border-bottom-right-radius: 4px;
  margin-left: 20%;
  border: 1px solid #e1f3d8;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.message.assistant .message-content {
  background-color: #fff;
  padding: 15px;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
  margin-right: 20%;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.chat-input-area {
  display: flex;
  gap: 15px;
  align-items: center;
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.submit-btn {
  height: 95px;
  width: 120px;
  border-radius: 8px;
  font-weight: bold;
  font-size: 16px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border: none;
}
.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(99, 102, 241, 0.3);
}
.metrics-panel {
  margin-top: 10px;
  background-color: #fff;
  border-radius: 4px;
}
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #e6a23c;
  margin-bottom: 8px;
  font-weight: 500;
}
.llm-trace {
  font-family: monospace;
  background: #f4f4f5;
  padding: 5px;
  border-radius: 4px;
  margin-bottom: 10px;
}
pre {
  background: #f8f8f8;
  padding: 5px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
