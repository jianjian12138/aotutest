<template>
  <div class="deeptutor-layout" :class="{ 'dark-mode': isDarkMode }">
    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 1. Personal Workspace (Dashboard) -->
      <div v-if="currentTab === 'dashboard'" class="view-panel dashboard-view">
        <div class="welcome-banner">
          <h1>欢迎回来, 用户!</h1>
          <p>您的个人知识引擎已就绪。已索引 <strong>{{ stats.documents }}</strong> 份文档。</p>
        </div>
        <div class="quick-access-grid">
          <div class="access-card" @click="navigateTo('notebook')">
            <div class="icon-wrapper bg-blue"><el-icon><Notebook /></el-icon></div>
            <h3>新建笔记</h3>
            <p>开启新的学习会话</p>
          </div>
          <div class="access-card" @click="navigateTo('idealab')">
             <div class="icon-wrapper bg-purple"><el-icon><MagicStick /></el-icon></div>
             <h3>深度研究</h3>
             <p>从想法生成代码解决方案</p>
          </div>
          <div class="access-card" @click="navigateTo('sources')">
             <div class="icon-wrapper bg-green"><el-icon><UploadFilled /></el-icon></div>
             <h3>上传数据</h3>
             <p>添加至个人知识库</p>
          </div>
        </div>
        <div class="recent-activity">
           <h3>最近活动</h3>
           <el-timeline>
             <el-timeline-item timestamp="刚刚" type="primary">更新了 RAG 管道配置</el-timeline-item>
             <el-timeline-item timestamp="2小时前" type="success">索引了 "深度学习_卷1.pdf"</el-timeline-item>
             <el-timeline-item timestamp="昨天" type="info">创建了新笔记 "图论基础"</el-timeline-item>
           </el-timeline>
        </div>
      </div>

      <!-- 2. Personal Notebook (Interactive Learning) -->
      <div v-if="currentTab === 'notebook'" class="view-panel notebook-view">
        <div class="notebook-sidebar">
           <div class="nb-header">
             <span>我的笔记</span>
             <el-button link type="primary" @click="createNotebook"><el-icon><Plus /></el-icon></el-button>
           </div>
           <div class="nb-list">
             <div 
                v-for="note in notebooks" 
                :key="note.id" 
                class="nb-item" 
                :class="{ active: currentNotebook?.id === note.id }"
                @click="selectNotebook(note)"
             >
               <div class="note-title"><el-icon><Document /></el-icon> {{ note.title }}</div>
               <el-icon class="delete-icon" @click.stop="deleteNotebook(note)"><Delete /></el-icon>
             </div>
           </div>
        </div>
        <div class="notebook-editor" v-if="currentNotebook">
           <div class="editor-toolbar">
             <span class="doc-title">
                <el-input v-model="currentNotebook.title" style="width: 200px" size="small" />
             </span>
             <div class="actions">
               <el-button size="small">保存</el-button>
               <el-button size="small" type="primary" @click="notebookDrawer = true">询问 AI</el-button>
             </div>
           </div>
           <textarea class="markdown-area" v-model="currentNotebook.content" placeholder="# 在此开始输入笔记..."></textarea>
        </div>
        <el-drawer v-model="notebookDrawer" title="上下文感知助手" :size="400">
           <div class="drawer-chat">
             <div class="chat-bubble ai">
               你好！我看到你正在写关于{{ currentNotebook?.title }}的内容。需要我提供帮助吗？
             </div>
             <div class="chat-input-area">
               <el-input placeholder="针对笔记提问..." />
             </div>
           </div>
        </el-drawer>
      </div>

      <!-- 3. Idea to Code (Deep Research) -->
      <div v-if="currentTab === 'idealab'" class="view-panel idealab-view">
        <div class="idea-input-section" v-if="!ideaGenerated">
           <h2>深度研究与想法生成</h2>
           <p>描述您的想法，DeepTutor 将进行研究、规划并生成代码库。</p>
           <el-input
             v-model="ideaInput"
             type="textarea"
             :rows="6"
             placeholder="例如：构建一个使用 pandas 分析股票市场数据并使用 matplotlib 可视化趋势的 Python 脚本..."
             class="idea-textarea"
           />
           <div class="idea-actions">
             <el-button type="primary" size="large" @click="startIdeaGen" :loading="ideaLoading">
               <el-icon><MagicStick /></el-icon> 生成解决方案
             </el-button>
           </div>
        </div>
        <div class="idea-result-section" v-else>
           <div class="gen-steps">
             <el-steps :active="genStep" finish-status="success">
               <el-step title="研究中" />
               <el-step title="规划中" />
               <el-step title="编码中" />
             </el-steps>
           </div>
           <div class="gen-content">
             <div class="file-tree">
               <div class="tree-item"><el-icon><Folder /></el-icon> src</div>
               <div class="tree-item indent"><el-icon><Document /></el-icon> main.py</div>
               <div class="tree-item indent"><el-icon><Document /></el-icon> utils.py</div>
             </div>
             <div class="code-preview">
               <pre><code>import pandas as pd
import matplotlib.pyplot as plt

def analyze_stock(data):
    # AI 生成的代码
    df = pd.DataFrame(data)
    return df.describe()</code></pre>
             </div>
           </div>
           <el-button @click="ideaGenerated = false">新想法</el-button>
        </div>
      </div>

      <!-- 4. RAG Pipeline (Atomic Customization) -->
      <div v-if="currentTab === 'engine'" class="view-panel engine-view">
         <h2>RAG 管道原子化配置</h2>
         <div class="config-grid">
           <div class="config-card">
             <h3>1. 文档加载</h3>
             <el-form label-position="top">
               <el-form-item label="解析策略">
                 <el-select v-model="ragConfig.parser">
                   <el-option label="LangChain Unstructured" value="unstructured" />
                   <el-option label="LlamaParse (云端)" value="llama" />
                 </el-select>
               </el-form-item>
             </el-form>
           </div>
           <div class="config-card">
             <h3>2. 文本切分</h3>
             <el-form label-position="top">
               <el-form-item label="分块大小 (Chunk Size)">
                 <el-slider v-model="ragConfig.chunkSize" :min="128" :max="2048" :step="128" show-input />
               </el-form-item>
               <el-form-item label="重叠 (Overlap)">
                 <el-slider v-model="ragConfig.overlap" :min="0" :max="200" :step="10" show-input />
               </el-form-item>
             </el-form>
           </div>
           <div class="config-card">
             <h3>3. 嵌入模型 (Embedding)</h3>
             <el-form label-position="top">
               <el-form-item label="提供商">
                 <el-select v-model="ragConfig.embeddingProvider">
                   <el-option label="Ollama (本地)" value="ollama" />
                   <el-option label="OpenAI" value="openai" />
                   <el-option label="HuggingFace" value="hf" />
                 </el-select>
               </el-form-item>
               <el-form-item label="模型名称">
                 <el-input v-model="ragConfig.embeddingModel" placeholder="例如：nomic-embed-text" />
               </el-form-item>
             </el-form>
           </div>
           <div class="config-card">
             <h3>4. 向量数据库</h3>
             <el-form label-position="top">
               <el-form-item label="数据库类型">
                 <el-select v-model="ragConfig.vectorDb">
                   <el-option label="ChromaDB (本地)" value="chroma" />
                   <el-option label="Milvus" value="milvus" />
                   <el-option label="PGVector" value="pgvector" />
                 </el-select>
               </el-form-item>
             </el-form>
           </div>
         </div>
         <div class="save-bar">
           <el-button type="primary">保存配置</el-button>
           <el-button type="success" plain>测试管道</el-button>
         </div>
      </div>

      <!-- 5. Knowledge Base (Incremental Edit) -->
      <div v-if="currentTab === 'sources'" class="view-panel sources-view">
        <div class="toolbar">
           <h2>知识库管理</h2>
           <el-button type="primary" @click="uploadDialogVisible = true"><el-icon><Upload /></el-icon> 添加文档</el-button>
        </div>
        <el-table :data="documents" style="width: 100%">
          <el-table-column prop="name" label="文档名称" />
          <el-table-column prop="chunks" label="切片数" width="100" />
          <el-table-column prop="status" label="状态" width="120">
             <template #default="scope">
                <el-tag :type="scope.row.status === 'Indexed' ? 'success' : 'warning'">{{ scope.row.status === 'Indexed' ? '已索引' : (scope.row.status === 'Indexing...' ? '索引中' : '待处理') }}</el-tag>
             </template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="right">
             <template #default="scope">
               <el-button size="small" link type="primary" @click="reindexDocument(scope.row)">重索引</el-button>
               <el-button size="small" link type="primary" @click="viewChunks(scope.row)">查看切片</el-button>
               <el-button size="small" link type="danger" @click="deleteDocument(scope.row)">删除</el-button>
             </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 6. Database Visualization -->
      <div v-if="currentTab === 'graph'" class="view-panel graph-view">
         <div class="viz-header">
           <h2>数据库可视化</h2>
           <div class="viz-controls">
              <el-button size="small" type="primary" plain @click="fetchDbTables">连接数据库</el-button>
              <el-radio-group v-model="vizMode" size="small" @change="initViz">
                <el-radio-button label="知识图谱" />
                <el-radio-button label="向量空间" />
              </el-radio-group>
           </div>
         </div>
         <div class="viz-container" ref="vizContainer"></div>
         <div class="viz-legend" v-if="dbTables.length > 0">
            <p>已连接数据库: <strong>{{ dbConfig.database }}</strong> ({{ dbTables.length }} tables)</p>
         </div>
      </div>

      <!-- 7. Settings (Local LLM) -->
      <div v-if="currentTab === 'settings'" class="view-panel settings-view">
         <h2>系统设置</h2>
         <div class="settings-section">
            <h3>本地 LLM 服务 (Ollama)</h3>
            <el-form label-width="120px">
              <el-form-item label="Base URL">
                <el-input v-model="llmConfig.baseUrl" placeholder="http://localhost:11434" />
              </el-form-item>
              <el-form-item label="聊天模型">
                <el-input v-model="llmConfig.chatModel" placeholder="deepseek-r1:7b" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary">检查连接</el-button>
              </el-form-item>
            </el-form>
         </div>
      </div>

      <!-- 8. AI Evaluator (Original) -->
      <div v-if="currentTab === 'evaluator'" class="view-panel evaluator-view">
         <div class="chat-container">
            <div class="chat-history" ref="chatRef">
               <div v-for="(msg, i) in chatHistory" :key="i" class="chat-msg" :class="msg.role">
                  <div class="avatar"><el-icon><UserFilled v-if="msg.role === 'user'" /><Service v-else /></el-icon></div>
                  <div class="content">
                    <div v-if="msg.thinking" class="thinking-box">
                      <div class="t-head"><el-icon><Cpu /></el-icon> 深度思考</div>
                      <div class="t-body">{{ msg.thinking }}</div>
                    </div>
                    <div class="text" v-html="renderMarkdown(msg.content)"></div>
                  </div>
               </div>
            </div>
            <div class="chat-input">
               <el-input v-model="chatInput" placeholder="向 AI 评测师提问..." @keyup.enter="sendChat" />
               <el-button type="primary" @click="sendChat">发送</el-button>
            </div>
         </div>
      </div>

    </div>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadDialogVisible" title="上传文档">
       <el-upload drag action="#" multiple :auto-upload="false">
         <el-icon class="el-icon--upload"><upload-filled /></el-icon>
         <div class="el-upload__text">将文件拖到此处或 <em>点击上传</em></div>
       </el-upload>
       <template #footer>
         <el-button @click="uploadDialogVisible = false">取消</el-button>
         <el-button type="primary" @click="uploadDialogVisible = false">上传并索引</el-button>
       </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Reading, House, Notebook, MagicStick, Connection, Cpu, 
  FolderOpened, ChatDotRound, UserFilled, Setting, Sunny, Moon,
  Plus, Document, Folder, UploadFilled, Service, Upload, Delete
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// Routing Logic
const routeMap = {
  'KGDashboard': 'dashboard',
  'KGNotebook': 'notebook',
  'KGIdeaLab': 'idealab',
  'KGGraph': 'graph',
  'KGEngine': 'engine',
  'KGSources': 'sources',
  'KGSettings': 'settings',
  'KGEvaluator': 'evaluator'
}
const tabMap = {
  'dashboard': 'KGDashboard',
  'notebook': 'KGNotebook',
  'idealab': 'KGIdeaLab',
  'graph': 'KGGraph',
  'engine': 'KGEngine',
  'sources': 'KGSources',
  'settings': 'KGSettings',
  'evaluator': 'KGEvaluator'
}

const currentTab = ref(routeMap[route.name] || 'dashboard')
const isDarkMode = ref(false)
const notebookDrawer = ref(false)
const uploadDialogVisible = ref(false)

// Data
const stats = ref({ documents: 128, notes: 45 })
const ideaInput = ref('')
const ideaGenerated = ref(false)
const ideaLoading = ref(false)
const genStep = ref(0)
const ragConfig = ref({
  parser: 'unstructured',
  chunkSize: 512,
  overlap: 50,
  embeddingProvider: 'ollama',
  embeddingModel: 'nomic-embed-text',
  vectorDb: 'chroma'
})
const documents = ref([
  { id: 1, name: 'Introduction_to_AI.pdf', chunks: 120, status: 'Indexed' },
  { id: 2, name: 'System_Design.md', chunks: 45, status: 'Indexed' },
  { id: 3, name: 'Meeting_Notes.txt', chunks: 12, status: 'Pending' }
])
const vizMode = ref('知识图谱')

// 数据库配置
const dbConfig = ref({
  host: 'localhost',
  port: 3306,
  user: 'root',
  password: '',
  database: 'test_db'
})
const dbTables = ref([])

// 笔记列表
const notebooks = ref([
  { id: 1, title: 'Python 进阶', content: '# Python 进阶概念\n\n## 装饰器 (Decorators)\n装饰器是 Python 中一个非常强大且有用的工具...' },
  { id: 2, title: 'RAG 架构设计', content: '# RAG 架构设计\n\nRetrieval-Augmented Generation...' }
])
const currentNotebook = ref(notebooks.value[0])

const createNotebook = () => {
  const newNote = {
    id: Date.now(),
    title: '未命名笔记',
    content: ''
  }
  notebooks.value.push(newNote)
  currentNotebook.value = newNote
}

const selectNotebook = (note) => {
  currentNotebook.value = note
}

const deleteNotebook = (note) => {
  ElMessageBox.confirm(
    `确定要删除笔记 "${note.title}" 吗?`,
    '删除确认',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    notebooks.value = notebooks.value.filter(n => n.id !== note.id)
    if (currentNotebook.value?.id === note.id) {
      currentNotebook.value = notebooks.value.length > 0 ? notebooks.value[0] : null
    }
    ElMessage.success('笔记已删除')
  })
}

// 数据库操作
const fetchDbTables = async () => {
  // 模拟获取数据库表
  // 实际应调用后端接口
  dbTables.value = [
    { name: 'users', rows: 100 },
    { name: 'products', rows: 50 },
    { name: 'orders', rows: 200 }
  ]
  ElMessage.success('已连接到数据库，获取到 3 张表')
  // 刷新图谱
  initViz()
}

// 知识库操作
const reindexDocument = (doc) => {
  ElMessage.info(`正在重新索引: ${doc.name}`)
  doc.status = 'Indexing...'
  setTimeout(() => {
    doc.status = 'Indexed'
    ElMessage.success(`${doc.name} 索引完成`)
  }, 2000)
}

const viewChunks = (doc) => {
  ElMessage.success(`查看文档 ${doc.name} 的切片`)
  // 这里可以弹出一个对话框显示切片详情
}

const deleteDocument = (doc) => {
  ElMessageBox.confirm(
    `确定要删除文档 ${doc.name} 吗?`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    documents.value = documents.value.filter(d => d.id !== doc.id)
    ElMessage.success('删除成功')
  })
}
const llmConfig = ref({ baseUrl: 'http://localhost:11434', chatModel: 'deepseek-r1:7b' })
const chatInput = ref('')
const chatHistory = ref([
  { role: 'assistant', content: 'Hello! I am your AI Evaluator powered by DeepSeek R1. How can I help you today?' }
])

// Methods
const handleTabChange = (tab) => {
  const routeName = tabMap[tab]
  if (routeName) {
    router.push({ name: routeName })
  } else {
    currentTab.value = tab
  }
}

const navigateTo = (tab) => {
  handleTabChange(tab)
}

const toggleTheme = () => isDarkMode.value = !isDarkMode.value

const startIdeaGen = () => {
  if (!ideaInput.value) return
  ideaLoading.value = true
  setTimeout(() => {
    ideaLoading.value = false
    ideaGenerated.value = true
    simulateSteps()
  }, 1000)
}

const simulateSteps = () => {
  genStep.value = 0
  const interval = setInterval(() => {
    genStep.value++
    if (genStep.value > 3) clearInterval(interval)
  }, 1000)
}

const sendChat = () => {
  if (!chatInput.value) return
  const msg = chatInput.value
  chatInput.value = ''
  chatHistory.value.push({ role: 'user', content: msg })
  
  setTimeout(() => {
    chatHistory.value.push({
      role: 'assistant',
      thinking: 'Analyzing user request...\nSearching local knowledge base...\nFound relevant documents: [Doc A, Doc B]',
      content: `Here is the evaluation for **${msg}** based on your local knowledge base.`
    })
    nextTick(() => {
      const el = document.querySelector('.chat-history')
      if (el) el.scrollTop = el.scrollHeight
    })
  }, 1500)
}

const renderMarkdown = (text) => marked.parse(text || '')

const initViz = () => {
  const dom = document.querySelector('.viz-container')
  if (!dom) return
  const myChart = echarts.init(dom)
  
  const data = []
  const links = []
  for (let i = 0; i < 30; i++) {
    data.push({ id: i, name: 'Node ' + i, symbolSize: 20, x: Math.random()*500, y: Math.random()*500 })
    if (i > 0) links.push({ source: i, target: Math.floor(Math.random()*i) })
  }
  
  myChart.setOption({
    series: [{
      type: 'graph',
      layout: 'force',
      data: data,
      links: links,
      roam: true,
      label: { show: true }
    }]
  })
}

watch(currentTab, (val) => {
  if (val === 'graph') {
    nextTick(initViz)
  }
})

watch(() => route.name, (val) => {
   if (routeMap[val]) currentTab.value = routeMap[val]
})

onMounted(() => {
  if (currentTab.value === 'graph') initViz()
})
</script>

<style scoped lang="scss">
.deeptutor-layout {
  display: flex;
  height: calc(100vh - 60px);
  background: #f5f7fa;
  color: #333;
  
  &.dark-mode {
    background: #121212;
    color: #e0e0e0;
    .sidebar { background: #1e1e1e; border-color: #333; }
    .brand-title { color: #fff; }
    .nav-item { color: #aaa; &:hover { background: #2c2c2c; color: #fff; } &.active { background: #2c2c2c; color: #409eff; } }
    .view-panel { background: #1e1e1e; }
    .access-card, .config-card, .chat-msg .content { background: #2c2c2c; color: #eee; }
    .thinking-box { background: #333; border-color: #444; }
    .markdown-area { background: #1e1e1e; color: #eee; border-color: #333; }
    .notebook-sidebar { border-right-color: #333; }
    .nb-item:hover { background: #2c2c2c; }
  }
}

.sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  
  .brand-header {
    height: 60px; display: flex; align-items: center; padding: 0 20px; gap: 10px;
    .logo-icon { color: #409eff; }
    .brand-title { font-size: 20px; font-weight: bold; color: #2c3e50; }
  }
  
  .nav-menu {
    flex: 1; padding: 20px 0;
    .menu-category { padding: 0 20px; font-size: 11px; font-weight: bold; color: #999; margin: 15px 0 5px; }
    .nav-item {
      padding: 10px 20px; display: flex; align-items: center; gap: 10px; cursor: pointer; color: #555; font-size: 14px;
      &:hover { background: #f0f2f5; color: #333; }
      &.active { background: #e6f7ff; color: #409eff; border-right: 3px solid #409eff; }
      &.highlight { color: #722ed1; }
    }
  }
  
  .sidebar-footer {
    padding: 15px; border-top: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;
    .user-profile { display: flex; align-items: center; gap: 8px; font-size: 14px; }
    .footer-icons { display: flex; gap: 10px; cursor: pointer; color: #888; }
  }
}

.main-content {
  flex: 1; padding: 20px; overflow-y: auto;
  
  .view-panel {
    background: #fff; border-radius: 8px; padding: 25px; height: 100%; box-shadow: 0 2px 12px rgba(0,0,0,0.05); overflow-y: auto;
  }
}

/* Dashboard */
.dashboard-view {
  .welcome-banner { margin-bottom: 30px; h1 { margin-bottom: 5px; } p { color: #666; } }
  .quick-access-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px;
    .access-card {
      border: 1px solid #eee; border-radius: 10px; padding: 20px; cursor: pointer; transition: all 0.2s;
      &:hover { transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
      .icon-wrapper { width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; margin-bottom: 15px;
        &.bg-blue { background: #409eff; } &.bg-purple { background: #722ed1; } &.bg-green { background: #67c23a; }
      }
      h3 { margin-bottom: 5px; font-size: 16px; }
      p { color: #888; font-size: 13px; }
    }
  }
}

/* Notebook */
.notebook-view {
  display: flex; padding: 0 !important;
  .notebook-sidebar {
    width: 220px; border-right: 1px solid #eee; padding: 15px;
    .nb-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; font-weight: bold; }
    .nb-item { 
      padding: 8px; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 8px; color: #666; 
      &:hover { background: #f0f2f5; .delete-icon { display: block; } }
      &.active { background: #e6f7ff; color: #409eff; }
      .note-title { display: flex; align-items: center; gap: 8px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
      .delete-icon { display: none; color: #f56c6c; padding: 4px; border-radius: 4px; &:hover { background: #fef0f0; } }
    }
  }
  .notebook-editor {
    flex: 1; display: flex; flex-direction: column;
    .editor-toolbar { height: 50px; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; font-weight: bold; }
    .markdown-area { flex: 1; border: none; padding: 20px; font-size: 16px; font-family: 'Monaco', monospace; resize: none; outline: none; }
  }
}

/* IdeaLab */
.idealab-view {
  .idea-input-section {
    max-width: 800px; margin: 50px auto; text-align: center;
    .idea-textarea { margin: 20px 0; font-size: 16px; }
  }
  .idea-result-section {
    .gen-steps { margin-bottom: 30px; }
    .gen-content {
      display: flex; height: 400px; border: 1px solid #eee; border-radius: 4px;
      .file-tree { width: 200px; border-right: 1px solid #eee; padding: 10px; .indent { margin-left: 20px; } }
      .code-preview { flex: 1; background: #fafafa; padding: 20px; font-family: monospace; }
    }
  }
}

/* Engine */
.engine-view {
  .config-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 20px;
    .config-card { border: 1px solid #eee; padding: 20px; border-radius: 8px; h3 { margin-bottom: 15px; font-size: 16px; } }
  }
  .save-bar { margin-top: 20px; text-align: right; }
}

/* Graph */
.graph-view {
  .viz-header { display: flex; justify-content: space-between; margin-bottom: 10px; align-items: center; }
  .viz-controls { display: flex; gap: 10px; align-items: center; }
  .viz-container { height: 500px; border: 1px solid #eee; border-radius: 4px; }
  .viz-legend { margin-top: 10px; font-size: 12px; color: #666; text-align: right; }
}

/* Evaluator */
.evaluator-view {
  padding: 0 !important;
  .chat-container {
    height: 100%; display: flex; flex-direction: column;
    .chat-history { flex: 1; padding: 20px; overflow-y: auto; }
    .chat-msg {
      display: flex; gap: 15px; margin-bottom: 20px;
      &.user { flex-direction: row-reverse; .content { background: #409eff; color: #fff; } }
      &.assistant { .content { background: #f0f2f5; } }
      .avatar { width: 36px; height: 36px; border-radius: 50%; background: #ddd; display: flex; align-items: center; justify-content: center; }
      .content { padding: 12px 16px; border-radius: 12px; max-width: 70%; }
      .thinking-box { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px; margin-bottom: 8px; font-size: 12px; color: #666; .t-head { font-weight: bold; margin-bottom: 4px; display: flex; align-items: center; gap: 5px; } }
    }
    .chat-input { padding: 20px; border-top: 1px solid #eee; display: flex; gap: 10px; }
  }
}
</style>
