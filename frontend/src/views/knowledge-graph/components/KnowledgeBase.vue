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
      <el-button type="primary" @click="uploadDialogVisible = true">
        <el-icon><Upload /></el-icon> 添加文档
      </el-button>
    

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
             <el-tag size="small" type="info">{{ getFileType(scope.row.name) }}</el-tag>
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
        <el-table-column label="操作" width="250" align="right" fixed="right">
          <template #default="scope">
            <el-button size="small" link type="primary" @click="reindexDocument(scope.row)">
              <el-icon><Refresh /></el-icon> 重索引
            </el-button>
            <el-button size="small" link type="primary" @click="viewChunks(scope.row)">
              <el-icon><View /></el-icon> 查看切片
            </el-button>
            <el-button size="small" link type="danger" @click="deleteDocument(scope.row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadDialogVisible" title="上传文档" width="500px" destroy-on-close>
      <div class="upload-container">
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
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleUpload" :loading="uploading">上传并索引</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Upload, UploadFilled, Document, Refresh, View, Delete, Connection, Check
} from '@element-plus/icons-vue'

const uploadDialogVisible = ref(false)
const uploading = ref(false)
const fileList = ref([])

// Mock Data
const documents = ref([
  { id: 1, name: 'Introduction_to_AI.pdf', chunks: 120, size: '2.4 MB', status: 'Indexed', updated_at: '2023-11-15 10:00' },
  { id: 2, name: 'System_Design.md', chunks: 45, size: '128 KB', status: 'Indexed', updated_at: '2023-11-14 15:30' },
  { id: 3, name: 'Meeting_Notes.txt', chunks: 12, size: '45 KB', status: 'Pending', updated_at: '2023-11-16 09:20' }
])

const totalChunks = computed(() => documents.value.reduce((acc, doc) => acc + doc.chunks, 0))

const getFileType = (filename) => {
  const ext = filename.split('.').pop().toUpperCase()
  return ext
}

const handleFileChange = (file) => {
  fileList.value.push(file)
}

const handleUpload = () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  uploading.value = true
  setTimeout(() => {
    // Mock upload success
    fileList.value.forEach(file => {
      documents.value.unshift({
        id: Date.now() + Math.random(),
        name: file.name,
        chunks: 0,
        size: (file.size / 1024).toFixed(1) + ' KB',
        status: 'Indexing...',
        updated_at: new Date().toLocaleString()
      })
    })
    
    // Simulate indexing completion
    setTimeout(() => {
       documents.value.forEach(d => {
         if (d.status === 'Indexing...') {
           d.status = 'Indexed'
           d.chunks = Math.floor(Math.random() * 100) + 10
         }
       })
       ElMessage.success('文档索引完成')
    }, 2000)

    uploading.value = false
    uploadDialogVisible.value = false
    fileList.value = []
    ElMessage.success('上传成功，开始后台索引')
  }, 1000)
}

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
</style>
