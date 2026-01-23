<template>
  <div class="test-case-manager">
    <div class="page-header">
      <h1 class="page-title">脚本列表</h1>
      <div class="header-actions">
        <el-select v-model="selectedProject" placeholder="选择项目" style="width: 200px; margin-right: 15px" @change="onProjectChange">
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
        <el-button type="primary" @click="goToScriptEditor">
          <el-icon><Plus /></el-icon>
          新建脚本
        </el-button>
      </div>
    </div>
    
    <div class="main-content">
      <!-- 左侧：脚本列表 -->
      <div class="left-panel">
        <div class="panel-header">
          <h3>脚本列表</h3>
          <div class="search-filter">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索脚本名称..."
              clearable
              style="width: 200px; margin-right: 10px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              查询
            </el-button>
          </div>
        </div>
        
        <div class="test-case-list">
          <div
            v-for="script in scripts"
            :key="script.id"
            class="test-case-item"
            @click="viewScript(script)"
          >
            <div class="case-header">
              <div class="case-info">
                <h4 class="case-name">{{ script.name }}</h4>
                <p class="case-description">{{ script.project?.name || '未知项目' }}</p>
              </div>
              <div class="case-actions">
                <el-button size="small" text @click.stop="viewScript(script)">
                  <el-icon><View /></el-icon>
                  查看
                </el-button>
                <el-button size="small" text @click.stop="editScript(script)">
                  <el-icon><Edit /></el-icon>
                  编辑
                </el-button>
                <el-button size="small" text type="danger" @click.stop="deleteScript(script)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </div>
            </div>
            <div class="case-meta">
              <el-tag size="small" :type="script.language === 'python' ? 'success' : 'primary'">
                {{ getLanguageText(script.language) }}
              </el-tag>
              <el-tag size="small" :type="script.framework === 'playwright' ? 'warning' : 'info'">
                {{ getFrameworkText(script.framework) }}
              </el-tag>
              <span class="update-time">{{ formatTime(script.created_at) }}</span>
            </div>
          </div>
        </div>
        
        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
      
      <!-- 右侧：脚本详情 -->
      <div class="right-panel">
        <div v-if="currentScript" class="test-case-detail">
          <div class="detail-header">
            <h3>脚本详情</h3>
            <div class="detail-actions">
              <el-button type="primary" size="small" @click="editScript(currentScript)">
                <el-icon><Edit /></el-icon>
                编辑脚本
              </el-button>
              <el-button size="small" @click="renameScript(currentScript)">
                <el-icon><EditPen /></el-icon>
                重命名
              </el-button>
            </div>
          </div>
          
          <div class="execution-result">
            <div class="result-header">
              <h4>{{ currentScript.name }}</h4>
              <div>
                <el-tag size="small" :type="currentScript.language === 'python' ? 'success' : 'primary'">
                  {{ getLanguageText(currentScript.language) }}
                </el-tag>
                <el-tag size="small" :type="currentScript.framework === 'playwright' ? 'warning' : 'info'" style="margin-left: 10px">
                  {{ getFrameworkText(currentScript.framework) }}
                </el-tag>
              </div>
            </div>
            <div class="result-content">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="脚本名称" :span="2">{{ currentScript.name }}</el-descriptions-item>
                <el-descriptions-item label="项目">{{ currentScript.project?.name || '未知项目' }}</el-descriptions-item>
                <el-descriptions-item label="语言">{{ getLanguageText(currentScript.language) }}</el-descriptions-item>
                <el-descriptions-item label="框架">{{ getFrameworkText(currentScript.framework) }}</el-descriptions-item>
                <el-descriptions-item label="类型">{{ getScriptTypeText(currentScript.script_type) }}</el-descriptions-item>
                <el-descriptions-item label="创建时间" :span="2">{{ formatTime(currentScript.created_at) }}</el-descriptions-item>
                <el-descriptions-item label="更新时间" :span="2">{{ formatTime(currentScript.updated_at) }}</el-descriptions-item>
              </el-descriptions>
              
              <div class="script-content">
                <h4>脚本内容:</h4>
                <pre class="code-view">{{ currentScript.content || '(无内容)' }}</pre>
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="no-selection">
          <el-empty description="请选择一个脚本" />
        </div>
      </div>
    </div>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="脚本详情" width="70%">
      <div v-if="currentScript" class="script-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="脚本名称" :span="2">{{ currentScript.name }}</el-descriptions-item>
          <el-descriptions-item label="项目">{{ currentScript.project?.name || '未知项目' }}</el-descriptions-item>
          <el-descriptions-item label="语言">{{ getLanguageText(currentScript.language) }}</el-descriptions-item>
          <el-descriptions-item label="框架">{{ getFrameworkText(currentScript.framework) }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ getScriptTypeText(currentScript.script_type) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ formatTime(currentScript.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">{{ formatTime(currentScript.updated_at) }}</el-descriptions-item>
        </el-descriptions>

        <div class="script-content">
          <h4>脚本内容:</h4>
          <pre class="code-view">{{ currentScript.content || '(无内容)' }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button type="primary" @click="editScript(currentScript)">编辑脚本</el-button>
      </template>
    </el-dialog>

    <!-- 重命名对话框 -->
    <el-dialog v-model="showRenameDialog" title="重命名脚本" width="400px">
      <el-form :model="renameForm" label-width="80px">
        <el-form-item label="新名称">
          <el-input v-model="renameForm.newName" placeholder="请输入新的脚本名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRenameDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑脚本" width="80%" :close-on-click-modal="false">
      <div v-if="editingScript" class="script-editor">
        <div class="editor-header">
          <span class="script-name">{{ editingScript.name }}</span>
          <div class="editor-info">
            <el-tag size="small" :type="editingScript.language === 'python' ? 'success' : 'primary'">
              {{ getLanguageText(editingScript.language) }}
            </el-tag>
            <el-tag size="small" :type="editingScript.framework === 'playwright' ? 'warning' : 'info'" style="margin-left: 10px">
              {{ getFrameworkText(editingScript.framework) }}
            </el-tag>
          </div>
        </div>
        <div class="editor-container">
          <textarea
            v-model="editingScript.content"
            class="code-editor"
            placeholder="请输入脚本内容..."
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEditedScript" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, View, Edit, Delete, EditPen, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

import {
  getUiProjects,
  getTestScripts,
  updateTestScript,
  deleteTestScript
} from '@/api/ui_automation'

const router = useRouter()

// 响应式数据
const projects = ref([])
const selectedProject = ref('')
const scripts = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')

// 对话框控制
const showDetailDialog = ref(false)
const showRenameDialog = ref(false)
const showEditDialog = ref(false)

// 当前操作的脚本
const currentScript = ref(null)
const editingScript = ref(null)
const saving = ref(false)

// 重命名表单
const renameForm = reactive({
  scriptId: null,
  newName: ''
})

// 加载项目列表
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    projects.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('获取项目列表失败')
    console.error('获取项目列表失败:', error)
  }
}

// 加载脚本列表
const loadScripts = async () => {
  if (!selectedProject.value) {
    scripts.value = []
    total.value = 0
    return
  }

  try {
    const params = {
      project: selectedProject.value,
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    // 添加搜索条件
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }

    const response = await getTestScripts(params)

    // 处理分页响应
    if (response.data.results) {
      scripts.value = response.data.results
      total.value = response.data.count || 0
    } else {
      scripts.value = response.data
      total.value = response.data.length
    }
  } catch (error) {
    ElMessage.error('获取脚本列表失败')
    console.error('获取脚本列表失败:', error)
  }
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1
  loadScripts()
}

// 项目切换
const onProjectChange = async () => {
  currentPage.value = 1
  await loadScripts()
}

// 页面大小改变
const handleSizeChange = async () => {
  currentPage.value = 1
  await loadScripts()
}

// 当前页改变
const handleCurrentChange = async () => {
  await loadScripts()
}

// 跳转到脚本编辑器
const goToScriptEditor = () => {
  router.push('/ui-automation/scripts/editor')
}

// 查看脚本详情
const viewScript = (script) => {
  currentScript.value = script
  showDetailDialog.value = true
}

// 编辑脚本
const editScript = (script) => {
  editingScript.value = { ...script }
  showDetailDialog.value = false
  showEditDialog.value = true
}

// 保存编辑的脚本
const saveEditedScript = async () => {
  if (!editingScript.value) return

  try {
    saving.value = true

    await updateTestScript(editingScript.value.id, {
      content: editingScript.value.content
    })

    ElMessage.success('脚本保存成功')
    showEditDialog.value = false

    // 重新加载脚本列表
    await loadScripts()
  } catch (error) {
    ElMessage.error('脚本保存���败')
    console.error('脚本保存失败:', error)
  } finally {
    saving.value = false
  }
}

// 重命名脚本
const renameScript = (script) => {
  renameForm.scriptId = script.id
  renameForm.newName = script.name
  showRenameDialog.value = true
}

// 确认重命名
const confirmRename = async () => {
  if (!renameForm.newName.trim()) {
    ElMessage.warning('请输入新的脚本名称')
    return
  }

  try {
    await updateTestScript(renameForm.scriptId, {
      name: renameForm.newName
    })

    ElMessage.success('重命名成功')
    showRenameDialog.value = false

    // 重新加载脚本列表
    await loadScripts()
  } catch (error) {
    ElMessage.error('重命名失败')
    console.error('重命名失败:', error)
  }
}

// 删除脚本
const deleteScript = async (script) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除脚本"${script.name}"吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteTestScript(script.id)
    ElMessage.success('删除成功')

    // 重新加载脚本列表
    await loadScripts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error('删除失败:', error)
    }
  }
}

// 辅助方法
const getScriptTypeText = (type) => {
  const typeMap = {
    'CODE': '代码脚本',
    'VISUAL': '可视化脚本',
    'KEYWORD': '关键字脚本'
  }
  return typeMap[type] || type
}

const getLanguageText = (language) => {
  const languageMap = {
    'python': 'Python',
    'javascript': 'JavaScript'
  }
  return languageMap[language] || language || '未知'
}

const getFrameworkText = (framework) => {
  const frameworkMap = {
    'playwright': 'Playwright',
    'selenium': 'Selenium'
  }
  return frameworkMap[framework] || framework || '未知'
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString()
}

// 组件挂载
onMounted(async () => {
  await loadProjects()

  if (projects.value.length > 0) {
    selectedProject.value = projects.value[0].id
    await loadScripts()
  }
})
</script>

<style scoped>
.test-case-manager {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #e6e6e6;
  background: white;
}

.page-title {
  margin: 0;
  font-size: 24px;
}

.header-actions {
  display: flex;
  align-items: center;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel {
  width: 350px;
  border-right: 1px solid #e6e6e6;
  background: white;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
}

.test-case-list {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
}

.test-case-item {
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  margin-bottom: 10px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.3s;
}

.test-case-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.case-info {
  flex: 1;
}

.case-name {
  margin: 0 0 5px 0;
  font-size: 16px;
  font-weight: 600;
}

.case-description {
  margin: 0;
  color: #666;
  font-size: 14px;
  line-height: 1.4;
}

.case-actions {
  display: flex;
  gap: 5px;
}

.case-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #888;
  margin-top: 10px;
}

.right-panel {
  flex: 1;
  background: white;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e6e6e6;
}

.detail-header h3 {
  margin: 0;
}

.detail-actions {
  display: flex;
  gap: 10px;
}

.execution-result {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.result-header h4 {
  margin: 0;
}

.result-content {
  flex: 1;
  overflow-y: auto;
}

.no-selection {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #999;
}

.pagination-container {
  padding: 15px;
  border-top: 1px solid #e6e6e6;
  display: flex;
  justify-content: flex-end;
}

.script-content {
  margin-top: 20px;
}

.script-content h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.code-view {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.script-editor {
  display: flex;
  flex-direction: column;
  height: 600px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #fafafa;
  border-bottom: 1px solid #e6e6e6;
}

.script-name {
  font-weight: bold;
  font-size: 16px;
}

.editor-info {
  display: flex;
  align-items: center;
}

.editor-container {
  flex: 1;
  position: relative;
}

.code-editor {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  resize: none;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
  padding: 15px;
  background-color: #1e1e1e;
  color: #d4d4d4;
  tab-size: 2;
}
</style>
