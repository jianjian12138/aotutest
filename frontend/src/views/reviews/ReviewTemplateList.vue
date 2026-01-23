<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">评审模板</h1>
      <div class="header-actions">
        <el-button type="primary" @click="createTemplate">
          <el-icon><Plus /></el-icon>
          创建模板
        </el-button>
      </div>
    </div>

    <div class="card-container">
      <div class="filter-bar">
      <el-form :inline="true" :model="filters">
        <el-form-item label="项目">
          <el-select v-model="filters.project" placeholder="请选择项目" clearable @change="fetchTemplates" style="width: 200px;">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyFilters">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="templates-grid">
      <el-card
        v-for="template in templates"
        :key="template.id"
        class="template-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <span class="template-name">{{ template.name }}</span>
            <div class="card-actions">
              <el-button link type="primary" @click="useTemplate(template)">使用</el-button>
              <el-button link type="warning" @click="editTemplate(template)">编辑</el-button>
              <el-popconfirm
                title="确定要删除这个模板吗？"
                @confirm="deleteTemplate(template.id)"
              >
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </template>

        <div class="template-content">
          <div class="template-info">
            <div class="info-item">
              <span class="info-label">项目:</span>
              <span class="info-value">
                {{ Array.isArray(template.project) 
                    ? template.project.map(p => p.name).join(', ') 
                    : (template.project?.name || '未设置') }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">创建人:</span>
              <span class="info-value">{{ template.creator?.username }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">创建时间:</span>
              <span class="info-value">{{ formatDate(template.created_at) }}</span>
            </div>
          </div>

          <div class="template-description">
            {{ template.description || '暂无描述' }}
          </div>

          <div class="template-checklist">
            <div class="checklist-title">检查清单:</div>
            <ul v-if="template.checklist?.length">
              <li v-for="(item, index) in template.checklist.slice(0, 3)" :key="index">
                {{ item }}
              </li>
              <li v-if="template.checklist.length > 3" class="more-items">
                还有 {{ template.checklist.length - 3 }} 项...
              </li>
            </ul>
            <div v-else class="empty-checklist">暂无检查清单</div>
          </div>

          <div class="template-reviewers">
            <div class="reviewers-title">默认评审人:</div>
            <div class="reviewers-list">
              <el-tag
                v-for="reviewer in template.default_reviewers"
                :key="reviewer.id"
                size="small"
                class="reviewer-tag"
              >
                {{ reviewer.username }}
              </el-tag>
              <span v-if="!template.default_reviewers?.length" class="empty-reviewers">
                未设置默认评审人
              </span>
            </div>
          </div>
        </div>
      </el-card>

      <div v-if="!templates.length && !loading" class="empty-templates">
        <el-empty description="暂无评审模板" />
      </div>
    </div>
    </div>

    <!-- 模板表单对话框 -->
    <el-dialog 
      v-model="templateDialogVisible" 
      :title="isEdit ? '编辑模板' : '创建模板'" 
      width="800px"
    >
      <el-form :model="templateForm" :rules="templateRules" ref="templateFormRef" label-width="120px">
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="模板名称" prop="name">
              <el-input v-model="templateForm.name" placeholder="请输入模板名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关联项目" prop="project">
              <el-select v-model="templateForm.project" placeholder="请选择项目" @change="onProjectChange">
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="模板描述">
          <el-input
            v-model="templateForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述"
          />
        </el-form-item>

        <el-form-item label="检查清单">
          <div class="checklist-editor">
            <div
              v-for="(item, index) in templateForm.checklist"
              :key="index"
              class="checklist-item"
            >
              <el-input
                v-model="templateForm.checklist[index]"
                placeholder="请输入检查项"
              />
              <el-button 
                type="danger" 
                size="small" 
                @click="removeChecklistItem(index)"
                :icon="Delete"
              />
            </div>
            <el-button type="primary" size="small" @click="addChecklistItem">
              <el-icon><Plus /></el-icon>
              添加检查项
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="默认评审人">
          <el-select
            v-model="templateForm.default_reviewers"
            multiple
            placeholder="请选择默认评审人"
          >
            <el-option
              v-for="user in projectUsers"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="templateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const router = useRouter()

const templates = ref([])
const projects = ref([])
const projectUsers = ref([])
const loading = ref(false)
const templateDialogVisible = ref(false)
const templateFormRef = ref()
const saving = ref(false)
const isEdit = ref(false)
const editingTemplateId = ref(null)

const filters = reactive({
  project: ''
})

const templateForm = reactive({
  name: '',
  description: '',
  project: '',
  checklist: [''],
  default_reviewers: []
})

const templateRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  project: [{ required: true, message: '请选择项目', trigger: 'change' }]
}

const fetchTemplates = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.project) {
      params.project = filters.project
    }
    
    const response = await api.get('/reviews/review-templates/', { params })
    templates.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error('获取模板列表失败')
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  fetchTemplates()
}

const resetFilters = () => {
  filters.project = ''
  fetchTemplates()
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  }
}

const fetchProjectUsers = async () => {
  try {
    const response = await api.get('/auth/users/')
    projectUsers.value = response.data.results || response.data || []
  } catch (error) {
    console.error('获取用户列表失败:', error)
    ElMessage.error('获取用户列表失败')
    projectUsers.value = []
  }
}

const createTemplate = () => {
  isEdit.value = false
  resetTemplateForm()
  templateDialogVisible.value = true
}

const editTemplate = (template) => {
  isEdit.value = true
  editingTemplateId.value = template.id
  
  templateForm.name = template.name
  templateForm.description = template.description
  // 处理project字段：如果是数组，取第一个ID；如果是单个对象，取其ID
  if (Array.isArray(template.project) && template.project.length > 0) {
    templateForm.project = template.project[0].id
  } else if (template.project && template.project.id) {
    templateForm.project = template.project.id
  } else {
    templateForm.project = ''
  }
  templateForm.checklist = template.checklist.length ? [...template.checklist] : ['']
  templateForm.default_reviewers = template.default_reviewers.map(u => u.id)
  
  // 用户列表已经在页面加载时获取，不需要重新获取
  templateDialogVisible.value = true
}

const useTemplate = (template) => {
  // 使用模板创建评审
  router.push({
    path: '/reviews/create',
    query: { template: template.id }
  })
}

const saveTemplate = async () => {
  if (!templateFormRef.value) return
  
  try {
    await templateFormRef.value.validate()
    saving.value = true
    
    const data = {
      ...templateForm,
      checklist: templateForm.checklist.filter(item => item.trim()),
      // 将project转换为数组格式，因为后端期望的是列表
      project: templateForm.project ? [templateForm.project] : []
    }
    
    if (isEdit.value) {
      await api.put(`/reviews/review-templates/${editingTemplateId.value}/`, data)
      ElMessage.success('模板更新成功')
    } else {
      await api.post('/reviews/review-templates/', data)
      ElMessage.success('模板创建成功')
    }
    
    templateDialogVisible.value = false
    fetchTemplates()
    
  } catch (error) {
    console.error('保存模板失败:', error)
    ElMessage.error(isEdit.value ? '模板更新失败' : '模板创建失败')
  } finally {
    saving.value = false
  }
}

const deleteTemplate = async (id) => {
  try {
    await api.delete(`/reviews/review-templates/${id}/`)
    ElMessage.success('删除成功')
    fetchTemplates()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const resetTemplateForm = () => {
  templateForm.name = ''
  templateForm.description = ''
  templateForm.project = ''
  templateForm.checklist = ['']
  templateForm.default_reviewers = []
  editingTemplateId.value = null
}

const addChecklistItem = () => {
  templateForm.checklist.push('')
}

const removeChecklistItem = (index) => {
  if (templateForm.checklist.length > 1) {
    templateForm.checklist.splice(index, 1)
  }
}

const onProjectChange = (projectId) => {
  if (projectId) {
    // 清空默认评审人选择
    templateForm.default_reviewers = []
  }
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}


onMounted(() => {
  fetchTemplates()
  fetchProjects()
  fetchProjectUsers() // 页面加载时就获取所有用户
})
</script>

<style scoped>
/* 页面特定样式 */
.page-container {
  padding: 0;
  display: flex;
  flex-direction: column;

  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #e6e6e6;
  background: white;
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 16px;
}

.page-title::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 20px;
  background: var(--primary-color, #409eff);
  border-radius: 2px;
}

.header-actions {
  display: flex;
  gap: 15px;
}
.review-template-list {
  padding: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.template-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .template-name {
      font-weight: 600;
      font-size: 16px;
    }
    
    .card-actions {
      display: flex;
      gap: 8px;
    }
  }
}

.template-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  
  .template-info {
    .info-item {
      display: flex;
      margin-bottom: 8px;
      
      .info-label {
        min-width: 80px;
        color: #909399;
        font-size: 14px;
      }
      
      .info-value {
        color: #303133;
        font-size: 14px;
      }
    }
  }
  
  .template-description {
    color: #606266;
    line-height: 1.6;
    font-size: 14px;
  }
  
  .template-checklist {
    .checklist-title {
      font-weight: 500;
      margin-bottom: 8px;
      color: #303133;
    }
    
    ul {
      margin: 0;
      padding-left: 20px;
      
      li {
        margin-bottom: 4px;
        color: #606266;
        font-size: 14px;
        
        &.more-items {
          color: #909399;
          font-style: italic;
        }
      }
    }
    
    .empty-checklist {
      color: #909399;
      font-size: 14px;
      font-style: italic;
    }
  }
  
  .template-reviewers {
    .reviewers-title {
      font-weight: 500;
      margin-bottom: 8px;
      color: #303133;
    }
    
    .reviewers-list {
      .reviewer-tag {
        margin-right: 8px;
        margin-bottom: 4px;
      }
      
      .empty-reviewers {
        color: #909399;
        font-size: 14px;
        font-style: italic;
      }
    }
  }
}

.empty-templates {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.checklist-editor {
  .checklist-item {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
    align-items: center;
  }
}
</style>