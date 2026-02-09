<template>
  <div class="knowledge-base-container">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title"> 知识库管理</h2>
        </div>
      </template>
        <p class="subtitle">管理您的文档资产，支持 PDF, Markdown, Word 等格式</p>
    </el-card>

    <div class="toolbar" style="padding: 0 20px; margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap;">
      <el-select v-model="currentProject" placeholder="选择项目过滤" clearable @change="fetchDocuments" style="width: 200px;">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      
      <el-button type="primary" @click="openUploadDialog('file')">
        <el-icon><Upload /></el-icon> 上传文档
      </el-button>
      <el-button type="primary" plain @click="openRequirementDialog">
        <el-icon><Document /></el-icon> 从需求导入
      </el-button>
      <el-button type="warning" @click="openRetrievalDialog">
        <el-icon><Search /></el-icon> 检索测试
      </el-button>
      
      <el-dropdown split-button type="info" @click="openUploadDialog('aliyun')">
        外部源
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="openUploadDialog('aliyun')">阿里云效</el-dropdown-item>
            <el-dropdown-item @click="openUploadDialog('youdao')">有道云笔记</el-dropdown-item>
            <el-dropdown-item @click="openUploadDialog('wechat')">微信公众号</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon bg-blue"><el-icon><Document /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ documents.length }}</div>
          <div class="stat-label">总文档数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon bg-green"><el-icon><Check /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ documents.filter(d => d.status === 'Indexed').length }}</div>
          <div class="stat-label">已索引</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon bg-orange"><el-icon><Connection /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ totalChunks }}</div>
          <div class="stat-label">知识切片</div>
        </div>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="documents" style="width: 100%" :header-cell-style="{ background: '#f5f7fa' }">
        <el-table-column prop="name" label="文档名称">
          <template #default="scope">
            <div class="doc-name">
              <el-icon class="file-icon"><Document /></el-icon>
              <span>{{ scope.row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100">
           <template #default="scope">
             <el-tag size="small" type="info">{{ scope.row.type.toUpperCase() }}</el-tag>
           </template>
        </el-table-column>
        <el-table-column prop="chunks" label="切片数" width="120" align="center" />
        <el-table-column prop="size" label="大小" width="120" align="center" />
        <el-table-column prop="updated_at" label="更新时间" width="180" align="center" />
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'Indexed' ? 'success' : (scope.row.status === 'Indexing...' ? 'warning' : 'info')" effect="light">
              {{ scope.row.status === 'Indexed' ? '已索引' : (scope.row.status === 'Indexing...' ? '索引中' : '待处理') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" align="right" fixed="right">
          <template #default="scope">
            <el-button size="small" link type="primary" @click="viewDocumentContent(scope.row)">
              <el-icon><View /></el-icon> 查看内容
            </el-button>
            <el-button size="small" link type="primary" @click="reindexDocument(scope.row)">
              <el-icon><Refresh /></el-icon> 重索引
            </el-button>
            <el-button size="small" link type="primary" @click="viewChunks(scope.row)">
              <el-icon><Connection /></el-icon> 查看切片
            </el-button>
            <el-button size="small" link type="danger" @click="deleteDocument(scope.row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadDialogVisible" title="添加文档" width="500px" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="数据来源">
          <el-select v-model="sourceType" placeholder="请选择数据来源">
            <el-option label="本地文件" value="file"></el-option>
            <el-option label="阿里云效" value="aliyun"></el-option>
            <el-option label="有道云笔记" value="youdao"></el-option>
            <el-option label="微信公众号" value="wechat"></el-option>
          </el-select>
        </el-form-item>
        
        <!-- Local File Upload -->
        <div v-if="sourceType === 'file'" class="upload-container">
          <el-upload
            drag
            action="#"
            multiple
            :auto-upload="false"
            :on-change="handleFileChange"
            :file-list="fileList"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">将文件拖到此处或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 PDF, Word, Markdown, TXT 文件，单个不超过 10MB</div>
            </template>
          </el-upload>
        </div>

        <!-- External Source Input -->
        <template v-else>
          <el-form-item label="文档名称" required v-if="sourceType !== 'wechat'">
            <el-input v-model="externalName" placeholder="请输入文档名称"></el-input>
          </el-form-item>
          <el-form-item :label="sourceType === 'aliyun' ? '项目/文档链接' : (sourceType === 'wechat' ? '公众号文章链接' : '笔记链接')" required>
            <el-input v-model="externalUrl" placeholder="请输入链接地址"></el-input>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="uploading" @click="handleUpload">
            {{ sourceType === 'file' ? '上传并解析' : '连接并抓取' }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Content Viewer Dialog -->
    <el-dialog
      v-model="contentDialogVisible"
      :title="viewingDoc?.name || '查看内容'"
      width="850px"
      destroy-on-close
    >
      <div v-loading="contentLoading" class="content-viewer">
        <iframe 
          v-if="viewingDoc?.type.toUpperCase() === 'HTML'" 
          :srcdoc="docContent" 
          class="html-iframe"
          frameborder="0"
          width="100%"
          height="600px"
        ></iframe>
        <pre v-else-if="docContent">{{ docContent }}</pre>
        <el-empty v-else-if="!contentLoading" description="暂无内容" />
      </div>
    </el-dialog>

    <!-- Chunk Viewer Dialog -->
    <el-dialog
      v-model="chunkDialogVisible"
      :title="`知识切片 - ${viewingDoc?.name || ''}`"
      width="70%"
    >
      <div v-loading="chunksLoading" class="chunks-container">
        <el-table :data="chunks" border style="width: 100%" height="400px">
          <el-table-column label="索引" width="80" align="center">
            <template #default="scope">
              #{{ scope.row.chunk_index }}
            </template>
          </el-table-column>
          <el-table-column prop="content" label="切片内容" show-overflow-tooltip>
            <template #default="scope">
              <div class="chunk-content-preview">{{ scope.row.content }}</div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center">
            <template #default="scope">
              <el-button link type="primary" @click="viewFullChunk(scope.row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- Full Chunk Dialog -->
    <el-dialog v-model="fullChunkVisible" title="切片详情" width="500px">
      <div class="full-chunk-content">{{ selectedChunk?.content }}</div>
    </el-dialog>
    <!-- Requirement Dialog -->
    <el-dialog v-model="requirementDialogVisible" title="从需求导入" width="500px">
      <el-form label-width="100px" style="margin-top: 20px">
        <el-form-item label="选择文档">
          <el-select v-model="selectedDocument" placeholder="请选择需求文档" filterable style="width: 100%">
            <el-option v-for="doc in requirementDocs" :key="doc.id" :label="doc.title" :value="doc.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="requirementDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRequirementSync">导入</el-button>
      </template>
    </el-dialog>

    <!-- Retrieval Dialog -->
    <el-dialog v-model="retrievalDialogVisible" title="检索测试 (RAG Debug)" width="700px">
      <div style="margin-bottom: 20px;">
        <el-input v-model="retrievalQuery" placeholder="输入问题或查询语句..." type="textarea" :rows="3" />
        <div style="margin-top: 10px; text-align: right;">
           <el-button type="primary" @click="handleRetrieval">查询</el-button>
        </div>
      </div>
      <div v-if="retrievalResult" class="retrieval-result">
        <h4>检索结果 ({{ retrievalResult.entities_count }} 实体)</h4>
        <pre class="result-box">{{ retrievalResult.context_text }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Upload, UploadFilled, Document, Refresh, View, Delete, Connection, Check, ChatDotRound, Search
} from '@element-plus/icons-vue'
import api from '@/utils/api'

const uploadDialogVisible = ref(false)
const chunkDialogVisible = ref(false)
const contentDialogVisible = ref(false)
const uploading = ref(false)
const contentLoading = ref(false)
const chunksLoading = ref(false)
const fullChunkVisible = ref(false)
const docContent = ref('')
const viewingDoc = ref(null)
const chunks = ref([])
const selectedChunk = ref(null)
const fileList = ref([])
const sourceType = ref('file')
const externalUrl = ref('')
const externalName = ref('')

const documents = ref([])
const loading = ref(false)

const projects = ref([])
const currentProject = ref(null)
const requirementDialogVisible = ref(false)
const requirementDocs = ref([])
const selectedDocument = ref(null)
const retrievalDialogVisible = ref(false)
const retrievalQuery = ref('')
const retrievalResult = ref(null)

const totalChunks = computed(() => {
  // Since backend doesn't return chunk count directly in list yet, we might need to approximate or update backend.
  // For now, assume 0 or map if available.
  return 0 
})

const fetchDocuments = async () => {
  loading.value = true
  try {
    const params = {}
    if (currentProject.value) params.project = currentProject.value
    
    const res = await api.get('/knowledge-graph/api/documents/', { params })
    documents.value = (res.data.results || res.data).map(doc => ({
      ...doc,
      type: doc.file_type || 'UNKNOWN',
      // Format size
      size: doc.size ? (doc.size / 1024).toFixed(1) + ' KB' : '-',
      // Map status
      status: doc.status === 'indexed' ? 'Indexed' : (doc.status === 'processing' ? 'Indexing...' : doc.status),
      // Chunks count is not in list response, default to '-' or 0
      chunks: '-' 
    }))
  } catch (err) {
    console.error('Failed to fetch documents', err)
    ElMessage.error('获取文档列表失败')
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const res = await api.get('/projects/')
    projects.value = res.data.results || res.data
  } catch (err) {
    console.error(err)
  }
}

const openRequirementDialog = async () => {
    requirementDialogVisible.value = true
    try {
        const docRes = await api.get('/requirement-analysis/api/documents/')
        requirementDocs.value = docRes.data.results || docRes.data
    } catch(e) {
        ElMessage.error('获取需求数据失败')
    }
}

const handleRequirementSync = async () => {
    if (!selectedDocument.value) {
        ElMessage.warning('请选择需求文档')
        return
    }

    try {
        const payload = {
            document_id: selectedDocument.value
        }

        await api.post('/knowledge-graph/api/documents/sync_requirement/', payload)
        ElMessage.success('导入成功')
        requirementDialogVisible.value = false
        fetchDocuments()
    } catch(e) {
        ElMessage.error('导入失败: ' + (e.response?.data?.error || e.message))
    }
}

const openRetrievalDialog = () => {
    retrievalDialogVisible.value = true
    retrievalResult.value = null
    retrievalQuery.value = ''
}

const handleRetrieval = async () => {
    if(!retrievalQuery.value) return
    try {
        const params = { query: retrievalQuery.value }
        if (currentProject.value) params.project_id = currentProject.value
        const res = await api.get('/knowledge-graph/api/documents/search/', { params })
        retrievalResult.value = res.data
    } catch(e) {
        ElMessage.error('检索失败')
    }
}

onMounted(() => {
  fetchDocuments()
  fetchProjects()
})

const getFileType = (filename) => {
  if (!filename) return 'UNKNOWN'
  if (filename.startsWith('http')) return 'URL'
  const ext = filename.split('.').pop().toUpperCase()
  return ext
}

const openUploadDialog = (type) => {
  sourceType.value = type
  uploadDialogVisible.value = true
}

const handleFileChange = (file) => {
  fileList.value.push(file)
}

const handleUpload = async () => {
  uploading.value = true
  
  try {
    if (sourceType.value === 'file') {
      if (fileList.value.length === 0) {
        ElMessage.warning('请先选择文件')
        uploading.value = false
        return
      }
      
      // Upload each file
      for (const file of fileList.value) {
        const formData = new FormData()
        formData.append('file', file.raw)
        formData.append('source_type', 'file')
        // Name is required by serializer if not optional, but model has it.
        // Let's ensure name is sent.
        formData.append('name', file.name) 
        
        await api.post('/knowledge-graph/api/documents/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
      }
      
      ElMessage.success('上传成功，开始后台处理')
    } else {
      if (!externalUrl.value || (sourceType.value !== 'wechat' && !externalName.value)) {
        ElMessage.warning('请填写完整信息')
        uploading.value = false
        return
      }
      
      await api.post('/knowledge-graph/api/documents/', {
        name: sourceType.value === 'wechat' ? '微信文章' : externalName.value,
        external_url: externalUrl.value,
        source_type: sourceType.value
      })
      
      ElMessage.success('连接成功，开始抓取内容')
    }
    
    // Refresh list
    await fetchDocuments()
    
    // Reset form
    uploadDialogVisible.value = false
    fileList.value = []
    externalUrl.value = ''
    externalName.value = ''
    sourceType.value = 'file'
    
  } catch (err) {
    console.error('Upload failed', err)
    ElMessage.error('上传失败: ' + (err.response?.data?.error || err.message))
  } finally {
    uploading.value = false
  }
}

const viewDocumentContent = async (row) => {
  viewingDoc.value = row
  contentDialogVisible.value = true
  contentLoading.value = true
  docContent.value = ''
  try {
    const res = await api.get(`/knowledge-graph/api/documents/${row.id}/content/`)
    docContent.value = res.data.content
  } catch (err) {
    ElMessage.error('获取内容失败')
  } finally {
    contentLoading.value = false
  }
}

const reindexDocument = async (row) => {
  ElMessage.info(`正在请求处理: ${row.name}`)
  try {
    await api.post(`/knowledge-graph/api/documents/${row.id}/process/`)
    ElMessage.success('处理请求已发送')
    fetchDocuments()
  } catch (err) {
    ElMessage.error('重索引失败')
  }
}

const viewChunks = async (row) => {
  viewingDoc.value = row
  chunkDialogVisible.value = true
  chunksLoading.value = true
  chunks.value = []
  try {
    const res = await api.get(`/knowledge-graph/api/documents/${row.id}/chunks/`)
    chunks.value = res.data
  } catch (err) {
    ElMessage.error('获取切片失败')
  } finally {
    chunksLoading.value = false
  }
}

const viewFullChunk = (chunk) => {
  selectedChunk.value = chunk
  fullChunkVisible.value = true
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
  ).then(async () => {
    try {
      await api.delete(`/knowledge-graph/api/documents/${doc.id}/`)
      ElMessage.success('删除成功')
      fetchDocuments()
    } catch (err) {
      ElMessage.error('删除失败')
    }
  })
}
</script>

<style scoped lang="scss">
.knowledge-base-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  background-color: #f5f7fa;
  overflow-y: auto;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
  .header-left {
    h2 {
      margin: 0;
      font-size: 20px;
      color: #1a1a1a;
      font-weight: 600;
    }
    .subtitle {
      margin: 4px 0 0;
      color: #909399;
      font-size: 13px;
    }
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
  
  .stat-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: transform 0.2s;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 24px;
      
      &.bg-blue { background: linear-gradient(135deg, #36cfc9 0%, #1890ff 100%); }
      &.bg-green { background: linear-gradient(135deg, #95de64 0%, #52c41a 100%); }
      &.bg-orange { background: linear-gradient(135deg, #ffc069 0%, #fa8c16 100%); }
    }
    
    .stat-info {
      .stat-value {
        font-size: 24px;
        font-weight: 700;
        color: #1a1a1a;
        line-height: 1.2;
      }
      .stat-label {
        font-size: 13px;
        color: #909399;
        margin-top: 4px;
      }
    }
  }
}

.table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: none;
  
  :deep(.el-card__body) {
    padding: 0;
    flex: 1;
  }
}

.doc-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  
  .file-icon {
    font-size: 18px;
    color: #409eff;
  }
}

.upload-container {
  padding: 20px 0;
}
.content-viewer {
  max-height: 500px;
  overflow-y: auto;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  
  pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: Consolas, Monaco, monospace;
    font-size: 14px;
    line-height: 1.6;
    color: #333;
    margin: 0;
  }

  .html-iframe {
    background: #fff;
    border: none;
    border-radius: 4px;
  }
}

.full-chunk-content {
  background: #f8f8f8;
  padding: 15px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
}
</style>
