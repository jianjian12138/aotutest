<template>
  <div class="ai-copilot-container">
    <div v-show="isOpen" class="copilot-panel">
      <div class="panel-header">
        <el-icon><MagicStick /></el-icon>
        <span>AI Copilot Skills</span>
        <el-button link @click="togglePanel"><el-icon><Close /></el-icon></el-button>
      </div>
      <div class="panel-body">
        <div class="skills-section">
          <div class="skill-tags">
            <el-tag v-for="skill in skills" :key="skill.name" @click="invokeSkill(skill)">
              {{ skill.label }}
            </el-tag>
          </div>
        </div>
        <div class="chat-area" ref="chatArea">
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
             {{ msg.content }}
          </div>
          <div v-if="loading" class="loading-indicator">AI 正在思考...</div>
        </div>
      </div>
      <div class="panel-footer">
        <el-input v-model="userInput" placeholder="Ask AI..." @keyup.enter="sendMessage" :disabled="loading" />
        <el-button type="primary" :loading="loading" @click="sendMessage">发送</el-button>
      </div>
    </div>
    
    <div class="fab" @click="togglePanel">
      <el-icon class="magic-icon"><MagicStick /></el-icon>
    </div>
  </div>
</template>

<script setup>
import { ref, onUpdated } from 'vue'
import { MagicStick, Close } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

const isOpen = ref(false)
const loading = ref(false)
const userInput = ref('')
const chatArea = ref(null)
const sessionId = ref(null)
const messages = ref([
    { role: 'ai', content: '您好！我是您的智能测试助手。请选择上方预设 Skill，或者直接向我提问。' }
])

const skills = [
  { name: 'analyze_error', label: '一键解读报错' },
  { name: 'generate_script', label: '生成自动化脚本' },
  { name: 'perf_test', label: '智能压测策略' }
]

const togglePanel = () => {
    isOpen.value = !isOpen.value
}

const scrollToBottom = () => {
    if (chatArea.value) {
        chatArea.value.scrollTop = chatArea.value.scrollHeight
    }
}

onUpdated(() => {
    scrollToBottom()
})

const invokeSkill = (skill) => {
    let prompt = ''
    if (skill.name === 'analyze_error') {
        prompt = '请帮我解读项目中最新的测试报错日志，分析失败原因并给出修复建议。'
    } else if (skill.name === 'generate_script') {
        prompt = '请根据当前页面的DOM结构帮我生成一个基于 Playwright 的自动化测试脚本。'
    } else if (skill.name === 'perf_test') {
        prompt = '请为主要业务流生成一个并发量为 100 的 Jmeter 压测场景设计方案。'
    }
    userInput.value = prompt
    sendMessage()
}

// 后端 send_message 必须携带合法 session_id：
// 先确保存在一个会话（POST /assistant/sessions/），再发消息。
const ensureSession = async () => {
    if (sessionId.value) return sessionId.value
    try {
        const res = await api.post('/assistant/sessions/', { title: 'AI Copilot 会话' })
        const data = res.data?.data || res.data
        sessionId.value = data?.session_id || data?.id || data?.sessionId || null
    } catch (e) {
        sessionId.value = null
        console.error('创建 AI 会话失败:', e)
    }
    return sessionId.value
}

const sendMessage = async () => {
    const text = userInput.value.trim()
    if (!text && !loading.value) return
    messages.value.push({ role: 'user', content: text })
    userInput.value = ''
    loading.value = true

    try {
        const sid = await ensureSession()
        if (!sid) {
            messages.value.push({
                role: 'ai',
                content: '⚠️ 无法创建 AI 会话，请确认后端已配置 AI 模型 / 工作流引擎（配置中心）。'
            })
            return
        }
        const response = await api.post('/assistant/chat/send_message/', {
            session_id: sid,
            message: text,
        })
        const data = response.data?.data || response.data
        const reply = data?.assistant_message?.content
            || data?.reply
            || data?.answer
            || (typeof data?.assistant_message === 'string' ? data.assistant_message : null)
        if (!reply) {
            messages.value.push({ role: 'ai', content: '（AI 未返回内容）' })
        } else {
            const content = typeof reply === 'string' ? reply : JSON.stringify(reply, null, 2)
            messages.value.push({ role: 'ai', content })
        }
    } catch (e) {
        // 真实错误透传，不再伪造"成功答复"
        const err = e?.response?.data?.error || e?.message || '请求失败'
        messages.value.push({ role: 'ai', content: `⚠️ ${err}` })
        console.error('AI API Error:', e)
    } finally {
        loading.value = false
    }
}
</script>

<style scoped lang="scss">
.ai-copilot-container {
  position: fixed;
  bottom: 30px;
  right: 30px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.fab {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  box-shadow: 0 10px 25px rgba(26, 92, 255, 0.4);
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s ease;
  
  &:hover {
    transform: scale(1.1) rotate(15deg);
    box-shadow: 0 15px 35px rgba(26, 92, 255, 0.6);
  }
}

.copilot-panel {
  width: 400px;
  height: 600px;
  margin-bottom: 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(255,255,255,0.5) inset;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  
  .panel-header {
    padding: 18px 20px;
    background: linear-gradient(90deg, rgba(var(--primary-rgb), 0.1), rgba(var(--accent-rgb), 0.1));
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(0,0,0,0.05);
    font-weight: 600;
    color: var(--text-color);
    
    .el-icon {
      font-size: 20px;
      color: var(--primary-color);
      margin-right: 10px;
    }
  }
  
  .panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
    display: flex;
    flex-direction: column;
    
    .skills-section {
      margin-bottom: 15px;
      
      .skill-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        
        .el-tag {
          cursor: pointer;
          border-radius: 12px;
          background: rgba(var(--primary-rgb), 0.05);
          border: 1px solid rgba(var(--primary-rgb), 0.2);
          color: var(--primary-color);
          transition: all 0.2s ease;
          
          &:hover {
            background: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
          }
        }
      }
    }
    
    .chat-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto; // Let chat area scroll if needed
      
      .message {
        padding: 12px 16px;
        border-radius: 16px;
        max-width: 85%;
        line-height: 1.5;
        font-size: 14px;
        white-space: pre-wrap;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        
        &.user {
          align-self: flex-end;
          background: linear-gradient(135deg, var(--primary-color), #3A74FF);
          color: white;
          border-bottom-right-radius: 4px;
        }
        
        &.ai {
          align-self: flex-start;
          background: white;
          color: var(--text-color);
          border: 1px solid rgba(0,0,0,0.05);
          border-bottom-left-radius: 4px;
        }
      }
      
      .loading-indicator {
        align-self: flex-start;
        font-size: 12px;
        color: var(--text-secondary);
        animation: pulse 1.5s infinite;
        padding: 5px 10px;
      }
    }
  }
  
  .panel-footer {
    padding: 15px;
    border-top: 1px solid rgba(0,0,0,0.05);
    display: flex;
    gap: 10px;
    background: rgba(255,255,255,0.5);
    
    .el-input {
      --el-border-radius-base: 20px;
      flex: 1;
    }
    .el-button {
      border-radius: 20px;
      padding: 8px 20px;
    }
  }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes pulse {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}

/* Dark mode compatibility */
html.dark {
  .copilot-panel {
    background: rgba(30, 30, 35, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    
    .panel-header {
      background: rgba(255,255,255,0.05);
      border-bottom: 1px solid rgba(255,255,255,0.05);
      color: #E2E8F0;
    }
    
    .message.ai {
      background: rgba(255,255,255,0.05);
      color: #E2E8F0;
      border: 1px solid rgba(255,255,255,0.1);
    }
    
    .panel-footer {
      background: rgba(0,0,0,0.2);
      border-top: 1px solid rgba(255,255,255,0.05);
    }
  }
}
</style>
