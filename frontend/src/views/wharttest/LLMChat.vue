<template>
  <div class="llm-chat-container">
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>会话列表</h3>
        <el-button type="primary" circle size="small" @click="newChat"><el-icon><Plus /></el-icon></el-button>
      </div>
      <el-scrollbar>
        <div 
          v-for="chat in chatHistory" 
          :key="chat.id" 
          class="chat-item" 
          :class="{ active: currentChatId === chat.id }"
          @click="switchChat(chat.id)"
        >
          <div class="chat-title">{{ chat.title }}</div>
          <div class="chat-time">{{ formatTime(chat.timestamp) }}</div>
        </div>
      </el-scrollbar>
    </div>
    
    <div class="main-chat">
      <div class="chat-header">
        <div class="model-selector">
          <span>模型: </span>
          <el-select v-model="selectedModel" placeholder="选择模型" size="small" style="width: 150px">
            <el-option label="GPT-4o" value="gpt-4o" />
            <el-option label="Claude 3.5 Sonnet" value="claude-3-5-sonnet" />
            <el-option label="DeepSeek V3" value="deepseek-v3" />
          </el-select>
        </div>
        <div class="mcp-selector">
           <el-popover placement="bottom" title="MCP 工具" :width="200" trigger="click">
             <template #reference>
               <el-button size="small" type="success" plain>
                 <el-icon><Tools /></el-icon> MCP 工具 ({{ enabledMCPs.length }})
               </el-button>
             </template>
             <el-checkbox-group v-model="enabledMCPs">
               <el-checkbox label="filesystem">文件系统</el-checkbox>
               <el-checkbox label="github">GitHub</el-checkbox>
               <el-checkbox label="database">数据库</el-checkbox>
             </el-checkbox-group>
           </el-popover>
        </div>
      </div>
      
      <div class="messages-area" ref="messagesRef">
        <div v-if="!currentChat.messages.length" class="empty-state">
          <el-icon :size="60"><ChatDotRound /></el-icon>
          <h3>开始与 AI 助手对话</h3>
          <p>您可以询问测试用例生成、代码分析或使用 MCP 工具查询系统信息。</p>
        </div>
        <div v-for="(msg, index) in currentChat.messages" :key="index" class="message-row" :class="msg.role">
          <div class="avatar">
            <el-avatar :size="36" :icon="msg.role === 'user' ? UserFilled : Service" :class="msg.role" />
          </div>
          <div class="message-content">
            <div class="bubble">
              <div class="text" v-html="renderMarkdown(msg.content)"></div>
              <div v-if="msg.toolCalls" class="tool-calls">
                 <div v-for="(tool, tIndex) in msg.toolCalls" :key="tIndex" class="tool-call">
                   <el-tag size="small" type="info">调用工具: {{ tool.name }}</el-tag>
                   <pre class="tool-args">{{ tool.args }}</pre>
                   <div class="tool-result" v-if="tool.result">
                     <strong>结果:</strong> {{ tool.result }}
                   </div>
                 </div>
              </div>
            </div>
            <span class="time">{{ formatTime(msg.timestamp) }}</span>
          </div>
        </div>
        <div v-if="loading" class="message-row assistant">
           <div class="avatar"><el-avatar :size="36" :icon="Service" class="assistant" /></div>
           <div class="message-content">
             <div class="bubble loading">
               <span>思考中...</span>
             </div>
           </div>
        </div>
      </div>
      
      <div class="input-area">
        <el-input
          v-model="inputContent"
          type="textarea"
          :rows="3"
          placeholder="输入您的问题..."
          @keydown.enter.prevent="sendMessage"
        />
        <div class="input-actions">
           <el-button type="primary" @click="sendMessage" :loading="loading">发送</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { Plus, UserFilled, Service, ChatDotRound, Tools } from '@element-plus/icons-vue'
import { marked } from 'marked'

const selectedModel = ref('gpt-4o')
const enabledMCPs = ref(['filesystem'])
const inputContent = ref('')
const loading = ref(false)
const messagesRef = ref(null)

const chatHistory = ref([
  {
    id: '1',
    title: '测试用例生成 - 登录模块',
    timestamp: new Date(),
    messages: [
      { role: 'user', content: '请帮我生成登录模块的测试用例', timestamp: new Date() },
      { role: 'assistant', content: '好的，基于通常的登录模块，我建议以下测试用例...', timestamp: new Date() }
    ]
  }
])

const currentChatId = ref('1')

const currentChat = computed(() => {
  return chatHistory.value.find(c => c.id === currentChatId.value) || { messages: [] }
})

const newChat = () => {
  const newId = Date.now().toString()
  chatHistory.value.unshift({
    id: newId,
    title: '新会话',
    timestamp: new Date(),
    messages: []
  })
  currentChatId.value = newId
}

const switchChat = (id) => {
  currentChatId.value = id
  scrollToBottom()
}

const sendMessage = async () => {
  if (!inputContent.value.trim() || loading.value) return
  
  const userMsg = inputContent.value
  inputContent.value = ''
  
  currentChat.value.messages.push({
    role: 'user',
    content: userMsg,
    timestamp: new Date()
  })
  
  scrollToBottom()
  loading.value = true
  
  // 模拟 AI 回复
  setTimeout(() => {
    loading.value = false
    currentChat.value.messages.push({
      role: 'assistant',
      content: `收到您的请求: "${userMsg}"。\n\n正在分析相关需求...`,
      timestamp: new Date(),
      // 模拟工具调用
      toolCalls: userMsg.includes('文件') ? [
        { name: 'filesystem.list_files', args: '{ path: "." }', result: '["src", "package.json", "README.md"]' }
      ] : undefined
    })
    scrollToBottom()
  }, 1500)
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const formatTime = (date) => {
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const renderMarkdown = (text) => {
  return marked.parse(text)
}

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped lang="scss">
.llm-chat-container {
  display: flex;
  height: calc(100vh - 100px);
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.sidebar {
  width: 260px;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
  
  .sidebar-header {
    padding: 15px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #ebeef5;
    
    h3 { margin: 0; font-size: 16px; }
  }
  
  .chat-item {
    padding: 12px 15px;
    cursor: pointer;
    border-bottom: 1px solid #f0f2f5;
    transition: background 0.2s;
    
    &:hover { background: #ecf5ff; }
    &.active { background: #e6f7ff; border-right: 3px solid #1890ff; }
    
    .chat-title {
      font-size: 14px;
      color: #303133;
      margin-bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    
    .chat-time {
      font-size: 12px;
      color: #909399;
    }
  }
}

.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 10px 20px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  
  .model-selector {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
  }
}

.messages-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7fa;
  
  .empty-state {
    text-align: center;
    margin-top: 100px;
    color: #909399;
  }
  
  .message-row {
    display: flex;
    margin-bottom: 20px;
    
    &.user {
      flex-direction: row-reverse;
      .bubble {
        background: #95ec69;
        color: #000;
      }
      .avatar { margin-left: 10px; margin-right: 0; }
    }
    
    &.assistant {
      .bubble {
        background: #fff;
        border: 1px solid #ebeef5;
      }
      .avatar { margin-right: 10px; }
    }
  }
  
  .avatar {
    flex-shrink: 0;
  }
  
  .message-content {
    max-width: 70%;
    display: flex;
    flex-direction: column;
  }
  
  .bubble {
    padding: 10px 15px;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.6;
    
    .text {
      word-break: break-word;
    }
    
    .tool-calls {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #eee;
      
      .tool-call {
        background: #f8f9fa;
        padding: 8px;
        border-radius: 4px;
        margin-bottom: 5px;
        font-size: 12px;
        
        .tool-args {
           margin: 5px 0;
           color: #666;
        }
      }
    }
  }
  
  .time {
    font-size: 12px;
    color: #999;
    margin-top: 4px;
    align-self: flex-end;
    
    .assistant & { align-self: flex-start; }
  }
}

.input-area {
  padding: 20px;
  background: #fff;
  border-top: 1px solid #ebeef5;
  
  .input-actions {
    margin-top: 10px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>