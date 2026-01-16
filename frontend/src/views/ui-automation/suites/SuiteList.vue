<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">测试套件管理</h1>
      <el-select v-model="projectId" placeholder="选择项目" style="width: 200px; margin-right: 15px" @change="onProjectChange">
        <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
      </el-select>
      <el-button type="primary" @click="handleNewSuite">
        <el-icon><Plus /></el-icon>
        新增套件
      </el-button>
    </div>

    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-input
              v-model="searchText"
              placeholder="搜索套件名称或描述"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
        </el-row>
      </div>

      <el-table :data="suites" v-loading="loading" style="width: 100%">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="套件名称" min-width="200">
          <template #default="{ row }">
            <el-link @click="editSuite(row.id)" type="primary">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="包含用例数" width="120">
          <template #default="{ row }">
            {{ row.test_case_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="执行状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getExecutionStatusTag(row.execution_status)">
              {{ getExecutionStatusText(row.execution_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="通过数" width="90">
          <template #default="{ row }">
            <span style="color: #67c23a; font-weight: bold;">{{ row.passed_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="失败数" width="90">
          <template #default="{ row }">
            <span style="color: #f56c6c; font-weight: bold;">{{ row.failed_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" :formatter="formatDate" />
        <el-table-column prop="updated_at" label="更新时间" width="180" :formatter="formatDate" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="editSuite(row.id)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="success" @click="runSuite(row)">
              <el-icon><RefreshRight /></el-icon>
              运行
            </el-button>
            <el-button size="small" type="danger" @click="deleteSuite(row.id)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 创建/编辑套件对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="isEditing ? '编辑测试套件' : '新增测试套件'"
      width="900px"
      :close-on-click-modal="false"
    >
      <el-form ref="createFormRef" :model="createForm" :rules="formRules" label-width="100px">
        <el-form-item label="套件名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入套件名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" placeholder="请输入套件描述" />
        </el-form-item>
        <el-form-item label="测试用例">
          <div class="test-case-selector">
            <div class="selector-panel">
              <div class="panel-header">
                <h4>可用用例</h4>
                <el-input
                  v-model="testCaseSearchText"
                  placeholder="搜索用例"
                  size="small"
                  clearable
                  style="width: 200px;"
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </div>
              <div class="panel-content">
                <el-table
                  :data="filteredAvailableTestCases"
                  height="300"
                  @row-click="handleTestCaseRowClick"
                  :row-class-name="getTestCaseRowClassName"
                >
                  <el-table-column prop="name" label="用例名称" min-width="150" show-overflow-tooltip />
                  <el-table-column prop="priority" label="优先级" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="getPriorityTag(row.priority)">
                        {{ getPriorityText(row.priority) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="status" label="状态" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="getCaseStatusTag(row.status)">
                        {{ getCaseStatusText(row.status) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="80">
                    <template #default="{ row }">
                      <el-button size="small" text @click.stop="addTestCase(row)">
                        <el-icon><ArrowRight /></el-icon>
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>

            <div class="selector-panel">
              <div class="panel-header">
                <h4>已选用例 ({{ selectedTestCases.length }})</h4>
              </div>
              <div class="panel-content">
                <el-table
                  :data="selectedTestCases"
                  height="300"
                >
                  <el-table-column prop="name" label="用例名称" min-width="150" show-overflow-tooltip />
                  <el-table-column prop="priority" label="优先级" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="getPriorityTag(row.priority)">
                        {{ getPriorityText(row.priority) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120">
                    <template #default="{ row, $index }">
                      <el-button
                        size="small"
                        text
                        @click="moveUp($index)"
                        :disabled="$index === 0"
                      >
                        <el-icon><Top /></el-icon>
                      </el-button>
                      <el-button
                        size="small"
                        text
                        @click="moveDown($index)"
                        :disabled="$index === selectedTestCases.length - 1"
                      >
                        <el-icon><Bottom /></el-icon>
                      </el-button>
                      <el-button
                        size="small"
                        text
                        type="danger"
                        @click="removeTestCase($index)"
                      >
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="cancelCreate">取消</el-button>
          <el-button type="primary" @click="handleCreate" :loading="saving">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 运行配置对话框 -->
    <el-dialog v-model="showRunDialog" title="执行测试套件" width="600px">
      <el-form :model="runConfig" label-width="120px">
        <el-form-item label="测试引擎">
          <el-select v-model="runConfig.engine" placeholder="请选择测试引擎">
            <el-option label="Playwright" value="playwright" />
            <el-option label="Selenium" value="selenium" />
          </el-select>
        </el-form-item>
        <el-form-item label="浏览器">
          <el-select v-model="runConfig.browser" placeholder="请选择浏览器">
            <el-option label="Chrome" value="chrome" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="Safari" value="safari" />
            <el-option label="Edge" value="edge" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行模式">
          <el-radio-group v-model="runConfig.headless">
            <el-radio :label="false">有头模式</el-radio>
            <el-radio :label="true">无头模式</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showRunDialog = false">取消</el-button>
          <el-button 
            type="primary" 
            @click="confirmRunSuite" 
            :loading="running"
          >
            开始执行
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Search, Edit, Delete, RefreshRight, Collection,
  ArrowRight, Top, Bottom
} from '@element-plus/icons-vue'
import {
  getUiProjects,
  getTestSuites,
  createTestSuite,
  updateTestSuite,
  deleteTestSuite,
  getTestCases,
  getTestSuiteTestCases,
  addTestCaseToTestSuite,
  removeTestCaseFromTestSuite,
  updateTestCaseOrder,
  runTestSuite
} from '@/api/ui_automation'

// 响应式数据
const projects = ref([])
const projectId = ref('')
const suites = ref([])
const loading = ref(false)
const searchText = ref('')
const total = ref(0)
const pagination = reactive({
  currentPage: 1,
  pageSize: 20
})

// 对话框控制
const showCreateDialog = ref(false)
const showRunDialog = ref(false)
const isEditing = ref(false)
const currentSuiteId = ref(null)
const saving = ref(false)
const running = ref(false)

// 表单数据
const createForm = reactive({
  name: '',
  description: ''
})

const formRules = {
  name: [{ required: true, message: '请输入套件名称', trigger: 'blur' }]
}

// 测试用例相关
const availableTestCases = ref([])
const selectedTestCases = ref([])
const testCaseSearchText = ref('')

// 运行配置
const runConfig = reactive({
  engine: 'playwright',
  browser: 'chrome',
  headless: false
})
const currentRunningSuite = ref(null)

// 计算属性 - 过滤后的可用测试用例
const filteredAvailableTestCases = computed(() => {
  if (!testCaseSearchText.value) {
    return availableTestCases.value
  }
  return availableTestCases.value.filter(tc =>
    tc.name.toLowerCase().includes(testCaseSearchText.value.toLowerCase()) ||
    (tc.description && tc.description.toLowerCase().includes(testCaseSearchText.value.toLowerCase()))
  )
})

// 加载项目列表
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    projects.value = response.data.results || response.data
  } catch (error) {
    console.error('获取项目列表失败:', error)
    ElMessage.error('获取项目列表失败')
  }
}

// 加载测试套件列表
const loadSuites = async () => {
  if (!projectId.value) {
    suites.value = []
    total.value = 0
    return
  }

  loading.value = true
  try {
    const response = await getTestSuites({
      project: projectId.value,
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchText.value
    })

    if (response.data.results) {
      suites.value = response.data.results
      total.value = response.data.count || 0
    } else {
      suites.value = response.data
      total.value = response.data.length
    }
  } catch (error) {
    console.error('获取测试套件列表失败:', error)
    ElMessage.error('获取测试套件列表失败')
  } finally {
    loading.value = false
  }
}

// 加载可用测试用例
const loadAvailableTestCases = async () => {
  if (!projectId.value) return

  try {
    const response = await getTestCases({
      project: projectId.value,
      page_size: 1000  // 加载所有用例
    })
    availableTestCases.value = response.data.results || response.data
  } catch (error) {
    console.error('获取测试用例列表失败:', error)
    ElMessage.error('获取测试用例列表失败')
  }
}

// 项目切换
const onProjectChange = async () => {
  pagination.currentPage = 1
  await loadSuites()
}

// 搜索处理
const handleSearch = async () => {
  pagination.currentPage = 1
  await loadSuites()
}

// 分页处理
const handleSizeChange = async () => {
  pagination.currentPage = 1
  await loadSuites()
}

const handleCurrentChange = async () => {
  await loadSuites()
}

// 新增套件
const handleCreate = async () => {
  if (!createForm.name) {
    ElMessage.warning('请输入套件名称')
    return
  }

  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  saving.value = true
  try {
    const suiteData = {
      project: projectId.value,
      name: createForm.name,
      description: createForm.description
    }

    let suiteId
    if (isEditing.value) {
      // 更新套件
      await updateTestSuite(currentSuiteId.value, suiteData)
      suiteId = currentSuiteId.value
      ElMessage.success('套件更新成功')
    } else {
      // 创建套件
      const response = await createTestSuite(suiteData)
      suiteId = response.data.id
      ElMessage.success('套件创建成功')
    }

    // 保存测试用例关联
    if (selectedTestCases.value.length > 0) {
      // 清除旧的关联（如果是编辑模式）
      if (isEditing.value) {
        const existingTestCases = await getTestSuiteTestCases(suiteId)
        for (const tc of existingTestCases.data) {
          await removeTestCaseFromTestSuite(suiteId, tc.test_case.id)
        }
      }

      // 添加新的关联
      for (let i = 0; i < selectedTestCases.value.length; i++) {
        await addTestCaseToTestSuite(suiteId, {
          test_case_id: selectedTestCases.value[i].id,
          order: i
        })
      }
    }

    showCreateDialog.value = false
    await loadSuites()
    resetForm()
  } catch (error) {
    console.error('保存测试套件失败:', error)
    ElMessage.error('保存测试套件失败')
  } finally {
    saving.value = false
  }
}

// 编辑套件
const editSuite = async (id) => {
  try {
    // 加载套件详情
    const suites_data = suites.value.find(s => s.id === id)
    if (!suites_data) return

    currentSuiteId.value = id
    isEditing.value = true
    createForm.name = suites_data.name
    createForm.description = suites_data.description

    // 加载已选测试用例
    const response = await getTestSuiteTestCases(id)
    selectedTestCases.value = response.data.map(item => item.test_case).sort((a, b) => a.order - b.order)

    // 加载可用测试用例
    await loadAvailableTestCases()

    showCreateDialog.value = true
  } catch (error) {
    console.error('加载套件详情失败:', error)
    ElMessage.error('加载套件详情失败')
  }
}

// 删除套件
const deleteSuite = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该测试套件吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteTestSuite(id)
    ElMessage.success('删除成功')
    await loadSuites()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除测试套件失败:', error)
      ElMessage.error('删除测试套件失败')
    }
  }
}

// 运行套件
const runSuite = (suite) => {
  // 检查是否包含测试用例
  if (!suite.test_case_count || suite.test_case_count === 0) {
    ElMessage.warning('该测试套件未包含任何测试用例，无法执行')
    return
  }

  currentRunningSuite.value = suite
  showRunDialog.value = true
}

// 确认运行套件
const confirmRunSuite = async () => {
  running.value = true
  try {
    const requestData = {
      use_ai: false,
      engine: runConfig.engine,
      browser: runConfig.browser,
      headless: runConfig.headless
    }

    const response = await runTestSuite(currentRunningSuite.value.id, requestData)
    
    ElMessage.success('测试套件开始执行')
    showRunDialog.value = false

    // 立即刷新一次以显示"运行中"状态
    await loadSuites()

    // 开始轮询检查执行状态
    pollSuiteStatus(currentRunningSuite.value.id)
  } catch (error) {
    console.error('执行测试套件失败:', error)
    // 如果后端返回了错误消息，显示具体错误
    const errorMsg = error.response?.data?.error || '执行测试套件失败'
    ElMessage.error(errorMsg)
  } finally {
    running.value = false
  }
}

// 轮询检查套件执行状态
const pollSuiteStatus = (suiteId) => {
  let pollCount = 0
  const maxPolls = 120 // 最多轮询2分钟（每秒一次）

  const pollInterval = setInterval(async () => {
    pollCount++

    try {
      // 重新加载套件列表
      await loadSuites()

      // 查找当前套件的状态
      const currentSuite = suites.value.find(s => s.id === suiteId)

      if (currentSuite && currentSuite.execution_status !== 'running') {
        // 执行完成，停止轮询
        clearInterval(pollInterval)

        // 根据状态显示消息
        if (currentSuite.execution_status === 'passed') {
          ElMessage.success(`测试套件执行完成：全部通过 (${currentSuite.passed_count}/${currentSuite.passed_count + currentSuite.failed_count})`)
        } else if (currentSuite.execution_status === 'failed') {
          ElMessage.warning(`测试套件执行完成：部分失败 (通过: ${currentSuite.passed_count}, 失败: ${currentSuite.failed_count})`)
        }
      }

      // 超过最大轮询次数，停止轮询
      if (pollCount >= maxPolls) {
        clearInterval(pollInterval)
        ElMessage.info('执行时间较长，请稍后刷新查看结果')
      }
    } catch (error) {
      console.error('轮询套件状态失败:', error)
      // 发生错误时停止轮询
      clearInterval(pollInterval)
    }
  }, 3000) // 每3秒轮询一次
}

// 测试用例管理方法
const handleTestCaseRowClick = (row) => {
  // 双击添加测试用例
  addTestCase(row)
}

const getTestCaseRowClassName = ({ row }) => {
  // 如果已选中，添加特殊样式
  return selectedTestCases.value.some(tc => tc.id === row.id) ? 'selected-row' : ''
}

const addTestCase = (testCase) => {
  // 检查是否已存在
  if (selectedTestCases.value.some(tc => tc.id === testCase.id)) {
    ElMessage.warning('该用例已添加')
    return
  }
  selectedTestCases.value.push({ ...testCase })
}

const removeTestCase = (index) => {
  selectedTestCases.value.splice(index, 1)
}

const moveUp = (index) => {
  if (index > 0) {
    const temp = selectedTestCases.value[index]
    selectedTestCases.value[index] = selectedTestCases.value[index - 1]
    selectedTestCases.value[index - 1] = temp
  }
}

const moveDown = (index) => {
  if (index < selectedTestCases.value.length - 1) {
    const temp = selectedTestCases.value[index]
    selectedTestCases.value[index] = selectedTestCases.value[index + 1]
    selectedTestCases.value[index + 1] = temp
  }
}

// 重置表单
const resetForm = () => {
  createForm.name = ''
  createForm.description = ''
  selectedTestCases.value = []
  testCaseSearchText.value = ''
  isEditing.value = false
  currentSuiteId.value = null
}

// 取消创建
const cancelCreate = () => {
  showCreateDialog.value = false
  resetForm()
}

// 新增套件按钮点击
const handleCreateButtonClick = async () => {
  resetForm()
  await loadAvailableTestCases()
  showCreateDialog.value = true
}

// 辅助方法
const formatDate = (row, column, cellValue) => {
  if (!cellValue) return ''
  return new Date(cellValue).toLocaleString()
}

const getExecutionStatusTag = (status) => {
  const statusMap = {
    'not_run': 'info',
    'passed': 'success',
    'failed': 'danger',
    'running': 'warning'
  }
  return statusMap[status] || 'info'
}

const getExecutionStatusText = (status) => {
  const statusMap = {
    'not_run': '未执行',
    'passed': '通过',
    'failed': '失败',
    'running': '执行中'
  }
  return statusMap[status] || '未知'
}

const getPriorityTag = (priority) => {
  const priorityMap = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  }
  return priorityMap[priority] || 'info'
}

const getPriorityText = (priority) => {
  const priorityMap = {
    'high': '高',
    'medium': '中',
    'low': '低'
  }
  return priorityMap[priority] || '未知'
}

const getCaseStatusTag = (status) => {
  const statusMap = {
    'draft': 'info',
    'ready': 'primary',
    'running': 'warning',
    'passed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

const getCaseStatusText = (status) => {
  const statusMap = {
    'draft': '草稿',
    'ready': '就绪',
    'running': '执行中',
    'passed': '通过',
    'failed': '失败'
  }
  return statusMap[status] || '未知'
}

// 监听新增套件按钮
const originalShowCreateDialog = showCreateDialog
onMounted(async () => {
  await loadProjects()
  if (projects.value.length > 0) {
    projectId.value = projects.value[0].id
    await loadSuites()
  }
})

// 监听对话框打开事件
const openCreateDialog = async () => {
  if (!isEditing.value) {
    await loadAvailableTestCases()
  }
}

// 修改新增套件按钮点击事件
const handleNewSuite = async () => {
  resetForm()
  await loadAvailableTestCases()
  showCreateDialog.value = true
}
</script>

<style scoped lang="scss">
.page-container {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 20px;
  border-radius: 4px;
}

.page-title {
  margin: 0;
  font-size: 24px;
}

.card-container {
  background: white;
  padding: 20px;
  border-radius: 4px;
}

.filter-bar {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

// 测试用例选择器样式
.test-case-selector {
  display: flex;
  gap: 20px;
  width: 100%;
}

.selector-panel {
  flex: 1;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.panel-header {
  background: #f5f7fa;
  padding: 12px 15px;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;

  h4 {
    margin: 0;
    font-size: 14px;
    color: #303133;
  }
}

.panel-content {
  padding: 10px;
}


:deep(.selected-row) {
  background-color: #f0f9ff !important;
}

:deep(.el-table__row) {
  cursor: pointer;

  &:hover {
    background-color: #f5f7fa;
  }
}

.mode-description {
  margin-top: 8px;
  
  .description-text {
    font-size: 12px;
    color: #909399;
    line-height: 1.5;
  }
}
</style>
