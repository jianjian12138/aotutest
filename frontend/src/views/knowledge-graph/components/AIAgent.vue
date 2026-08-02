<template>
  <BasePage title="AI助手">
    
    <div class="content-wrapper">
      <!-- Sidebar for Chat History -->
      <div class="chat-sidebar">
        <div class="new-chat-btn-wrapper">
          <el-button type="primary" class="new-chat-btn" @click="startNewChat" :icon="Plus">
            新会话
          </el-button>
        </div>
        
        <div class="history-list">
          <div class="history-label">历史会话</div>
          <div class="session-scroll-area">
            <div 
              v-for="session in historySessionsDescending" 
              :key="session.id"
              :class="['session-item', { active: currentSession?.id === session.id }]"
              @click="switchToSession(session)"
            >
              <div class="session-title-wrapper">
                <el-icon class="chat-icon"><ChatDotRound /></el-icon>
                <span class="session-title" :title="session.title">{{ session.title || '新会话' }}</span>
              </div>
              <div class="session-actions" @click.stop>
                <el-popconfirm title="确定删除此会话吗？" @confirm="deleteSession(session.id)">
                  <template #reference>
                    <el-icon class="delete-icon"><Delete /></el-icon>
                  </template>
                </el-popconfirm>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Chat Area -->
      <div class="chat-main">
        <!-- Model Selector Header -->
        <div class="agent-header">
          <div class="header-left">
             <span class="session-name">{{ currentSession?.title || '新会话' }}</span>
          </div>
          <div class="header-right">
             <el-select 
               v-model="selectedModelId" 
               placeholder="选择 AI 模型" 
               size="small" 
               style="width: 200px"
               @change="handleModelChange"
             >
               <el-option
                 v-for="model in availableModels"
                 :key="model.id"
                 :label="model.name"
                 :value="model.id"
               >
                 <span style="float: left">{{ model.name }}</span>
                 <span style="float: right; color: #8492a6; font-size: 12px">{{ model.model_type }}</span>
               </el-option>
             </el-select>
          </div>
        </div>

        <!-- Welcome Screen -->
        <div v-if="isNewChatMode" class="welcome-screen">
          <div class="welcome-content">
            <div class="logo-area">
              <div class="logo-circle">
                <el-icon><Cpu /></el-icon>
              </div>
              <h1>AI 知识助手</h1>
              <p>基于知识库的智能问答助手，为您解答专业问题</p>
            </div>
            
            <div class="center-input-wrapper">
              <el-input
                v-model="inputMessage"
                type="textarea"
                :rows="3"
                placeholder="输入您的问题，按回车发送..."
                class="center-input"
                resize="none"
                @keydown.enter.exact.prevent="handleEnter"
              />
              <div class="input-actions">
                <el-button 
                  type="primary" 
                  circle 
                  :icon="Promotion" 
                  :disabled="!inputMessage.trim()"
                  @click="sendMessage"
                />
              </div>
            </div>
            
            <div class="suggestion-chips">
              <div class="chip" @click="useSuggestion('总结一下最近上传的文档内容')">文档总结</div>
              <div class="chip" @click="useSuggestion('如何配置 RAG 管道参数？')">RAG 配置</div>
              <div class="chip" @click="useSuggestion('帮我生成一份测试计划')">生成测试计划</div>
            </div>
          </div>
        </div>

        <!-- Chat Messages -->
        <div v-else class="chat-screen">
          <div class="messages-container" ref="messagesContainer">
            <div 
              v-for="(message, index) in messages" 
              :key="message.id || index"
              :class="['message-row', message.role]"
            >
              <div class="avatar">
                <el-avatar v-if="message.role === 'user'" :size="36" :icon="User" class="user-avatar" />
                <el-avatar v-else :size="36" :icon="Cpu" class="ai-avatar" />
              </div>
              <div class="message-bubble">
                <div class="message-content" v-safe-html="formatMessageContent(message.content)"></div>
                <div class="message-status" v-if="message.isPending">
                  <el-icon class="is-loading"><Loading /></el-icon> 思考中...
                </div>
              </div>
            </div>
            <div style="height: 20px;"></div>
          </div>

          <div class="chat-footer">
            <div class="input-box">
              <el-input
                v-model="inputMessage"
                type="textarea"
                :rows="1"
                :autosize="{ minRows: 1, maxRows: 5 }"
                placeholder="输入消息..."
                resize="none"
                @keydown.enter.exact.prevent="handleEnter"
              />
              <el-button 
                type="primary" 
                class="send-btn"
                :disabled="!inputMessage.trim() || sending"
                @click="sendMessage"
              >
                <el-icon><Promotion /></el-icon>
              </el-button>
            </div>
            <div class="footer-tip">内容由 AI 生成，请仔细甄别</div>
          </div>
        </div>
      </div>
    </div>
  
  </BasePage>
</template>
<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Plus, Delete, ChatDotRound, User, Cpu, Promotion, Loading 
} from '@element-plus/icons-vue'
import api from '@/utils/api'

// State
const historySessions = ref([])
const currentSession = ref(null)
const messages = ref([])
const inputMessage = ref('')
const sending = ref(false)
const messagesContainer = ref(null)
const availableModels = ref([])
const selectedModelId = ref(null)

// Computed
const historySessionsDescending = computed(() => {
  return [...historySessions.value].sort((a, b) => 
    new Date(b.updated_at) - new Date(a.updated_at)
  )
})

const isNewChatMode = computed(() => {
  return !currentSession.value || (!currentSession.value.id && messages.value.length === 0)
})

// Methods
const loadModels = async () => {
  try {
    const response = await api.get('/requirement-analysis/api/ai-models/')
    // Handle pagination or list
    const results = response.data.results || response.data || []
    availableModels.value = results.filter(m => m.is_active)
    
    // Select first available model if none selected
    if (availableModels.value.length > 0 && !selectedModelId.value) {
      selectedModelId.value = availableModels.value[0].id
    }
  } catch (error) {
    console.error('Failed to load models:', error)
  }
}

const handleModelChange = (val) => {
  console.log('Model switched to:', val)
  // Logic to update session config if needed
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

const formatMessageContent = (content) => {
  if (!content) return ''
  return content
    .replace(/\n/g, '<br>')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const startNewChat = () => {
  currentSession.value = { title: '新会话' }
  messages.value = []
  inputMessage.value = ''
}

const switchToSession = async (session) => {
  if (currentSession.value?.id === session.id) return
  try {
    currentSession.value = { ...session }
    const response = await api.get(`/assistant/sessions/${session.id}/messages/`)
    messages.value = response.data
    scrollToBottom()
  } catch (error) {
    console.error('加载消息失败:', error)
    ElMessage.error('加载消息失败')
  }
}

const deleteSession = async (sessionId) => {
  try {
    await api.delete(`/assistant/sessions/${sessionId}/`)
    historySessions.value = historySessions.value.filter(s => s.id !== sessionId)
    if (currentSession.value?.id === sessionId) {
      startNewChat()
    }
    ElMessage.success('会话已删除')
  } catch (error) {
    ElMessage.error('删除会话失败')
  }
}

const useSuggestion = (text) => {
  inputMessage.value = text
  sendMessage()
}

const handleEnter = (e) => {
  if (!e.shiftKey && !sending.value) {
    sendMessage()
  }
}

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || sending.value) return
  
  inputMessage.value = ''
  sending.value = true
  
  // 1. User Message
  messages.value.push({
    role: 'user',
    content: text,
    created_at: new Date().toISOString()
  })
  
  // 2. Pending AI Message
  messages.value.push({
    role: 'assistant',
    content: '',
    isPending: true
  })
  scrollToBottom()
  
  try {
    let sessionId = currentSession.value?.id
    let isFirstMessage = false
    
    if (!sessionId) {
      isFirstMessage = true
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`
      const title = text.length > 10 ? text.substring(0, 10) + '...' : text
      
      const sessionRes = await api.post('/assistant/sessions/', {
        session_id: newSessionId,
        title: title
      })
      
      currentSession.value = sessionRes.data
      sessionId = currentSession.value.session_id
      historySessions.value.unshift(currentSession.value)
    } else {
      sessionId = currentSession.value.session_id
    }
    
    // 3. Send Request
    const response = await api.post('/assistant/chat/send_message/', {
      session_id: sessionId,
      message: text,
      model_id: selectedModelId.value // Pass selected model
    }, { timeout: 60000 })
    
    // 4. Update Messages
    messages.value.pop() // Remove pending
    messages.value.pop() // Remove temp user
    
    messages.value.push(response.data.user_message)
    messages.value.push(response.data.assistant_message)
    
    if (!isFirstMessage) {
      const index = historySessions.value.findIndex(s => s.id === currentSession.value.id)
      if (index !== -1) {
        historySessions.value[index] = { ...currentSession.value, updated_at: new Date().toISOString() }
        const updatedSession = historySessions.value.splice(index, 1)[0]
        historySessions.value.unshift(updatedSession)
      }
    }
    
  } catch (error) {
    console.error('发送失败:', error)
    messages.value.pop() // Remove pending
    ElMessage.error(error.response?.data?.error || '发送失败，请重试')
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

const loadHistory = async () => {
  try {
    const response = await api.get('/assistant/sessions/')
    historySessions.value = response.data.results || response.data || []
  } catch (error) {
    console.error('加载历史失败:', error)
  }
}

onMounted(() => {
  loadModels()
  loadHistory()
  startNewChat()
})
</script>

<style scoped lang="scss">

.ai-agent-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
}

.content-wrapper {
  display: flex;
  flex: 1;
  overflow: hidden;
  background: #fff;
  border-radius: 8px;
  margin: 0px;
  border: 1px solid #e0e0e0;
}

.chat-sidebar {
  width: 240px;
  background: #f9f9f9;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  
  .new-chat-btn-wrapper {
    padding: 16px;
    .new-chat-btn {
      width: 100%;
    }
  }
  
  .history-list {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    
    .history-label {
      padding: 0 16px 8px;
      font-size: 12px;
      color: #909399;
    }
    
    .session-scroll-area {
      flex: 1;
      overflow-y: auto;
      padding: 0 8px;
      
      .session-item {
        padding: 10px 12px;
        margin-bottom: 4px;
        border-radius: 6px;
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #606266;
        
        &:hover {
          background: #e6f7ff;
          .session-actions { opacity: 1; }
        }
        
        &.active {
          background: #e6f7ff;
          color: #409eff;
        }
        
        .session-title-wrapper {
          display: flex;
          align-items: center;
          gap: 8px;
          overflow: hidden;
          
          .session-title {
            font-size: 13px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
        }
        
        .session-actions {
          opacity: 0;
          .delete-icon { font-size: 14px; color: #f56c6c; }
        }
      }
    }
  }
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.agent-header {
  height: 50px;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  
  .session-name {
    font-weight: 600;
    color: #303133;
  }
}

.welcome-screen {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .welcome-content {
    max-width: 600px;
    width: 100%;
    text-align: center;
    
    .logo-circle {
      width: 64px;
      height: 64px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 50%;
      margin: 0 auto 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 32px;
    }
    
    h1 { margin-bottom: 10px; color: #303133; }
    p { color: #909399; margin-bottom: 40px; }
  }
}

.center-input-wrapper {
  position: relative;
  margin-bottom: 30px;
  
  .center-input :deep(.el-textarea__inner) {
    border-radius: 12px;
    padding: 12px 50px 12px 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border: 1px solid #e4e7ed;
    
    &:focus { border-color: #409eff; }
  }
  
  .input-actions {
    position: absolute;
    right: 10px;
    bottom: 10px;
  }
}

.suggestion-chips {
  display: flex;
  justify-content: center;
  gap: 10px;
  
  .chip {
    padding: 6px 16px;
    background: #f0f2f5;
    border-radius: 16px;
    font-size: 13px;
    color: #606266;
    cursor: pointer;
    &:hover { color: #409eff; background: #ecf5ff; }
  }
}

.chat-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  
  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    
    .message-row {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      
      &.user {
        flex-direction: row-reverse;
        .message-bubble {
          background: #409eff;
          color: white;
          border-radius: 12px 12px 0 12px;
          :deep(code) { color: #fff; background: rgba(0,0,0,0.1); }
        }
      }
      
      &.assistant {
        .message-bubble {
          background: #f5f7fa;
          color: #303133;
          border-radius: 12px 12px 12px 0;
        }
      }
      
      .message-bubble {
        max-width: 80%;
        padding: 10px 16px;
        font-size: 14px;
        line-height: 1.6;
        
        :deep(pre) {
          background: #282c34;
          color: #abb2bf;
          padding: 10px;
          border-radius: 6px;
          overflow-x: auto;
        }
      }
    }
  }
  
  .chat-footer {
    padding: 16px 20px;
    border-top: 1px solid #eee;
    
    .input-box {
      position: relative;
      border: 1px solid #dcdfe6;
      border-radius: 8px;
      padding: 4px;
      
      :deep(.el-textarea__inner) {
        border: none;
        box-shadow: none;
        padding-right: 40px;
      }
      
      .send-btn {
        position: absolute;
        right: 6px;
        bottom: 6px;
        padding: 6px;
        height: 28px;
        width: 28px;
        min-height: auto;
      }
    }
    .footer-tip {
      text-align: center;
      font-size: 12px;
      color: #c0c4cc;
      margin-top: 8px;
    }
  }
}
</style>
