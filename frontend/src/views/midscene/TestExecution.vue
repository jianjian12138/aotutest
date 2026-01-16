<template>
  <div class="test-execution-container">
    <div class="header">
      <h2>自然语言测试执行</h2>
      <p>通过对话式界面执行UI自动化测试</p>
      <div class="header-actions">
         <el-button type="primary" size="small" @click="createNewSession">
          <el-icon><Plus /></el-icon> 新建会话
        </el-button>
        <el-button type="success" size="small" @click="clearHistory">
          <el-icon><Delete /></el-icon> 清空会话
        </el-button>
      </div>
    </div>

    <div class="main-layout">
      <!-- 聊天区域 -->
      <div class="chat-area">
        <div class="messages" ref="messagesRef">
          <div v-if="messages.length === 0" class="empty-state">
             <el-empty description="请输入自然语言指令开始测试" />
          </div>
          <div 
            v-for="(msg, index) in messages" 
            :key="index" 
            class="message-item"
            :class="msg.role"
          >
            <div class="avatar">
              <el-avatar :size="36" :icon="msg.role === 'user' ? UserFilled : Service" :class="msg.role" />
            </div>
            <div class="content">
              <div class="bubble">
                <p v-if="msg.type === 'text'">{{ msg.content }}</p>
                <div v-else-if="msg.type === 'image'" class="image-content">
                  <el-image 
                    :src="msg.content" 
                    :preview-src-list="[msg.content]" 
                    fit="contain"
                    class="screenshot"
                  />
                </div>
                <div v-else-if="msg.type === 'action-result'" class="action-result">
                  <el-tag :type="msg.success ? 'success' : 'danger'" size="small">
                    {{ msg.success ? '执行成功' : '执行失败' }}
                  </el-tag>
                  <div class="result-details" v-if="msg.details">
                    <pre>{{ msg.details }}</pre>
                  </div>
                </div>
              </div>
              <div class="meta">
                <span class="time">{{ formatTime(msg.timestamp) }}</span>
              </div>
            </div>
          </div>
          
           <div v-if="isLoading" class="message-item assistant">
             <div class="avatar">
               <el-avatar :size="36" :icon="Service" class="assistant" />
             </div>
             <div class="content">
               <div class="bubble loading">
                 <span class="dot"></span>
                 <span class="dot"></span>
                 <span class="dot"></span>
               </div>
             </div>
           </div>
        </div>

        <div class="input-area">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            placeholder="请输入您想要执行的操作，例如：点击登录按钮，填写用户名为admin，检查页面标题是否包含首页"
            @keydown.enter.prevent="sendMessage"
            :disabled="isLoading"
          />
          <div class="input-actions">
            <span class="hint">Ctrl + Enter 发送 | 支持自然语言描述UI操作</span>
            <el-button type="primary" @click="sendMessage" :loading="isLoading">
              <el-icon><Promotion /></el-icon> 发送
            </el-button>
          </div>
        </div>
      </div>

      <!-- 实时预览区域 (可选) -->
      <div class="preview-area">
         <div class="preview-header">
           <span>执行历史</span>
           <el-button type="text" size="small" @click="clearHistory">清空</el-button>
         </div>
         <div class="execution-history">
            <div v-if="history.length === 0" class="history-empty">
               <el-empty description="暂无执行记录" :image-size="80" />
            </div>
            <el-timeline v-else>
              <el-timeline-item
                v-for="(item, index) in history"
                :key="index"
                :type="item.status === 'success' ? 'success' : 'danger'"
                :timestamp="formatTime(item.timestamp)"
              >
                {{ item.description }}
              </el-timeline-item>
            </el-timeline>
         </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { UserFilled, Service, Promotion, Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const messagesRef = ref(null)
const history = ref([])

// 模拟初始化消息
const createNewSession = () => {
  messages.value = [
    {
      role: 'assistant',
      type: 'text',
      content: '你好！我是 Midscene AI 助手。我可以帮你执行 Web UI 自动化测试。请告诉我你想做什么？',
      timestamp: new Date()
    }
  ]
  history.value = []
}

const clearHistory = () => {
    messages.value = []
    history.value = []
    createNewSession()
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return
  
  const userMsg = inputMessage.value
  inputMessage.value = ''
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    type: 'text',
    content: userMsg,
    timestamp: new Date()
  })
  
  scrollToBottom()
  isLoading.value = true
  
  // 模拟 AI 响应和执行过程
  try {
    // 这里将来会调用后端 Midscene API
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 模拟执行结果
    const mockResponse = {
        role: 'assistant',
        type: 'action-result',
        success: true,
        content: '执行完成',
        details: `执行步骤:\n1. 定位元素 "登录按钮"\n2. 点击元素\n3. 等待页面跳转`,
        timestamp: new Date()
    }
    
    messages.value.push(mockResponse)
    
    // 添加到历史记录
    history.value.unshift({
        status: 'success',
        description: userMsg,
        timestamp: new Date()
    })
    
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      type: 'text',
      content: '抱歉，执行过程中出现了错误。',
      timestamp: new Date()
    })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const formatTime = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleTimeString()
}

onMounted(() => {
  createNewSession()
})
</script>

<style scoped lang="scss">
.test-execution-container {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  background-color: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.header {
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    margin: 0;
    font-size: 18px;
    color: #303133;
  }
  
  p {
      margin: 5px 0 0;
      font-size: 12px;
      color: #909399;
  }
  
  .header-actions {
      display: flex;
      gap: 10px;
  }
}

.main-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #ebeef5;
}

.messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #f5f7fa;
  
  .empty-state {
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
  }
}

.message-item {
  display: flex;
  margin-bottom: 20px;
  
  &.user {
    flex-direction: row-reverse;
    
    .bubble {
      background-color: #ecf5ff; // 浅蓝色背景
      border: 1px solid #d9ecff;
      border-radius: 12px 0 12px 12px;
      margin-right: 12px;
    }
    
    .avatar {
        margin-left: 0;
    }
  }
  
  &.assistant {
    .bubble {
      background-color: #fff;
      border: 1px solid #ebeef5;
      border-radius: 0 12px 12px 12px;
      margin-left: 12px;
    }
  }
}

.avatar {
  flex-shrink: 0;
  
  .el-avatar {
      background-color: #409eff;
      
      &.assistant {
          background-color: #67c23a;
      }
  }
}

.content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
}

.bubble {
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.5;
  color: #303133;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  
  p {
    margin: 0;
    white-space: pre-wrap;
  }
  
  &.loading {
      display: flex;
      gap: 4px;
      padding: 16px;
      
      .dot {
          width: 8px;
          height: 8px;
          background-color: #909399;
          border-radius: 50%;
          animation: bounce 1.4s infinite ease-in-out both;
          
          &:nth-child(1) { animation-delay: -0.32s; }
          &:nth-child(2) { animation-delay: -0.16s; }
      }
  }
}

.action-result {
    .result-details {
        margin-top: 8px;
        background: #f8f9fa;
        padding: 8px;
        border-radius: 4px;
        font-size: 12px;
        
        pre {
            margin: 0;
            white-space: pre-wrap;
            color: #606266;
        }
    }
}

.meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  text-align: right;
}

.input-area {
  padding: 20px;
  background-color: #fff;
  border-top: 1px solid #ebeef5;
  
  .input-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
    
    .hint {
      font-size: 12px;
      color: #909399;
    }
  }
}

.preview-area {
  width: 300px;
  background-color: #fff;
  display: flex;
  flex-direction: column;
  
  .preview-header {
      padding: 15px;
      border-bottom: 1px solid #ebeef5;
      font-weight: bold;
      display: flex;
      justify-content: space-between;
      align-items: center;
  }
  
  .execution-history {
      flex: 1;
      padding: 20px;
      overflow-y: auto;
      
      .history-empty {
          margin-top: 50px;
          text-align: center;
      }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>