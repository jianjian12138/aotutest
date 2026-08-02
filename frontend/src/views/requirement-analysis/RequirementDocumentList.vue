<template>
  <BasePage title="需求文档管理">
    <template #actions>
      <PremiumButton type="primary" glow @click="openUploadDialog">
        <el-icon><Upload /></el-icon> 上传需求文档
      </PremiumButton>
      <PremiumButton type="success" glow @click="openTextDialog">
        <el-icon><EditPen /></el-icon> 录入文本需求
      </PremiumButton>
    </template>

    <div class="main-layout" style="width: 100%;">
      <PremiumCard class="table-card" padding="0">
        <el-table class="premium-table" :data="documents" v-loading="loading" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="title" label="文档标题" min-width="200">
            <template #default="scope">
              <span class="document-title" @click="viewDetails(scope.row)">{{ scope.row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="document_type" label="类型" width="100">
            <template #default="scope">
              <el-tag size="small">{{ scope.row.document_type.toUpperCase() }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="viewDetails(scope.row)">详情</el-button>
              <el-button 
                link 
                type="primary" 
                v-if="scope.row.status === 'uploaded'"
                @click="analyzeDocument(scope.row)"
              >
                开始分析
              </el-button>
              <el-button 
                link 
                type="success" 
                v-if="scope.row.status === 'analyzed'"
                @click="triggerAgentCompile(scope.row)"
              >
                ✨ AI 建网络/建库
              </el-button>
              <el-button link type="danger" @click="deleteDocument(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="pagination-footer">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="fetchDocuments"
          />
        </div>
      </PremiumCard>
    </div>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadDialogVisible" title="上传需求文档" width="500px">
      <el-form label-width="100px">
        <el-form-item label="文档标题" required>
          <el-input v-model="uploadForm.title" placeholder="请输入文档标题" />
        </el-form-item>
        <el-form-item label="关联项目">
          <el-select v-model="uploadForm.project" placeholder="请选择项目" style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件" required>
          <el-upload
            ref="uploadRef"
            action="#"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
          >
            <el-button type="primary">点击选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 .txt, .md, .docx, .pdf, .png, .jpg 格式</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUpload" :loading="submitting">上传并分析</el-button>
      </template>
    </el-dialog>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailDialogVisible" title="文档详情" width="800px">
      <div v-loading="detailLoading">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="标题">{{ currentDoc?.title }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag size="small">{{ currentDoc?.document_type.toUpperCase() }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(currentDoc?.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentDoc?.status)">{{ getStatusLabel(currentDoc?.status) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 20px;">
          <h4>文档内容与预览</h4>
          <div class="content-box">
             <el-image 
                 v-if="['png', 'jpg'].includes(currentDoc?.document_type) && currentDoc?.file" 
                 :src="currentDoc.file" 
                 :preview-src-list="[currentDoc.file]"
                 fit="contain"
                 style="max-width: 100%; max-height: 400px; margin-bottom: 15px; border-radius: 4px; border: 1px solid #ebeef5; display: block;"
             />
            <pre>{{ currentDoc?.extracted_text || '暂无内容' }}</pre>
          </div>
        </div>

        <div v-if="docRequirements.length > 0" style="margin-top: 20px;">
          <h4>分析结果 ({{ docRequirements.length }} 个需求)</h4>
          <el-table :data="docRequirements" border style="width: 100%" height="300px">
            <el-table-column prop="requirement_id" label="ID" width="100" />
            <el-table-column prop="requirement_name" label="需求名称" width="200" />
            <el-table-column prop="requirement_type" label="类型" width="100" />
            <el-table-column prop="requirement_level" label="优先级" width="100" />
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
          </el-table>
        </div>
        <el-empty v-else-if="currentDoc?.status === 'analyzed'" description="未识别到需求条目" />
      </div>
    </el-dialog>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, EditPen } from '@element-plus/icons-vue'
import api from '@/utils/api'

// State
const documents = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const projects = ref([])

const uploadDialogVisible = ref(false)
const textDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const submitting = ref(false)
const detailLoading = ref(false)
const uploadFile = ref(null)

const currentDoc = ref(null)
const docRequirements = ref([])

const uploadForm = reactive({
  title: '',
  project: ''
})

const textForm = reactive({
  title: '',
  project: '',
  description: ''
})

// Lifecycle
onMounted(() => {
  fetchDocuments()
  fetchProjects()
})

// Methods
const fetchDocuments = async () => {
  loading.value = true
  try {
    const res = await api.get('/requirement-analysis/api/documents/', {
      params: { page: currentPage.value, page_size: pageSize.value }
    })
    documents.value = res.data.results || res.data
    total.value = res.data.count || documents.value.length
  } catch (err) {
    console.error(err)
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

const getStatusType = (status) => {
  const map = {
    'uploaded': 'info',
    'analyzing': 'warning',
    'analyzed': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

const getStatusLabel = (status) => {
  const map = {
    'uploaded': '待分析',
    'analyzing': '分析中',
    'analyzed': '已分析',
    'failed': '分析失败'
  }
  return map[status] || status
}

const formatDateTime = (val) => {
  if (!val) return '-'
  return new Date(val).toLocaleString()
}

// Upload Logic
const openUploadDialog = () => {
  uploadForm.title = ''
  uploadForm.project = ''
  uploadFile.value = null
  uploadDialogVisible.value = true
}

const handleFileChange = (file) => {
  uploadFile.value = file.raw
}

const submitUpload = async () => {
  if (!uploadForm.title || !uploadFile.value) {
    ElMessage.warning('请填写标题并选择文件')
    return
  }

  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('title', uploadForm.title)
    if (uploadForm.project) formData.append('project', uploadForm.project)
    formData.append('file', uploadFile.value)

    await api.post('/requirement-analysis/api/upload-analyze/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success('上传并开始分析')
    uploadDialogVisible.value = false
    fetchDocuments()
  } catch (err) {
    ElMessage.error('上传失败: ' + (err.response?.data?.error || err.message))
  } finally {
    submitting.value = false
  }
}

// Text Logic
const openTextDialog = () => {
  textForm.title = ''
  textForm.project = ''
  textForm.description = ''
  textDialogVisible.value = true
}

const submitText = async () => {
  if (!textForm.title || !textForm.description) {
    ElMessage.warning('请填写标题和描述')
    return
  }

  submitting.value = true
  try {
    await api.post('/requirement-analysis/api/analyze-text/', {
      title: textForm.title,
      project: textForm.project || null,
      description: textForm.description
    })
    ElMessage.success('已提交分析')
    textDialogVisible.value = false
    fetchDocuments()
  } catch (err) {
    ElMessage.error('提交失败: ' + (err.response?.data?.error || err.message))
  } finally {
    submitting.value = false
  }
}

const deleteDocument = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该文档吗？', '提示', { type: 'warning' })
    await api.delete(`/requirement-analysis/api/documents/${row.id}/`)
    ElMessage.success('删除成功')
    fetchDocuments()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('删除失败')
  }
}

const analyzeDocument = async (row) => {
  try {
    await api.post(`/requirement-analysis/api/documents/${row.id}/analyze/`)
    ElMessage.success('已触发分析')
    fetchDocuments()
  } catch (err) {
    ElMessage.error('触发分析失败')
  }
}

// ✨ [V2.4] AI Multi-Agent Compile Action
const triggerAgentCompile = async (row) => {
  if (!row.project) {
    ElMessage.warning('未能识别该需求文档的归属 API 项目挂载点，无法自动建库！')
    return
  }
  try {
    await ElMessageBox.confirm(
      '此机动操作将授权 Multi-Agent Executor 根据原生模型推演该 PRD，在后台自动生成 API 接口测试流节点写入测试库，是否继续？',
      '🤖 Agent 赋权执行调度确认',
      { type: 'warning' }
    )
    await api.post(`/requirement-analysis/api/documents/${row.id}/agent_compile/`, {
        project_id: row.project
    })
    ElMessage.success('🎉 Manager Agent 已经接管任务！正在后台分派 Executor 进行闭环建库...')
  } catch (err) {
    if (err !== 'cancel') {
        const msg = err.response?.data?.error || 'Agent 调度失败'
        ElMessage.error(`Agent 调度失败: ${msg}`)
    }
  }
}

const viewDetails = async (row) => {
  currentDoc.value = row
  detailDialogVisible.value = true
  docRequirements.value = []
  
  if (row.status === 'analyzed') {
    detailLoading.value = true
    try {
      // 获取分析详情（如果有ID）
      if (row.analysis_id) {
        const res = await api.get(`/requirement-analysis/api/requirements/?analysis_id=${row.analysis_id}`)
        docRequirements.value = res.data.results || res.data
      } else {
        // 尝试通过文档ID获取分析记录，或者直接获取文档关联的需求（如果后端支持）
        // 这里暂时假设已经有analysis_id在row里，或者重新获取一下文档详情
        const docRes = await api.get(`/requirement-analysis/api/documents/${row.id}/`)
        currentDoc.value = docRes.data
        if (currentDoc.value.analysis) {
           const reqRes = await api.get(`/requirement-analysis/api/requirements/?analysis_id=${currentDoc.value.analysis.id}`)
           docRequirements.value = reqRes.data.results || reqRes.data
        }
      }
    } catch (err) {
      console.error(err)
      ElMessage.warning('获取需求详情失败')
    } finally {
      detailLoading.value = false
    }
  } else if (row.status === 'analyzing') {
    ElMessage.info('文档正在分析中，请稍后查看')
  } else {
    // 尝试获取extracted_text
     detailLoading.value = true
     try {
        const res = await api.get(`/requirement-analysis/api/documents/${row.id}/extract_text/`)
        currentDoc.value.extracted_text = res.data.extracted_text
     } catch(e) {
        // ignore
     } finally {
        detailLoading.value = false
     }
  }
}
</script>

<style scoped>
.document-title {
  color: #409eff;
  cursor: pointer;
  font-weight: 500;
}
.content-box {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
}
.content-box pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: inherit;
  color: #606266;
}
</style>