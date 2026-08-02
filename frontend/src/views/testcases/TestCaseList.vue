<template>
  <BasePage title="测试用例">
    <template #actions>
      <PremiumButton 
        v-if="selectedTestCases.length > 0" 
        type="danger" 
        @click="batchDeleteTestCases"
        :disabled="isDeleting">
        <el-icon><Delete /></el-icon>
        批量删除 ({{ selectedTestCases.length }})
      </PremiumButton>
      <PremiumButton type="success" @click="exportToExcel">
        <el-icon><Download /></el-icon>
        导出Excel
      </PremiumButton>
      <PremiumButton type="warning" @click="handleImport">
        <el-icon><Upload /></el-icon>
        导入用例
      </PremiumButton>
      <PremiumButton type="primary" glow @click="$router.push('/ai-generation/testcases/create')">
        <el-icon><Plus /></el-icon>
        新建用例
      </PremiumButton>
    </template>
    <div class="main-layout" style="display: flex; gap: 20px; align-items: flex-start;">
      <!-- 最左侧：模块树 -->
      <PremiumCard class="module-panel" padding="16px" style="width: 280px; flex-shrink: 0; min-height: 500px">
        <div class="sidebar-header" style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0; font-size: 16px;">用例模块</h3>
          <el-button type="primary" link size="small" @click="showCreateModuleDialog = true" title="创建模块">
            <el-icon><FolderAdd /></el-icon>
          </el-button>
        </div>
        <div class="module-tree-container" style="max-height: calc(100vh - 200px); overflow-y: auto;">
          <el-tree
            ref="moduleTreeRef"
            :data="moduleTreeData"
            :props="moduleTreeProps"
            node-key="id"
            :expand-on-click-node="false"
            :default-expanded-keys="expandedModuleKeys"
            @node-click="onModuleNodeClick"
            @node-contextmenu="onModuleNodeRightClick"
            highlight-current
          >
            <template #default="{ node, data }">
              <div class="tree-node" style="display: flex; align-items: center; gap: 8px; width: 100%">
                <el-icon><Folder /></el-icon>
                <span class="node-label" style="font-size: 14px;">{{ node.label }}</span>
                <span v-if="data.case_count > 0" style="background: #f0f2f5; color: #909399; font-size: 12px; padding: 0 6px; border-radius: 10px; margin-left: auto;">{{ data.case_count }}</span>
              </div>
            </template>
          </el-tree>
        </div>
      </PremiumCard>

    <div class="testcase-list-wrapper" style="flex: 1; min-width: 0;">
      <!-- 搜索和筛选 -->
      <PremiumCard class="filter-card" padding="16px 24px">
        <el-row :gutter="20">
          <el-col :span="5">
            <el-input
              v-model="searchText"
              placeholder="搜索用例标题"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="projectFilter" placeholder="关联项目" clearable @change="handleFilter">
              <el-option
                v-for="project in projects"
                :key="project.id"
                :label="project.name"
                :value="project.id"
              />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-select v-model="priorityFilter" placeholder="优先级筛选" clearable @change="handleFilter">
              <el-option label="低" value="low" />
              <el-option label="中" value="medium" />
              <el-option label="高" value="high" />
              <el-option label="紧急" value="critical" />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="handleFilter">
              <el-option label="草稿" value="draft" />
              <el-option label="激活" value="active" />
              <el-option label="废弃" value="deprecated" />
            </el-select>
          </el-col>
        </el-row>
      </PremiumCard>
      
      <!-- 测试用例表格 -->
      <PremiumCard class="table-card" padding="0">
        <el-table class="premium-table" 
        :data="testcases" 
        v-loading="loading" 
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column type="index" label="序号" width="80" :index="getSerialNumber" />
        <el-table-column prop="title" label="用例标题" min-width="250">
          <template #default="{ row }">
            <el-link @click="goToTestCase(row.id)" type="primary">
              {{ row.title }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="project.name" label="关联项目" width="150">
          <template #default="{ row }">
            {{ row.project?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="versions" label="关联版本" width="200">
          <template #default="{ row }">
            <div v-if="row.versions && row.versions.length > 0" class="version-tags">
              <el-tag 
                v-for="version in row.versions.slice(0, 2)" 
                :key="version.id" 
                size="small" 
                :type="version.is_baseline ? 'warning' : 'info'"
                class="version-tag"
              >
                {{ version.name }}
              </el-tag>
              <el-tooltip v-if="row.versions.length > 2" :content="getVersionsTooltip(row.versions)">
                <el-tag size="small" type="info" class="version-tag">
                  +{{ row.versions.length - 2 }}
                </el-tag>
              </el-tooltip>
            </div>
            <span v-else class="no-version">未关联版本</span>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="test_type" label="测试类型" width="120">
          <template #default="{ row }">
            {{ getTypeText(row.test_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="author.username" label="作者" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button link type="primary" @click="editTestCase(row)">编辑</el-button>
              <el-divider direction="vertical" />
              <el-button link type="danger" @click="deleteTestCase(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
        <div class="pagination-footer">
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
      </PremiumCard>
    </div>
    </div>

    <!-- 新建/编辑模块对话框 -->
    <el-dialog v-model="showCreateModuleDialog" :title="editingModule ? '编辑模块' : '创建模块'" width="450px" class="premium-dialog">
      <el-form ref="moduleFormRef" :model="moduleForm" :rules="moduleRules" label-width="90px">
        <el-form-item label="模块名称" prop="name">
          <el-input v-model="moduleForm.name" placeholder="请输入模块名称" />
        </el-form-item>
        <el-form-item label="父级模块" prop="parent">
          <el-tree-select
            v-model="moduleForm.parent"
            :data="moduleTreeData"
            :props="moduleTreeProps"
            node-key="id"
            value-key="id"
            placeholder="请选择父级模块(可选)"
            check-strictly
            clearable
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateModuleDialog = false">取消</el-button>
          <el-button type="primary" @click="saveModuleForm">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 右键菜单 -->
    <ul v-show="showContextMenu" class="context-menu" :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px', position: 'fixed', background: 'white', border: '1px solid #e4e7ed', boxShadow: '0 2px 12px 0 rgba(0,0,0,0.1)', borderRadius: '4px', padding: '5px 0', margin: '0', listStyle: 'none', zIndex: 3000, minWidth: '120px' }">
      <li class="context-menu-item" @click="addTestCaseToModule" style="padding: 8px 15px; cursor: pointer; fontSize: 14px; color: #606266;">添加用例</li>
      <li class="context-menu-item" @click="addSubModule" style="padding: 8px 15px; cursor: pointer; fontSize: 14px; color: #606266;">添加子模块</li>
      <li class="context-menu-item" @click="editModuleNode" style="padding: 8px 15px; cursor: pointer; fontSize: 14px; color: #606266;">编辑</li>
      <li class="context-menu-item" @click="deleteModuleNode" style="padding: 8px 15px; cursor: pointer; fontSize: 14px; color: #606266;">删除</li>
    </ul>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入测试用例" width="500px" class="premium-dialog">
      <el-form :model="importForm" label-width="100px">
        <el-form-item label="目标项目" required>
          <el-select v-model="importForm.projectId" placeholder="请选择项目" style="width: 100%">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="文件类型" required>
          <el-select v-model="importForm.fileType" placeholder="请选择类型" style="width: 100%">
            <el-option label="Excel (.xlsx)" value="excel" />
            <el-option label="CSV (.csv)" value="csv" />
            <el-option label="JSON (.json)" value="json" />
            <el-option label="YAML (.yaml)" value="yaml" />
            <el-option label="Postman Collection (.json)" value="postman" />
            <el-option label="JMeter Script (.jmx)" value="jmeter" />
            <el-option label="ZIP包 (AI_TEST兼容)" value="zip" />
          </el-select>
        </el-form-item>
        <el-form-item label="上传文件" required>
          <el-upload
            ref="uploadRef"
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            style="width: 100%"
          >
            <template #trigger>
              <el-button type="primary">选择文件</el-button>
            </template>
            <template #tip>
              <div class="el-upload__tip">
                支持 Excel, CSV, JSON, YAML 或 ZIP 格式
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="importDialogVisible = false">取消</el-button>
          <PremiumButton type="primary" @click="submitImport" :loading="isImporting" glow>
            导入
          </PremiumButton>
        </div>
      </template>
    </el-dialog>

  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElUpload } from 'element-plus'
import { Plus, Search, Download, Delete, Upload, Folder, FolderAdd } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import * as XLSX from 'xlsx'

const router = useRouter()
const loading = ref(false)
const testcases = ref([])
const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchText = ref('')
const projectFilter = ref('')
const priorityFilter = ref('')
const statusFilter = ref('')
const selectedTestCases = ref([])
const isDeleting = ref(false)

// Module variables
const moduleTreeData = ref([])
const expandedModuleKeys = ref([])
const selectedModuleId = ref(null)
const selectedModuleNode = ref(null)
const moduleTreeProps = { children: 'children', label: 'name' }
const moduleTreeRef = ref(null)

const showCreateModuleDialog = ref(false)
const editingModule = ref(null)
const moduleFormRef = ref(null)
const moduleForm = reactive({ name: '', parent: null })
const moduleRules = { name: [{ required: true, message: '请输入模块名称', trigger: 'blur' }] }

const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const rightClickedModule = ref(null)

const getTestCaseModules = (params) => api.get('/testcases/modules/tree/', { params })
const createTestCaseModule = (data) => api.post('/testcases/modules/', data)
const updateTestCaseModule = (id, data) => api.patch(`/testcases/modules/${id}/`, data)
const deleteTestCaseModule = (id) => api.delete(`/testcases/modules/${id}/`)

const loadModuleTree = async () => {
  if (!projectFilter.value && projects.value.length > 0) {
    projectFilter.value = projects.value[0].id
  }
  if (!projectFilter.value) {
    moduleTreeData.value = []
    return
  }
  try {
    const res = await getTestCaseModules({ project: projectFilter.value })
    moduleTreeData.value = res.data?.results || res.data || []
  } catch(error) {
    console.error('获取模块树失败:', error)
  }
}

const onModuleNodeClick = (data) => {
  selectedModuleId.value = data.id
  selectedModuleNode.value = data
  fetchTestCases()
}

const onModuleNodeRightClick = (event, data) => {
  event.preventDefault()
  showContextMenu.value = false
  rightClickedModule.value = data
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  showContextMenu.value = true
  
  const hideMenu = () => {
    showContextMenu.value = false
    document.removeEventListener('click', hideMenu)
  }
  setTimeout(() => document.addEventListener('click', hideMenu), 100)
}

const addTestCaseToModule = () => {
  router.push({ path: '/ai-generation/testcases/create', query: { module_id: rightClickedModule.value.id } })
}

const addSubModule = () => {
  editingModule.value = null
  moduleForm.name = ''
  moduleForm.parent = rightClickedModule.value ? rightClickedModule.value.id : null
  showCreateModuleDialog.value = true
}

const editModuleNode = () => {
  editingModule.value = rightClickedModule.value
  moduleForm.name = rightClickedModule.value.name
  moduleForm.parent = rightClickedModule.value.parent || null
  showCreateModuleDialog.value = true
}

const deleteModuleNode = async () => {
  if (!rightClickedModule.value) return
  try {
    await ElMessageBox.confirm(`确定删除模块 "${rightClickedModule.value.name}" 吗？该目录下的所有用例及子模块将解除关联或被删除。`, '提示', { type: 'warning' })
    await deleteTestCaseModule(rightClickedModule.value.id)
    ElMessage.success('删除成功')
    if (selectedModuleId.value === rightClickedModule.value.id) {
      selectedModuleId.value = null
      fetchTestCases()
    }
    loadModuleTree()
  } catch(e) {}
}

const saveModuleForm = async () => {
  if (!moduleFormRef.value) return
  const valid = await moduleFormRef.value.validate()
  if (!valid) return
  try {
    const data = {
      name: moduleForm.name,
      parent: moduleForm.parent || null,
      project: projectFilter.value
    }
    if (editingModule.value) {
      await updateTestCaseModule(editingModule.value.id, data)
      ElMessage.success('修改成功')
    } else {
      await createTestCaseModule(data)
      ElMessage.success('创建成功')
    }
    showCreateModuleDialog.value = false
    loadModuleTree()
  } catch(e) {
    ElMessage.error(editingModule.value ? '修改失败' : '创建失败')
  }
}

// Import Dialog
const importDialogVisible = ref(false)
const isImporting = ref(false)
const importForm = ref({
  projectId: '',
  fileType: 'excel',
  file: null
})
const uploadRef = ref(null)

const handleImport = () => {
  importForm.value = {
    projectId: projectFilter.value || (projects.value.length > 0 ? projects.value[0].id : ''),
    fileType: 'excel',
    file: null
  }
  importDialogVisible.value = true
}

const handleFileChange = (file) => {
  importForm.value.file = file.raw
}

const submitImport = async () => {
  if (!importForm.value.file) {
    ElMessage.warning('请选择文件')
    return
  }
  if (!importForm.value.projectId) {
    ElMessage.warning('请选择项目')
    return
  }

  isImporting.value = true
  const formData = new FormData()
  formData.append('file', importForm.value.file)
  formData.append('project_id', importForm.value.projectId)
  formData.append('file_type', importForm.value.fileType)

  try {
    const response = await api.post('/testcases/import/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    ElMessage.success(response.data.message || '导入成功')
    importDialogVisible.value = false
    fetchTestCases()
  } catch (error) {
    console.error('Import failed:', error)
    ElMessage.error(error.response?.data?.error || '导入失败')
  } finally {
    isImporting.value = false
  }
}

const fetchTestCases = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      project: projectFilter.value,
      priority: priorityFilter.value,
      status: statusFilter.value
    }
    if (selectedModuleId.value) {
      params.module = selectedModuleId.value
    }
    const response = await api.get('/testcases/', { params })
    testcases.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取测试用例列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchTestCases()
}

const handleFilter = () => {
  currentPage.value = 1
  selectedModuleId.value = null
  loadModuleTree()
  fetchTestCases()
}

const handlePageChange = () => {
  fetchTestCases()
}

// 分页事件处理
const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
  fetchTestCases()
}

const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
  fetchTestCases()
}

const goToTestCase = (id) => {
  router.push(`/ai-generation/testcases/${id}`)
}

const editTestCase = (testcase) => {
  router.push(`/ai-generation/testcases/${testcase.id}/edit`)
}

const deleteTestCase = async (testcase) => {
  try {
    await ElMessageBox.confirm('确定要删除这个测试用例吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/testcases/${testcase.id}/`)
    ElMessage.success('测试用例删除成功')
    fetchTestCases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('测试用例删除失败')
    }
  }
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedTestCases.value = selection
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除
const batchDeleteTestCases = async () => {
  if (selectedTestCases.value.length === 0) {
    ElMessage.warning('请先选择要删除的测试用例')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedTestCases.value.length} 个测试用例吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    isDeleting.value = true
    let successCount = 0
    let failCount = 0

    // 逐个删除选中的测试用例
    for (const testcase of selectedTestCases.value) {
      try {
        await api.delete(`/testcases/${testcase.id}/`)
        successCount++
      } catch (error) {
        console.error(`删除测试用例 ${testcase.id} 失败:`, error)
        failCount++
      }
    }

    // 显示删除结果
    if (successCount > 0) {
      ElMessage.success(`成功删除 ${successCount} 个测试用例${failCount > 0 ? `，${failCount} 个失败` : ''}`)
    } else {
      ElMessage.error('删除失败')
    }

    // 清空选择并重新加载列表
    selectedTestCases.value = []
    fetchTestCases()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败: ' + (error.message || '未知错误'))
    }
  } finally {
    isDeleting.value = false
  }
}

const getPriorityText = (priority) => {
  const textMap = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '紧急'
  }
  return textMap[priority] || priority
}

const getStatusType = (status) => {
  const typeMap = {
    draft: 'info',
    active: 'success',
    deprecated: 'warning'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    draft: '草稿',
    active: '激活',
    deprecated: '废弃'
  }
  return textMap[status] || status
}

const getTypeText = (type) => {
  const textMap = {
    functional: '功能测试',
    integration: '集成测试',
    api: 'API测试',
    ui: 'UI测试',
    performance: '性能测试',
    security: '安全测试'
  }
  return textMap[type] || '-'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const getVersionsTooltip = (versions) => {
  return versions.map(v => v.name + (v.is_baseline ? ' (基线)' : '')).join('、')
}

// 将HTML的<br>标签转换为换行符（用于Excel导出）
const convertBrToNewline = (text) => {
  if (!text) return ''
  return text.replace(/<br\s*\/?>/gi, '\n')
}

const exportToExcel = async () => {
  try {
    loading.value = true
    
    // 获取所有测试用例数据（不分页）
    const response = await api.get('/testcases/', { 
      params: { 
        page_size: 9999, // 获取所有数据
        search: searchText.value,
        project: projectFilter.value,
        priority: priorityFilter.value,
        status: statusFilter.value
      } 
    })
    
    const allTestCases = response.data.results || []
    
    if (allTestCases.length === 0) {
      ElMessage.warning('没有测试用例数据可导出')
      return
    }
    
    // 创建工作簿
    const workbook = XLSX.utils.book_new()
    
    // 准备Excel数据
    const worksheetData = [
      ['测试用例编号', '用例标题', '关联项目', '关联版本', '前置条件', '操作步骤', '预期结果', '优先级', '状态', '测试类型', '作者', '创建时间']
    ]
    
    allTestCases.forEach((testcase, index) => {
      const versions = testcase.versions && testcase.versions.length > 0 
        ? testcase.versions.map(v => v.name + (v.is_baseline ? '(基线)' : '')).join('、')
        : '未关联版本'
      
      worksheetData.push([
        `TC${String(index + 1).padStart(3, '0')}`,
        testcase.title || '',
        testcase.project?.name || '',
        versions,
        convertBrToNewline(testcase.preconditions || ''),
        convertBrToNewline(testcase.steps || ''),
        convertBrToNewline(testcase.expected_result || ''),
        getPriorityText(testcase.priority),
        getStatusText(testcase.status),
        getTypeText(testcase.test_type),
        testcase.author?.username || '',
        formatDate(testcase.created_at)
      ])
    })
    
    // 创建工作表
    const worksheet = XLSX.utils.aoa_to_sheet(worksheetData)
    
    // 设置列宽
    const colWidths = [
      { wch: 15 }, // 测试用例编号
      { wch: 30 }, // 用例标题
      { wch: 20 }, // 关联项目
      { wch: 25 }, // 关联版本
      { wch: 30 }, // 前置条件
      { wch: 40 }, // 操作步骤
      { wch: 30 }, // 预期结果
      { wch: 10 }, // 优先级
      { wch: 10 }, // 状态
      { wch: 15 }, // 测试类型
      { wch: 15 }, // 作者
      { wch: 20 }  // 创建时间
    ]
    worksheet['!cols'] = colWidths
    
    // 设置表头样式
    for (let col = 0; col < worksheetData[0].length; col++) {
      const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col })
      if (!worksheet[cellAddress]) continue
      worksheet[cellAddress].s = {
        font: { bold: true },
        alignment: { horizontal: 'center', vertical: 'center', wrapText: true }
      }
    }
    
    // 设置其他行的样式
    for (let row = 1; row < worksheetData.length; row++) {
      for (let col = 0; col < worksheetData[row].length; col++) {
        const cellAddress = XLSX.utils.encode_cell({ r: row, c: col })
        if (worksheet[cellAddress]) {
          worksheet[cellAddress].s = {
            alignment: { vertical: 'top', wrapText: true }
          }
        }
      }
    }
    
    // 添加工作表到工作簿
    XLSX.utils.book_append_sheet(workbook, worksheet, '测试用例')
    
    // 生成文件名
    const fileName = `测试用例_${new Date().toISOString().slice(0, 10)}.xlsx`
    
    // 导出文件
    XLSX.writeFile(workbook, fileName)
    
    ElMessage.success('测试用例导出成功')
  } catch (error) {
    console.error('导出测试用例失败:', error)
    ElMessage.error('导出测试用例失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
    if (!projectFilter.value && projects.value.length > 0) {
      projectFilter.value = projects.value[0].id
      loadModuleTree()
      fetchTestCases()
    }
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  }
}

onMounted(() => {
  fetchProjects()
  if (projectFilter.value) {
    fetchTestCases()
  }
})
</script>

<style lang="scss" scoped>

.testcase-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.filter-card {
  margin-bottom: 8px;
}

.text-right {
  text-align: right;
}

.total-text {
  font-size: 14px;
  color: var(--slate-500);
}

.pagination-footer {
  padding: 24px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--border-light);
  background: var(--slate-50);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.premium-table) {
  .el-table__row {
    transition: background-color 0.3s;
    &:hover {
      background-color: var(--slate-50) !important;
    }
  }
}

.priority-tag {
  &.low { color: #67c23a; }
  &.medium { color: #e6a23c; }
  &.high { color: #f56c6c; }
  &.critical { color: #f56c6c; font-weight: bold; }
}
/* 页面特定样式 */






.version-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  
  .version-tag {
    margin: 0;
  }
}

.no-version {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}
</style>
