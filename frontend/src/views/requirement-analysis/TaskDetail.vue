<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">任务详情 - {{ task.title }}</h1>
      <div class="header-actions">
        <button 
          v-if="testCases.length > 0" 
          class="export-btn" 
          @click="exportToExcel"
          :disabled="isExporting">
          <span v-if="isExporting">💾 导出中...</span>
          <span v-else>💾 导出Excel</span>
        </button>
      </div>
    </div>

    <div class="card-container">
      <div class="task-info-bar" style="margin-bottom: 20px; display: flex; gap: 20px; align-items: center;">
        <span class="task-id" style="color: #606266;">任务ID: {{ taskId }}</span>
        <span class="task-status" :class="task.status">{{ getStatusText(task.status) }}</span>
      </div>

      <!-- 需求描述折叠卡片 -->
      <div v-if="task.requirement_text" class="requirement-description-card">
        <el-collapse>
          <el-collapse-item name="requirement">
            <template #title>
              <div class="collapse-title">
                <span class="title-icon">📋</span>
                <span class="title-text">需求描述</span>
                <span class="title-hint">（点击展开查看完整内容）</span>
              </div>
            </template>
            <div class="requirement-content">
              <div class="requirement-text">
                {{ task.requirement_text }}
              </div>
              <div class="requirement-actions">
                <el-button size="small" @click="copyRequirementText">
                  <el-icon><DocumentCopy /></el-icon>
                  复制需求描述
                </el-button>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
  
      <div v-if="isLoading" class="loading-state">
        <p>🔄 正在加载任务详情...</p>
      </div>
  
      <div v-else-if="!task.task_id" class="error-state">
        <h3>任务不存在或已被删除</h3>
        <router-link to="/generated-testcases">返回任务列表</router-link>
      </div>
  
      <div v-else class="task-content">
        <!-- 批量操作区域 -->
        <div class="batch-actions" v-if="testCases.length > 0">
          <div class="selection-info">
            <label class="select-all">
              <input 
                type="checkbox" 
                :checked="isAllSelected" 
                @change="toggleSelectAll">
              全选
            </label>
            <span class="selected-count" v-if="selectedCases.length > 0">
              已选择 {{ selectedCases.length }} 条用例
            </span>
          </div>
          <div class="batch-buttons">
            <button 
              class="batch-adopt-btn" 
              :disabled="selectedCases.length === 0"
              @click="batchAdopt">
              ✅ 一键采纳 ({{ selectedCases.length }})
            </button>
            <button 
              class="batch-discard-btn" 
              :disabled="selectedCases.length === 0"
              @click="batchDiscard">
              ❌ 一键弃用 ({{ selectedCases.length }})
            </button>
          </div>
        </div>
  
        <!-- 测试用例列表 -->
        <div class="testcases-table" v-if="testCases.length > 0">
          <div class="table-header">
            <div class="header-cell checkbox-cell">选择</div>
            <div class="header-cell">测试用例编号</div>
            <div class="header-cell">测试场景</div>
            <div class="header-cell">前置条件</div>
            <div class="header-cell">操作步骤</div>
            <div class="header-cell">预期结果</div>
            <div class="header-cell">优先级</div>
            <div class="header-cell">操作</div>
          </div>
          
          <div class="table-body">
            <div 
              v-for="(testCase, index) in paginatedTestCases" 
              :key="testCase.id || index"
              class="table-row">
              <div class="body-cell checkbox-cell">
                <input 
                  type="checkbox" 
                  :value="testCase"
                  v-model="selectedCases"
                  @change="updateSelectAll">
              </div>
              <div class="body-cell">{{ testCase.caseId || `TC${String(index + 1).padStart(3, '0')}` }}</div>
              <div class="body-cell">{{ testCase.scenario }}</div>
              <div class="body-cell text-limit-2">{{ formatTextForList(testCase.precondition) }}</div>
              <div class="body-cell text-limit-2">{{ formatTextForList(testCase.steps) }}</div>
              <div class="body-cell text-limit-2">{{ formatTextForList(testCase.expected) }}</div>
              <div class="body-cell">
                <span class="priority-tag" :class="testCase.priority?.toLowerCase()">{{ testCase.priority || 'P2' }}</span>
              </div>
              <div class="body-cell">
                <div class="action-buttons">
                  <button class="view-btn" @click="viewCaseDetail(testCase, index)">📖 查看详情</button>
                  <button class="adopt-btn" @click="adoptSingleCase(testCase, index)">✅ 采纳</button>
                  <button class="discard-btn" @click="discardSingleCase(testCase, index)">❌ 弃用</button>
                </div>
              </div>
            </div>
          </div>
        </div>
  
        <div v-else class="empty-state">
          <h3>暂无测试用例数据</h3>
          <p>该任务还没有生成测试用例或用例已被清空</p>
        </div>
  
        <!-- 分页 -->
        <div v-if="testCases.length > 0" class="pagination-section">
          <div class="pagination-info">
            显示 {{ paginationStart }}-{{ paginationEnd }} 条，共 {{ testCases.length }} 条
          </div>
          <div class="pagination-controls">
            <div class="page-size-selector">
              <label>每页显示：</label>
              <select v-model="pageSize" @change="currentPage = 1">
                <option value="10">10 条</option>
                <option value="20">20 条</option>
                <option value="50">50 条</option>
              </select>
            </div>
            <div class="pagination-buttons">
              <button :disabled="currentPage <= 1" @click="currentPage--">上一页</button>
              <span class="current-page">第 {{ currentPage }} 页，共 {{ totalPages }} 页</span>
              <button :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 用例详情弹窗 -->
    <div v-if="showCaseDetail" class="case-detail-modal" @click="closeCaseDetail">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ isEditing ? '编辑测试用例' : '测试用例详情' }}</h3>
          <button class="close-btn" @click="closeCaseDetail">×</button>
        </div>

        <!-- 查看模式 -->
        <div v-if="!isEditing" class="modal-body">
          <div class="detail-item">
            <label>用例编号:</label>
            <span>{{ selectedCase.caseId || `TC${String(selectedCaseIndex + 1).padStart(3, '0')}` }}</span>
          </div>
          <div class="detail-item">
            <label>测试场景:</label>
            <p>{{ selectedCase.scenario }}</p>
          </div>
          <div class="detail-item">
            <label>前置条件:</label>
            <p v-html="selectedCase.precondition || '无'"></p>
          </div>
          <div class="detail-item">
            <label>操作步骤:</label>
            <p class="test-steps" v-html="selectedCase.steps"></p>
          </div>
          <div class="detail-item">
            <label>预期结果:</label>
            <p v-html="selectedCase.expected"></p>
          </div>
          <div class="detail-item">
            <label>优先级:</label>
            <span class="priority-tag" :class="selectedCase.priority?.toLowerCase()">{{ selectedCase.priority || 'P2' }}</span>
          </div>
        </div>

        <!-- 编辑模式 -->
        <div v-else class="modal-body edit-mode">
          <div class="form-item">
            <label>用例编号:</label>
            <span class="readonly-field">{{ editForm.caseId || `TC${String(selectedCaseIndex + 1).padStart(3, '0')}` }}</span>
          </div>
          <div class="form-item">
            <label>测试场景:</label>
            <el-input v-model="editForm.scenario" type="textarea" :rows="2" placeholder="请输入测试场景" />
          </div>
          <div class="form-item">
            <label>前置条件:</label>
            <el-input v-model="editForm.precondition" type="textarea" :rows="3" placeholder="请输入前置条件" />
          </div>
          <div class="form-item">
            <label>操作步骤:</label>
            <el-input v-model="editForm.steps" type="textarea" :rows="6" placeholder="请输入操作步骤" />
          </div>
          <div class="form-item">
            <label>预期结果:</label>
            <el-input v-model="editForm.expected" type="textarea" :rows="4" placeholder="请输入预期结果" />
          </div>
          <div class="form-item">
            <label>优先级:</label>
            <el-select v-model="editForm.priority" placeholder="请选择优先级">
              <el-option label="P0" value="P0"></el-option>
              <el-option label="P1" value="P1"></el-option>
              <el-option label="P2" value="P2"></el-option>
              <el-option label="P3" value="P3"></el-option>
            </el-select>
          </div>
        </div>

        <!-- 底部操作栏 -->
        <div class="modal-footer">
          <template v-if="!isEditing">
            <button class="action-btn edit-btn" @click="startEdit">
              <span>✏️ 编辑</span>
            </button>
            <button class="action-btn close-btn-footer" @click="closeCaseDetail">关闭</button>
          </template>
          <template v-else>
            <button class="action-btn save-btn" @click="saveEdit" :disabled="isSaving">
              <span v-if="isSaving">💾 保存中...</span>
              <span v-else>💾 保存</span>
            </button>
            <button class="action-btn cancel-btn" @click="cancelEdit" :disabled="isSaving">取消</button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'

export default {
  name: 'TaskDetail',
  data() {
    return {
      taskId: '',
      task: {},
      testCases: [],
      selectedCases: [],
      isLoading: true,
      showCaseDetail: false,
      selectedCase: {},
      selectedCaseIndex: 0,
      currentPage: 1,
      pageSize: 10,
      isExporting: false,
      // 编辑相关状态
      isEditing: false,
      isSaving: false,
      editForm: {
        caseId: '',
        scenario: '',
        precondition: '',
        steps: '',
        expected: '',
        priority: 'P2'
      }
    }
  },

  computed: {
    isAllSelected() {
      return this.testCases.length > 0 && this.selectedCases.length === this.testCases.length
    },

    totalPages() {
      return Math.ceil(this.testCases.length / this.pageSize)
    },

    paginatedTestCases() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      return this.testCases.slice(start, end)
    },

    paginationStart() {
      return (this.currentPage - 1) * this.pageSize + 1
    },

    paginationEnd() {
      return Math.min(this.currentPage * this.pageSize, this.testCases.length)
    }
  },

  mounted() {
    this.taskId = this.$route.params.taskId
    this.loadTaskDetail()
  },

  methods: {
    // 复制需求描述文本
    async copyRequirementText() {
      try {
        await navigator.clipboard.writeText(this.task.requirement_text)
        ElMessage.success('需求描述已复制到剪贴板')
      } catch (error) {
        // 如果 navigator.clipboard 不可用，使用备用方法
        const textArea = document.createElement('textarea')
        textArea.value = this.task.requirement_text
        textArea.style.position = 'fixed'
        textArea.style.opacity = '0'
        document.body.appendChild(textArea)
        textArea.select()
        try {
          document.execCommand('copy')
          ElMessage.success('需求描述已复制到剪贴板')
        } catch (err) {
          ElMessage.error('复制失败，请手动复制')
        }
        document.body.removeChild(textArea)
      }
    },

    async loadTaskDetail() {
      try {
        // 获取任务基本信息
        const taskResponse = await api.get(`/requirement-analysis/api/testcase-generation/${this.taskId}/`)
        this.task = taskResponse.data

        // 解析最终测试用例
        if (this.task.final_test_cases) {
          this.testCases = this.parseTestCases(this.task.final_test_cases)
        }
      } catch (error) {
        console.error('加载任务详情失败:', error)
        ElMessage.error('加载任务详情失败')
      } finally {
        this.isLoading = false
      }
    },

    parseTestCases(content) {
      // 复用RequirementAnalysisView中的解析逻辑
      if (!content) return []
      
      const lines = content.split('\n').filter(line => line.trim())
      const testCases = []
      
      // 尝试解析表格格式
      let isTableFormat = false
      const tableData = []
      
      for (let line of lines) {
        const trimmedLine = line.trim()
        if (trimmedLine.includes('|') && !trimmedLine.includes('--------')) {
          const cells = trimmedLine.split('|').map(cell => cell.trim()).filter(cell => cell)
          if (cells.length > 1) {
            tableData.push(cells)
            isTableFormat = true
          }
        }
      }
      
      if (isTableFormat && tableData.length > 1) {
        // 表格格式解析
        const headers = tableData[0]
        for (let i = 1; i < tableData.length; i++) {
          const row = tableData[i]
          const testCase = {}
          
          headers.forEach((header, index) => {
            const value = row[index] || ''
            if (header.includes('编号') || header.includes('ID') || header.includes('用例ID')) {
              testCase.caseId = value
            } else if (header.includes('场景') || header.includes('标题') || header.includes('测试目标')) {
              testCase.scenario = value
            } else if (header.includes('前置')) {
              testCase.precondition = value
            } else if (header.includes('步骤') || header.includes('操作步骤')) {
              testCase.steps = value
            } else if (header.includes('预期') || header.includes('结果')) {
              testCase.expected = value
            } else if (header.includes('优先级')) {
              testCase.priority = value
            }
          })
          
          if (testCase.scenario || testCase.caseId) {
            // 如果没有steps字段，使用scenario作为steps的默认值
            if (!testCase.steps && testCase.scenario) {
              testCase.steps = '参考测试目标执行相应操作'
            }
            testCases.push(testCase)
          }
        }
      } else {
        // 结构化文本格式解析
        let currentTestCase = {}
        let caseNumber = 1
        
        for (const line of lines) {
          if (line.includes('测试用例') || line.includes('Test Case') || 
              line.match(/^(\d+\.|\*|\-|\d+、)/)) {
            
            if (Object.keys(currentTestCase).length > 0) {
              testCases.push(currentTestCase)
              caseNumber++
            }
            
            currentTestCase = {
              caseId: `TC${String(caseNumber).padStart(3, '0')}`,
              scenario: line.replace(/^(\d+\.|\*|\-|\d+、)\s*/, '').replace(/测试用例\d*[:：]?\s*/, ''),
              precondition: '',
              steps: '',
              expected: '',
              priority: '中'
            }
          } else if (line.includes('前置条件') || line.includes('前提')) {
            currentTestCase.precondition = line.replace(/.*?[:：]\s*/, '')
          } else if (line.includes('测试步骤') || line.includes('操作步骤') || line.includes('步骤')) {
            currentTestCase.steps = line.replace(/.*?[:：]\s*/, '')
          } else if (line.includes('预期结果') || line.includes('Expected')) {
            currentTestCase.expected = line.replace(/.*?[:：]\s*/, '')
          } else if (line.includes('优先级')) {
            currentTestCase.priority = line.replace(/.*?[:：]\s*/, '')
          }
        }
        
        if (Object.keys(currentTestCase).length > 0) {
          testCases.push(currentTestCase)
        }
      }
      
      return testCases
    },

    getStatusText(status) {
      const statusMap = {
        'pending': '需求分析中',
        'generating': '用例编写中',
        'reviewing': '用例评审中',
        'completed': '已完成',
        'failed': '失败'
      }
      return statusMap[status] || status
    },

    // 格式化列表中的文本，将<br>转换为换行
    formatTextForList(text) {
      if (!text) return ''
      // 将<br>、<br/>、<br />等标签替换为换行符
      return text.replace(/<br\s*\/?>/gi, '\n')
    },

    toggleSelectAll() {
      if (this.isAllSelected) {
        this.selectedCases = []
      } else {
        this.selectedCases = [...this.testCases]
      }
    },

    updateSelectAll() {
      // 这个方法会在单个checkbox变化时触发，用于更新全选状态
      // Vue的v-model会自动处理selectedCases数组的更新
    },

    async batchAdopt() {
      if (this.selectedCases.length === 0) {
        ElMessage.warning('请先选择要采纳的测试用例')
        return
      }

      if (!confirm(`确定要采纳选中的 ${this.selectedCases.length} 条测试用例吗？`)) {
        return
      }

      try {
        const casesData = this.selectedCases.map((testCase, index) => ({
          title: testCase.scenario || `测试用例${index + 1}`,
          description: testCase.scenario || '',
          preconditions: testCase.precondition || '',
          steps: testCase.steps || '',
          expected_result: testCase.expected || '',
          priority: this.mapPriority(testCase.priority),
          test_type: 'functional',
          status: 'draft'
        }))

        // await api.post(`/requirement-analysis/api/testcase-generation/${this.taskId}/batch-adopt-selected/`, {
        await api.post(`/requirement-analysis/api/testcase-generation/${this.taskId}/batch_adopt_selected/`, {
          test_cases: casesData
        })

        ElMessage.success(`成功采纳 ${this.selectedCases.length} 条测试用例！`)
        this.selectedCases = []
        
        // 不再移除已采纳的用例，保留在列表中供多次采纳
        // this.testCases = this.testCases.filter(tc => !this.selectedCases.includes(tc))
        
      } catch (error) {
        console.error('批量采纳失败:', error)
        ElMessage.error('批量采纳失败: ' + (error.response?.data?.message || error.message))
      }
    },

    async batchDiscard() {
      if (this.selectedCases.length === 0) {
        ElMessage.warning('请先选择要弃用的测试用例')
        return
      }

      if (!confirm(`确定要弃用选中的 ${this.selectedCases.length} 条测试用例吗？此操作不可恢复。`)) {
        return
      }

      try {
        // 获取选中用例的全局索引（不是分页索引）
        const caseIndices = this.selectedCases.map(selectedCase => {
          // 在完整列表中查找索引
          const globalIndex = this.testCases.findIndex(tc => 
            tc.scenario === selectedCase.scenario && 
            tc.steps === selectedCase.steps && 
            tc.expected === selectedCase.expected
          )
          return globalIndex
        }).filter(index => index !== -1) // 过滤掉未找到的(-1)

        const response = await api.post(`/requirement-analysis/api/testcase-generation/${this.taskId}/discard_selected_cases/`, {
          case_indices: caseIndices
        })

        if (response.data.task_deleted) {
          ElMessage.success('所有测试用例已弃用，任务已删除')
          // 返回到AI生成用例记录列表
          this.$router.push('/generated-testcases')
        } else {
          ElMessage.success(`成功弃用 ${response.data.discarded_count} 条测试用例`)
          
          // 重新解析更新后的测试用例
          if (response.data.updated_test_cases) {
            this.testCases = this.parseTestCases(response.data.updated_test_cases)
            this.selectedCases = []
            this.currentPage = 1 // 重置到第一页
          }
        }
        
      } catch (error) {
        console.error('批量弃用失败:', error)
        ElMessage.error('批量弃用失败: ' + (error.response?.data?.error || error.message))
      }
    },

    viewCaseDetail(testCase, index) {
      this.selectedCase = testCase
      this.selectedCaseIndex = index
      this.showCaseDetail = true
    },

    closeCaseDetail() {
      this.showCaseDetail = false
      this.selectedCase = {}
      this.isEditing = false
      this.editForm = {
        caseId: '',
        scenario: '',
        precondition: '',
        steps: '',
        expected: '',
        priority: 'P2'
      }
    },

    // 开始编辑
    startEdit() {
      this.isEditing = true

      this.editForm = {
        caseId: this.selectedCase.caseId || '',
        scenario: this.selectedCase.scenario || '',
        // 将<br>转换为换行符以便编辑
        precondition: this.convertBrToNewline(this.selectedCase.precondition || ''),
        steps: this.convertBrToNewline(this.selectedCase.steps || ''),
        expected: this.convertBrToNewline(this.selectedCase.expected || ''),
        // 直接使用原始优先级值，不转换
        priority: this.selectedCase.priority || 'P2'
      }
    },

    // 取消编辑
    cancelEdit() {
      this.isEditing = false
      this.editForm = {
        caseId: '',
        scenario: '',
        precondition: '',
        steps: '',
        expected: '',
        priority: 'P2'
      }
    },

    // 保存编辑
    async saveEdit() {
      // 简单验证
      if (!this.editForm.scenario?.trim()) {
        ElMessage.warning('请输入测试场景')
        return
      }

      this.isSaving = true

      try {
        // 将换行符转换回<br>
        const updatedCase = {
          ...this.selectedCase,
          scenario: this.editForm.scenario,
          precondition: this.convertNewlineToBr(this.editForm.precondition),
          steps: this.convertNewlineToBr(this.editForm.steps),
          expected: this.convertNewlineToBr(this.editForm.expected),
          priority: this.editForm.priority
        }

        // 更新本地数组中的数据
        const index = this.testCases.findIndex(tc => tc === this.selectedCase)
        if (index !== -1) {
          this.testCases[index] = updatedCase
          this.selectedCase = updatedCase
        }

        // 重新生成表格格式的测试用例字符串
        const updatedTestCases = this.generateTestCasesString()

        // 调用后端API保存（使用自定义action接口）
        await api.post(`/requirement-analysis/api/testcase-generation/${this.taskId}/update_test_cases/`, {
          final_test_cases: updatedTestCases
        })

        // 更新内存中的task数据
        this.task.final_test_cases = updatedTestCases

        ElMessage.success('测试用例更新成功')
        this.isEditing = false
      } catch (error) {
        console.error('更新失败:', error)
        ElMessage.error('更新失败: ' + (error.response?.data?.error || error.message))
      } finally {
        this.isSaving = false
      }
    },

    // 将testCases数组重新生成为表格格式的字符串
    generateTestCasesString() {
      if (this.testCases.length === 0) return ''

      // 表头
      const headers = ['测试用例编号', '测试场景', '前置条件', '操作步骤', '预期结果', '优先级']
      let result = headers.join(' | ') + '\n'
      result += '|'.repeat(headers.length) + '\n'

      // 数据行
      this.testCases.forEach((testCase, index) => {
        const row = [
          testCase.caseId || `TC${String(index + 1).padStart(3, '0')}`,
          testCase.scenario || '',
          testCase.precondition || '',
          testCase.steps || '',
          testCase.expected || '',
          testCase.priority || 'P2'
        ]
        result += row.join(' | ') + '\n'
      })

      return result
    },

    // 将HTML的<br>标签转换为换行符
    convertBrToNewline(text) {
      if (!text) return ''
      return text.replace(/<br\s*\/?>/gi, '\n')
    },

    // 将换行符转换为HTML的<br>标签
    convertNewlineToBr(text) {
      if (!text) return ''
      return text.replace(/\n/g, '<br>')
    },

    async adoptSingleCase(testCase, index) {
      if (!confirm(`确定要采纳测试用例"${testCase.scenario}"吗？`)) {
        return
      }

      try {
        const caseData = {
          title: testCase.scenario || `测试用例${index + 1}`,
          description: testCase.scenario || '',
          preconditions: testCase.precondition || '',
          steps: testCase.steps || '',
          expected_result: testCase.expected || '',
          priority: this.mapPriority(testCase.priority),
          test_type: 'functional',
          status: 'draft'
        }

        await api.post('/testcases/', caseData)
        ElMessage.success('测试用例采纳成功！')
        
        // 不再移除已采纳的用例，保留在列表中供多次采纳
        // this.testCases.splice(this.testCases.indexOf(testCase), 1)
        
      } catch (error) {
        console.error('采纳用例失败:', error)
        ElMessage.error('采纳用例失败: ' + (error.response?.data?.message || error.message))
      }
    },

    discardSingleCase(testCase, index) {
      if (!confirm(`确定要弃用测试用例"${testCase.scenario}"吗？此操作不可恢复。`)) {
        return
      }

      try {
        // 计算全局索引（当前页面起始位置 + 当前索引）
        const globalIndex = (this.currentPage - 1) * this.pageSize + index

        // 调用后端API弃用单个测试用例
        api.post(`/requirement-analysis/api/testcase-generation/${this.taskId}/discard_single_case/`, {
          case_index: globalIndex
        }).then(response => {
          if (response.data.task_deleted) {
            ElMessage.success('所有测试用例已弃用，任务已删除')
            // 返回到AI生成用例记录列表
            this.$router.push('/generated-testcases')
          } else {
            ElMessage.success('测试用例已弃用')
            
            // 重新解析更新后的测试用例
            if (response.data.updated_test_cases) {
              this.testCases = this.parseTestCases(response.data.updated_test_cases)
              
              // 如果当前页没有数据了，回到上一页
              if (this.currentPage > 1 && this.paginatedTestCases.length === 0) {
                this.currentPage--
              }
            }
          }
        }).catch(error => {
          console.error('弃用用例失败:', error)
          ElMessage.error('弃用用例失败: ' + (error.response?.data?.error || error.message))
        })
        
      } catch (error) {
        console.error('弃用用例失败:', error)
        ElMessage.error('弃用用例失败')
      }
    },

    mapPriority(priority) {
      const priorityMap = {
        '最高': 'critical',
        '高': 'high',
        '中': 'medium',
        '低': 'low',
        'P0': 'critical',
        'P1': 'high',
        'P2': 'medium',
        'P3': 'low'
      }
      return priorityMap[priority] || 'medium'
    },

    // 将英文优先级转换为中文显示
    priorityToChinese(priority) {
      const priorityMap = {
        'critical': '紧急',
        'high': '高',
        'medium': '中',
        'low': '低'
      }
      return priorityMap[priority] || '中'
    },

    // 导出到Excel
    exportToExcel() {
      if (this.testCases.length === 0) {
        ElMessage.warning('没有测试用例可以导出')
        return
      }

      this.isExporting = true

      try {
        // 创建工作簿
        const workbook = XLSX.utils.book_new()

        // 准备数据
        const worksheetData = []
        
        // 添加表头
        worksheetData.push(['测试用例编号', '测试场景', '前置条件', '操作步骤', '预期结果', '优先级'])

        // 添加数据行
        this.testCases.forEach((testCase, index) => {
          worksheetData.push([
            testCase.caseId || `TC${String(index + 1).padStart(3, '0')}`,
            testCase.scenario || '',
            this.formatTextForList(testCase.precondition || ''),
            this.formatTextForList(testCase.steps || ''),
            this.formatTextForList(testCase.expected || ''),
            testCase.priority || '中'
          ])
        })

        // 创建工作表
        const worksheet = XLSX.utils.aoa_to_sheet(worksheetData)

        // 设置列宽
        const colWidths = [
          { wch: 15 }, // 测试用例编号
          { wch: 30 }, // 测试场景
          { wch: 25 }, // 前置条件
          { wch: 50 }, // 操作步骤（增加宽度）
          { wch: 40 }, // 预期结果（增加宽度）
          { wch: 10 }  // 优先级
        ]
        worksheet['!cols'] = colWidths

        // 为所有单元格添加自动换行样式
        const range = XLSX.utils.decode_range(worksheet['!ref'])
        for (let row = range.s.r; row <= range.e.r; row++) {
          for (let col = range.s.c; col <= range.e.c; col++) {
            const cellAddress = XLSX.utils.encode_cell({ r: row, c: col })
            if (!worksheet[cellAddress]) continue
            worksheet[cellAddress].s = {
              alignment: {
                wrapText: true,
                vertical: 'top'
              }
            }
          }
        }

        // 将工作表添加到工作簿
        XLSX.utils.book_append_sheet(workbook, worksheet, '测试用例')

        // 生成文件名
        const fileName = `测试用例_${this.taskId}_${new Date().toISOString().slice(0, 10)}.xlsx`

        // 导出文件
        XLSX.writeFile(workbook, fileName)

        ElMessage.success('测试用例导出成功')
      } catch (error) {
        console.error('导出Excel失败:', error)
        ElMessage.error('导出Excel失败: ' + (error.message || '未知错误'))
      } finally {
        this.isExporting = false
      }
    }
  }
}
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
/* 需求描述折叠卡片 */
.requirement-description-card {
  margin-bottom: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.collapse-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
}

.title-icon {
  font-size: 18px;
}

.title-text {
  color: #303133;
  font-weight: 600;
}

.title-hint {
  font-size: 13px;
  color: #909399;
  font-weight: normal;
}

.requirement-content {
  padding: 16px 0;
}

.requirement-text {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 16px;
  line-height: 1.8;
  color: #606266;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  border-left: 4px solid #409eff;
}

.requirement-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

/* 自定义折叠面板样式 */
.requirement-description-card :deep(.el-collapse) {
  border: none;
}

.requirement-description-card :deep(.el-collapse-item__header) {
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
  padding: 16px 20px;
  font-size: 15px;
}

.requirement-description-card :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.requirement-description-card :deep(.el-collapse-item__content) {
  padding: 0 20px 16px;
}

.task-id {
  color: #666;
  font-family: monospace;
}

.task-status {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: bold;
}

.task-status.completed {
  background: #e8f5e8;
  color: #388e3c;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.export-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s ease;
  white-space: nowrap;
}

.export-btn:hover:not(:disabled) {
  background: #229954;
}

.export-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.batch-actions {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selection-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.selected-count {
  color: #3498db;
  font-weight: bold;
}

.batch-buttons {
  display: flex;
  gap: 10px;
}

.batch-adopt-btn, .batch-discard-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.batch-adopt-btn {
  background: #27ae60;
  color: white;
}

.batch-adopt-btn:hover:not(:disabled) {
  background: #229954;
}

.batch-discard-btn {
  background: #e74c3c;
  color: white;
}

.batch-discard-btn:hover:not(:disabled) {
  background: #c0392b;
}

.batch-adopt-btn:disabled, .batch-discard-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.testcases-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.table-header {
  display: grid;
  grid-template-columns: 60px 120px 1fr 1fr 1fr 1fr 80px 150px;
  background: #f8f9fa;
  font-weight: bold;
  color: #2c3e50;
}

.table-body .table-row {
  display: grid;
  grid-template-columns: 60px 120px 1fr 1fr 1fr 1fr 80px 150px;
  border-bottom: 1px solid #eee;
  transition: background 0.2s ease;
}

.table-row:hover {
  background: #f8f9fa;
}

.header-cell, .body-cell {
  padding: 12px 8px;
  display: flex;
  align-items: flex-start; /* 改为顶部对齐，避免内容被裁剪 */
  border-right: 1px solid #eee;
  word-break: break-word;
}

/* 操作步骤和预期结果列的特殊样式 */
.body-cell.text-limit-2 {
  align-items: flex-start;
  overflow: hidden;
}

.checkbox-cell {
  justify-content: center;
}

.header-cell:last-child, .body-cell:last-child {
  border-right: none;
}

.priority-tag {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
}

.text-limit-2 {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: pre-wrap;
  line-height: 1.6;
  max-height: 3.6em; /* 2行 × 1.6行高 + 0.4em余量 */
  min-height: 3.2em; /* 确保有足够空间显示2行 */
  word-break: break-word;
}

.priority-tag.low {
  background: #e8f5e8;
  color: #388e3c;
}

.priority-tag.p3 {
  background: #e8f5e8;
  color: #388e3c;
}

.priority-tag.medium {
  background: #e3f2fd;
  color: #1976d2;
}

.priority-tag.p2 {
  background: #e3f2fd;
  color: #1976d2;
}

.priority-tag.high {
  background: #fff3e0;
  color: #f57c00;
}

.priority-tag.p1 {
  background: #fff3e0;
  color: #f57c00;
}

.priority-tag.critical {
  background: #ffebee;
  color: #d32f2f;
}

.priority-tag.p0 {
  background: #ffebee;
  color: #d32f2f;
}

.action-buttons {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.view-btn, .adopt-btn, .discard-btn {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s ease;
}

.view-btn {
  background: #3498db;
  color: white;
}

.view-btn:hover {
  background: #2980b9;
}

.adopt-btn {
  background: #27ae60;
  color: white;
}

.adopt-btn:hover {
  background: #229954;
}

.discard-btn {
  background: #e74c3c;
  color: white;
}

.discard-btn:hover {
  background: #c0392b;
}

.pagination-section {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 20px;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 15px;
}

.pagination-buttons button {
  padding: 6px 12px;
  border: 1px solid #ddd;
  background: white;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.pagination-buttons button:hover:not(:disabled) {
  background: #f0f0f0;
}

.pagination-buttons button:disabled {
  color: #ccc;
  cursor: not-allowed;
}

.case-detail-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 800px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 30px;
}

.detail-item {
  margin-bottom: 20px;
}

.detail-item label {
  font-weight: bold;
  color: #2c3e50;
  display: block;
  margin-bottom: 8px;
}

.detail-item span, .detail-item p {
  color: #666;
  line-height: 1.6;
}

.test-steps {
  white-space: pre-line;
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #3498db;
}

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.error-state h3, .empty-state h3 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.error-state a {
  color: #3498db;
  text-decoration: none;
}

.error-state a:hover {
  text-decoration: underline;
}

/* 编辑模式样式 */
.edit-mode {
  .form-item {
    margin-bottom: 20px;
  }

  .form-item label {
    font-weight: bold;
    color: #2c3e50;
    display: block;
    margin-bottom: 8px;
  }

  .readonly-field {
    color: #666;
    padding: 8px 12px;
    background: #f5f5f5;
    border-radius: 4px;
    display: inline-block;
  }
}

/* 底部操作栏 */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 30px;
  border-top: 1px solid #eee;
  background: #f9f9f9;
  border-radius: 0 0 12px 12px;
}

.action-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.edit-btn {
  background: #409eff;
  color: white;
}

.edit-btn:hover {
  background: #66b1ff;
}

.save-btn {
  background: #67c23a;
  color: white;
}

.save-btn:hover:not(:disabled) {
  background: #85ce61;
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-btn {
  background: #909399;
  color: white;
}

.cancel-btn:hover:not(:disabled) {
  background: #a6a9ad;
}

.close-btn-footer {
  background: #e4e7ed;
  color: #606266;
}

.close-btn-footer:hover {
  background: #ecf5ff;
}
</style>