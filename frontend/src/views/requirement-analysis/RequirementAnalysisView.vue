<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">智能用例生成</h1>
      </div>
    </div>

    <div class="card-container main-content">
      <!-- 手动输入需求描述区域 -->
      <div class="manual-input-section" v-if="!isGenerating && !showResults">
        <div class="manual-input-card">
          <h2>✍️ 手动输入需求描述</h2>
          <div class="input-form">
            <div class="form-group">
              <label>需求标题 <span class="required">*</span></label>
              <input 
                v-model="manualInput.title" 
                type="text" 
                class="form-input"
                placeholder="请输入需求标题，如：用户登录功能需求">
            </div>
            
            <div class="form-group">
              <label>需求描述 <span class="required">*</span></label>
              <textarea 
                v-model="manualInput.description" 
                class="form-textarea"
                rows="8"
                placeholder="请详细描述您的需求，包括功能描述、使用场景、业务流程等。例如：&#10;&#10;1. 用户可以通过用户名和密码登录系统&#10;2. 系统需要验证用户身份&#10;3. 登录成功后跳转到主页面&#10;4. 支持记住登录状态&#10;5. 登录失败要给出明确提示..."></textarea>
              <div class="char-count">{{ manualInput.description.length }}/2000</div>
            </div>
            
            <div class="form-row" style="display: flex; gap: 20px;">
              <div class="form-group" style="flex: 1;">
                <label>关联项目（可选）</label>
                <select v-model="manualInput.selectedProject" class="form-select">
                  <option value="">请选择项目</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.name }}
                  </option>
                </select>
              </div>

              <div class="form-group" style="flex: 1;">
                <label>提示词模板（可选）</label>
                <select v-model="manualInput.selectedPromptConfig" class="form-select">
                  <option value="">默认提示词</option>
                  <option v-for="config in promptConfigs" :key="config.id" :value="config.id">
                    {{ config.name }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>关联知识库文档（增强生成准确性，可选）</label>
              <select v-model="manualInput.selectedKnowledgeDocs" multiple class="form-select" style="height: 100px;">
                <option v-for="doc in knowledgeBaseDocs" :key="doc.id" :value="doc.id">
                  {{ doc.title }}
                </option>
              </select>
              <p class="text-gray-500" style="font-size: 0.85rem; color: #666; margin-top: 5px;">
                按住 Ctrl (Windows) 或 Cmd (Mac) 可多选。选中的文档将作为生成用例的参考上下文。
              </p>
            </div>

            <button 
              class="generate-manual-btn" 
              @click="generateFromManualInput"
              :disabled="!canGenerateManual || isGenerating">
              <span v-if="isGenerating">🔄 生成中...</span>
              <span v-else>🚀 生成测试用例</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 分隔线 -->
      <div class="divider" v-if="!isGenerating && !showResults">
        <span>或</span>
      </div>

      <!-- 文档上传区域 -->
      <div class="upload-section" v-if="!isGenerating && !showResults">
        <div class="upload-card">
          <h2>📄 上传需求文档</h2>
          <div class="upload-area" 
               @dragover.prevent 
               @drop="handleDrop"
               :class="{ 'drag-over': isDragOver }"
               @dragenter="isDragOver = true"
               @dragleave="isDragOver = false">
            <div v-if="!selectedFile" class="upload-placeholder">
              <i class="upload-icon">📁</i>
              <p>拖拽文件到此处或点击选择文件</p>
              <p class="upload-hint">支持 PDF、Word、TXT、Markdown 以及图片格式（JPG、PNG、GIF、SVG）</p>
              <input 
                type="file" 
                ref="fileInput" 
                @change="handleFileSelect"
                accept=".pdf,.doc,.docx,.txt,.md,.markdown,.jpg,.jpeg,.png,.gif,.bmp,.svg"
                style="display: none;">
              <button class="select-file-btn" @click="$refs.fileInput.click()">
                选择文件
              </button>
            </div>
            
            <div v-else class="file-selected">
              <div class="file-info">
                <i class="file-icon">📄</i>
                <div class="file-details">
                  <p class="file-name">{{ selectedFile.name }}</p>
                  <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
                </div>
                <button class="remove-file" @click="removeFile">❌</button>
              </div>
            </div>
          </div>

          <div v-if="selectedFile" class="document-info">
            <div class="form-group">
              <label>文档标题</label>
              <input 
                v-model="documentTitle" 
                type="text" 
                class="form-input"
                placeholder="请输入文档标题">
            </div>
            
            <div class="form-row" style="display: flex; gap: 20px;">
              <div class="form-group" style="flex: 1;">
                <label>关联项目（可选）</label>
                <select v-model="selectedProject" class="form-select">
                  <option value="">请选择项目</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.name }}
                  </option>
                </select>
              </div>

              <div class="form-group" style="flex: 1;">
                <label>提示词模板（可选）</label>
                <select v-model="selectedPromptConfig" class="form-select">
                  <option value="">默认提示词</option>
                  <option v-for="config in promptConfigs" :key="config.id" :value="config.id">
                    {{ config.name }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>关联知识库文档（增强生成准确性，可选）</label>
              <select v-model="selectedKnowledgeDocs" multiple class="form-select" style="height: 100px;">
                <option v-for="doc in knowledgeBaseDocs" :key="doc.id" :value="doc.id">
                  {{ doc.title }}
                </option>
              </select>
              <p class="text-gray-500" style="font-size: 0.85rem; color: #666; margin-top: 5px;">
                按住 Ctrl (Windows) 或 Cmd (Mac) 可多选。
              </p>
            </div>

            <button 
              class="generate-btn" 
              @click="generateFromDocument"
              :disabled="!documentTitle || isGenerating">
              <span v-if="isGenerating">🔄 生成中...</span>
              <span v-else>🚀 生成测试用例</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 生成进度 -->
      <div v-if="isGenerating" class="generation-progress">
        <div class="progress-card">
          <h3>🤖 AI正在为您生成测试用例</h3>
          <div class="progress-info">
            <div class="progress-item">
              <span class="label">任务ID:</span>
              <span class="value">{{ currentTaskId || '准备中...' }}</span>
            </div>
            <div class="progress-item">
              <span class="label">当前状态:</span>
              <span class="value">{{ progressText }}</span>
            </div>
          </div>
          <div class="progress-steps">
            <div class="step" :class="{ active: currentStep >= 1 }">
              <span class="step-number">1</span>
              <span class="step-text">需求分析</span>
            </div>
            <div class="step" :class="{ active: currentStep >= 2 }">
              <span class="step-number">2</span>
              <span class="step-text">用例编写</span>
            </div>
            <div class="step" :class="{ active: currentStep >= 3 }">
              <span class="step-number">3</span>
              <span class="step-text">用例评审</span>
            </div>
            <div class="step" :class="{ active: currentStep >= 4 }">
              <span class="step-number">4</span>
              <span class="step-text">完成</span>
            </div>
          </div>
          <button class="cancel-generation-btn" @click="cancelGeneration">
            取消生成
          </button>
        </div>
      </div>

      <!-- 生成结果 -->
      <div v-if="showResults && generationResult" class="generation-result">
        <div class="result-header">
          <h2>✅ 测试用例生成完成</h2>
          <div class="result-summary">
            <span class="summary-item">
              📊 任务ID: {{ generationResult.task_id }}
            </span>
            <span class="summary-item">
              ⏱️ 生成时间: {{ formatDateTime(generationResult.completed_at) }}
            </span>
          </div>
          <button class="new-generation-btn" @click="resetGeneration">
            📝 生成新的测试用例
          </button>
        </div>

        <!-- AI编写的测试用例 -->
        <div class="generated-testcases-section">
          <h3>📋 AI编写的测试用例</h3>
          <div class="testcase-content">
            <div v-html="generationResult.generated_test_cases"></div>
          </div>
        </div>

        <!-- AI评审意见 -->
        <div v-if="generationResult.review_feedback" class="review-feedback-section">
          <h3>🔍 AI评审意见</h3>
          <div class="review-content">
            <pre>{{ generationResult.review_feedback }}</pre>
          </div>
        </div>

        <!-- 最终测试用例 -->
        <div v-if="generationResult.final_test_cases" class="final-testcases-section">
          <h3>🎯 最终测试用例</h3>
          <div class="testcase-content">
            <div v-html="generationResult.final_test_cases"></div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div v-if="generationResult.final_test_cases" class="actions-section">
          <button class="download-btn" @click="downloadTestCases">
            <span>📥 下载测试用例(.xlsx)</span>
          </button>
          <button class="save-btn" @click="saveToTestCaseRecords">
            <span>💾 保存到用例记录</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'
import * as XLSX from 'xlsx'

export default {
  name: 'RequirementAnalysisView',
  data() {
    return {
      // 手动输入需求
      manualInput: {
        title: '',
        description: '',
        selectedProject: '',
        selectedKnowledgeDocs: [],
        selectedPromptConfig: ''
      },
      
      // 文件上传
      selectedFile: null,
      documentTitle: '',
      selectedProject: '',
      selectedKnowledgeDocs: [],
      selectedPromptConfig: '',
      
      projects: [],
      knowledgeBaseDocs: [],
      promptConfigs: [],
      isDragOver: false,
      
      // 生成状态
      isGenerating: false,
      currentTaskId: null,
      progressText: '准备开始生成...',
      currentStep: 0,
      pollInterval: null,
      
      // 生成结果
      showResults: false,
      generationResult: null
    }
  },
  
  computed: {
    canGenerateManual() {
      return this.manualInput.title.trim() && 
             this.manualInput.description.trim() && 
             this.manualInput.description.length <= 2000
    }
  },
  
  mounted() {
    this.loadProjects()
    this.loadKnowledgeBaseDocs()
    this.loadPromptConfigs()
  },
  
  beforeUnmount() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval)
    }
  },
  
  methods: {
    async loadProjects() {
      try {
        const response = await api.get('/projects/')
        this.projects = response.data.results || response.data
      } catch (error) {
        console.error('加载项目失败:', error)
      }
    },

    async loadKnowledgeBaseDocs() {
      try {
        // 尝试不同的知识库文档API路径
        let response;
        try {
          response = await api.get('/knowledge-graph/api/documents/')
        } catch (e) {
          // 如果新路径失败，尝试旧路径
          response = await api.get('/assistant/api/documents/')
        }
        this.knowledgeBaseDocs = response.data.results || response.data
      } catch (error) {
        console.error('加载知识库文档失败:', error)
      }
    },

    async loadPromptConfigs() {
      try {
        const response = await api.get('/requirement-analysis/api/prompts/')
        const results = response.data.results || response.data
        this.promptConfigs = results.filter(p => p.is_active && p.prompt_type === 'writer')
      } catch (error) {
        console.error('加载提示词配置失败:', error)
      }
    },

    handleDrop(event) {
      event.preventDefault()
      this.isDragOver = false
      const files = event.dataTransfer.files
      if (files.length > 0) {
        this.handleFileSelect({ target: { files } })
      }
    },

    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        const allowedTypes = [
          'application/pdf',
          'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'text/plain'
        ]
        
        if (allowedTypes.includes(file.type) || 
            file.name.match(/\.(pdf|doc|docx|txt|md|markdown|jpg|jpeg|png|gif|bmp|svg)$/i)) {
          this.selectedFile = file
          this.documentTitle = file.name.replace(/\.[^/.]+$/, "")
        } else {
          ElMessage.error('请选择 PDF、Word、TXT、Markdown 或图片格式的文件')
        }
      }
    },

    removeFile() {
      this.selectedFile = null
      this.documentTitle = ''
      this.$refs.fileInput.value = ''
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },

    async generateFromManualInput() {
      if (!this.canGenerateManual) {
        ElMessage.error('请填写完整的需求信息')
        return
      }

      const requirementText = `需求标题: ${this.manualInput.title}\n\n需求描述:\n${this.manualInput.description}`
      
      await this.startGeneration(
        this.manualInput.title, 
        requirementText, 
        this.manualInput.selectedProject,
        this.manualInput.selectedKnowledgeDocs,
        this.manualInput.selectedPromptConfig
      )
    },

    async generateFromDocument() {
      if (!this.selectedFile || !this.documentTitle) {
        ElMessage.error('请选择文件并输入文档标题')
        return
      }

      try {
        // 首先上传并提取文档内容
        const formData = new FormData()
        formData.append('title', this.documentTitle)
        formData.append('file', this.selectedFile)
        if (this.selectedProject) {
          formData.append('project', this.selectedProject)
        }

        ElMessage.info('正在提取文档内容...')
        const uploadResponse = await api.post('/requirement-analysis/api/documents/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })

        // 提取文档内容
        const extractResponse = await api.get(`/requirement-analysis/api/documents/${uploadResponse.data.id}/extract_text/`)
        const extractedText = extractResponse.data.extracted_text

        if (!extractedText || extractedText.trim().length === 0) {
          ElMessage.error('无法从文档中提取到有效内容，请检查文档格式')
          return
        }

        const requirementText = `文档标题: ${this.documentTitle}\n\n文档内容:\n${extractedText}`
        
        await this.startGeneration(
          this.documentTitle, 
          requirementText, 
          this.selectedProject,
          this.selectedKnowledgeDocs,
          this.selectedPromptConfig
        )

      } catch (error) {
        console.error('文档处理失败:', error)
        ElMessage.error('文档处理失败: ' + (error.response?.data?.error || error.message))
      }
    },

    async startGeneration(title, requirementText, projectId, knowledgeBaseIds, promptConfigId) {
      this.isGenerating = true
      this.currentStep = 1
      this.progressText = '正在创建生成任务...'

      try {
        // 调用新的生成API
        const requestData = {
          title: title,
          requirement_text: requirementText,
          use_writer_model: true,
          use_reviewer_model: true
        }
        
        // 如果选择了项目，添加到请求中
        if (projectId) {
          requestData.project = projectId
        }
        
        // 添加 RAG 和 Prompt 配置
        if (knowledgeBaseIds && knowledgeBaseIds.length > 0) {
          requestData.knowledge_base_ids = knowledgeBaseIds
        }
        
        if (promptConfigId) {
          requestData.prompt_config_id = promptConfigId
        }
        
        const response = await api.post('/requirement-analysis/api/testcase-generation/generate/', requestData)

        this.currentTaskId = response.data.task_id
        this.progressText = '任务已创建，正在处理中...'
        
        ElMessage.success('测试用例生成任务已启动')
        
        // 开始轮询任务进度
        this.startPolling()

      } catch (error) {
        console.error('创建生成任务失败:', error)
        ElMessage.error('创建任务失败: ' + (error.response?.data?.error || error.message))
        this.isGenerating = false
      }
    },

    startPolling() {
      this.pollInterval = setInterval(async () => {
        try {
          const response = await api.get(`/requirement-analysis/api/testcase-generation/${this.currentTaskId}/progress/`)
          const task = response.data
          
          console.log(`任务状态: ${task.status}, 进度: ${task.progress}%`)
          
          // 更新进度显示
          if (task.status === 'generating') {
            this.currentStep = 2
            this.progressText = '正在编写测试用例...'
          } else if (task.status === 'reviewing') {
            this.currentStep = 3
            this.progressText = '正在评审测试用例...'
          } else if (task.status === 'completed') {
            this.currentStep = 4
            this.progressText = '生成完成！'
            
            // 任务完成，显示结果
            this.generationResult = task
            this.showResults = true
            this.isGenerating = false
            
            clearInterval(this.pollInterval)
            this.pollInterval = null
            
            ElMessage.success('测试用例生成完成！')
            return
          } else if (task.status === 'failed') {
            this.progressText = '生成失败'
            this.isGenerating = false
            
            clearInterval(this.pollInterval)
            this.pollInterval = null
            
            ElMessage.error('测试用例生成失败: ' + (task.error_message || '未知错误'))
            return
          }
          
        } catch (error) {
          console.error('检查任务进度失败:', error)
          // 继续轮询，不中断
        }
      }, 3000) // 每3秒检查一次
    },

    cancelGeneration() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
      this.isGenerating = false
      this.currentTaskId = null
      ElMessage.info('已取消生成任务')
    },

    // 下载测试用例为xlsx文件
    async downloadTestCases() {
      try {
        // 解析最终测试用例内容
        const finalTestCases = this.generationResult.final_test_cases;
        const taskId = this.generationResult.task_id;

        // 创建工作簿
        const workbook = XLSX.utils.book_new();

        // 过滤掉总结和建议部分，只保留测试用例内容
        const filteredContent = this.filterTestCasesOnly(finalTestCases);

        // 尝试解析表格格式的测试用例（参考AutoGenTestCase的做法）
        const tableFormat = this.parseTableFormat(filteredContent);

        let worksheetData = [];

        if (tableFormat.length > 0) {
          // 如果解析到表格格式，直接使用，但要确保表头正确
          worksheetData = tableFormat;
          
          // 检查并修正表头
          if (worksheetData.length > 0) {
            const header = worksheetData[0];
            for (let i = 0; i < header.length; i++) {
              if (header[i] && header[i].includes('测试步骤')) {
                header[i] = header[i].replace('测试步骤', '操作步骤');
              }
              if (header[i] && header[i].includes('Test Steps')) {
                header[i] = header[i].replace('Test Steps', '操作步骤');
              }
            }
          }
        } else {
          // 否则尝试解析结构化格式
          worksheetData = this.parseStructuredFormat(filteredContent);
        }

        // 将所有单元格中的<br>标签转换为换行符
        worksheetData = worksheetData.map(row =>
          row.map(cell => this.convertBrToNewline(cell))
        );

        // 创建工作表
        const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);

        // 设置列宽
        const colWidths = [
          { wch: 15 }, // 测试用例编号
          { wch: 30 }, // 测试场景
          { wch: 25 }, // 前置条件
          { wch: 40 }, // 操作步骤
          { wch: 30 }, // 预期结果
          { wch: 10 }  // 优先级
        ];
        worksheet['!cols'] = colWidths;

        // 设置表头样式（加粗）
        if (worksheetData.length > 1) {
          for (let col = 0; col < Math.min(6, worksheetData[0].length); col++) {
            const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col });
            if (!worksheet[cellAddress]) continue;
            worksheet[cellAddress].s = {
              font: { bold: true },
              alignment: { horizontal: 'center', vertical: 'center', wrapText: true }
            };
          }
          
          // 设置自动换行
          for (let row = 1; row < worksheetData.length; row++) {
            for (let col = 0; col < Math.min(6, worksheetData[row].length); col++) {
              const cellAddress = XLSX.utils.encode_cell({ r: row, c: col });
              if (worksheet[cellAddress]) {
                worksheet[cellAddress].s = {
                  alignment: { vertical: 'top', wrapText: true }
                };
              }
            }
          }
        }

        // 将工作表添加到工作簿
        XLSX.utils.book_append_sheet(workbook, worksheet, '测试用例');

        // 生成文件名（包含任务ID和日期）
        const fileName = `测试用例_${taskId}_${new Date().toISOString().slice(0, 10)}.xlsx`;

        // 导出文件
        XLSX.writeFile(workbook, fileName);

        ElMessage.success('测试用例下载成功');
      } catch (error) {
        console.error('下载测试用例失败:', error);
        ElMessage.error('下载测试用例失败: ' + (error.message || '未知错误'));
      }
    },

    // 保存到用例记录
    async saveToTestCaseRecords() {
      try {
        // 调用后端API保存到记录
        const response = await api.post(`/requirement-analysis/api/testcase-generation/${this.generationResult.task_id}/save_to_records/`)
        
        if (response.data.already_saved) {
          ElMessage.info('测试用例已经保存过了')
        } else {
          const importedCount = response.data.imported_count || 0
          ElMessage.success(`测试用例已保存！已导入 ${importedCount} 条测试用例到测试用例管理系统`)
        }

        // 不跳转，留在当前页面
        // this.$router.push('/generated-testcases')
      } catch (error) {
        console.error('保存测试用例失败:', error)
        ElMessage.error('保存测试用例失败: ' + (error.response?.data?.error || error.message))
      }
    },

    resetGeneration() {
      // 重置生成状态
      this.isGenerating = false;
      this.currentTaskId = null;
      this.progressText = '准备开始生成...';
      this.currentStep = 0;
      this.showResults = false;
      this.generationResult = null;

      if (this.pollInterval) {
        clearInterval(this.pollInterval);
        this.pollInterval = null;
      }
    },

    // 格式化日期时间
    formatDateTime(dateTimeString) {
      if (!dateTimeString) return '';
      const date = new Date(dateTimeString);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    },

    // 将HTML的<br>标签转换为换行符（用于Excel导出）
    convertBrToNewline(text) {
      if (!text) return '';
      return text.replace(/<br\s*\/?>/gi, '\n');
    },

    // 过滤掉总结和建议部分，只保留测试用例内容
    filterTestCasesOnly(content) {
      if (!content) return '';

      const lines = content.split('\n');
      const filteredLines = [];
      let inTestCaseSection = true;
      
      for (let line of lines) {
        const trimmedLine = line.trim();
        
        // 检查是否到了总结或建议部分
        if (trimmedLine.includes('总结') || 
            trimmedLine.includes('建议') || 
            trimmedLine.includes('Summary') || 
            trimmedLine.includes('Recommendation') ||
            trimmedLine.includes('最后') ||
            trimmedLine.includes('补充说明')) {
          inTestCaseSection = false;
          break;
        }
        
        if (inTestCaseSection) {
          filteredLines.push(line);
        }
      }
      
      return filteredLines.join('\n');
    },

    // 解析表格格式的测试用例（参考AutoGenTestCase的做法）
    parseTableFormat(content) {
      if (!content) return [];
      
      const lines = content.split('\n').filter(line => line.trim());
      const worksheetData = [];
      
      for (let line of lines) {
        const trimmedLine = line.trim();
        
        // 检查是否是表格行（包含|分隔符，且不是分隔线）
        if (trimmedLine.includes('|') && !trimmedLine.includes('--------')) {
          const cells = trimmedLine.split('|').map(cell => cell.trim()).filter(cell => cell);
          if (cells.length > 1) {
            worksheetData.push(cells);
          }
        }
      }
      
      return worksheetData;
    },

    // 解析结构化格式的测试用例
    parseStructuredFormat(content) {
      if (!content) return [];
      
      const lines = content.split('\n').filter(line => line.trim());
      const worksheetData = [];
      
      // 添加表头
      worksheetData.push(['测试用例编号', '测试场景', '前置条件', '操作步骤', '预期结果', '优先级']);
      
      let currentTestCase = {};
      let testCaseNumber = 1;
      let i = 0;
      
      while (i < lines.length) {
        const line = lines[i].trim();
        
        // 识别测试用例开始标志
        if (line.includes('测试用例') || line.includes('Test Case') || 
            line.match(/^(\d+\.|\*|\-|\d+、)/)) {
          
          // 如果之前有测试用例数据，先保存
          if (Object.keys(currentTestCase).length > 0) {
            worksheetData.push([
              currentTestCase.number || `TC${testCaseNumber}`,
              currentTestCase.scenario || '',
              currentTestCase.precondition || '',
              currentTestCase.steps || '',
              currentTestCase.expected || '',
              currentTestCase.priority || '中'
            ]);
            testCaseNumber++;
          }
          
          // 开始新的测试用例
          currentTestCase = {
            number: `TC${testCaseNumber}`,
            scenario: line.replace(/^(\d+\.|\*|\-|\d+、)\s*/, '').replace(/测试用例\d*[:：]?\s*/, ''),
            precondition: '',
            steps: '',
            expected: '',
            priority: '中'
          };
          i++;
        }
        // 识别前置条件
        else if (line.includes('前置条件') || line.includes('前提') || 
                 line.includes('Precondition')) {
          let precondition = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的前置条件行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('测试步骤') || nextLine.includes('操作步骤') || 
                nextLine.includes('Test Steps') || nextLine.includes('步骤') ||
                nextLine.includes('预期结果') || nextLine.includes('Expected') ||
                nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              precondition += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.precondition = precondition;
        }
        // 识别测试步骤
        else if (line.includes('测试步骤') || line.includes('操作步骤') || 
                 line.includes('Test Steps') || line.includes('步骤')) {
          let steps = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的步骤行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('预期结果') || nextLine.includes('Expected') ||
                nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              steps += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.steps = steps;
        }
        // 识别预期结果
        else if (line.includes('预期结果') || line.includes('Expected') || 
                 line.includes('期望')) {
          let expected = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的结果行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              expected += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.expected = expected;
        }
        // 识别优先级
        else if (line.includes('优先级') || line.includes('Priority')) {
          currentTestCase.priority = line.replace(/.*?[:：]\s*/, '');
          i++;
        }
        // 如果是没有明确标识的行，可能是场景描述的延续
        else if (Object.keys(currentTestCase).length > 0 && 
                 !currentTestCase.steps && !currentTestCase.expected && 
                 !currentTestCase.precondition) {
          if (currentTestCase.scenario && line.length > 5) {
            currentTestCase.scenario += '\n' + line;
          }
          i++;
        } else {
          i++;
        }
      }
      
      // 保存最后一个测试用例
      if (Object.keys(currentTestCase).length > 0) {
        worksheetData.push([
          currentTestCase.number || `TC${testCaseNumber}`,
          currentTestCase.scenario || '',
          currentTestCase.precondition || '',
          currentTestCase.steps || '',
          currentTestCase.expected || '',
          currentTestCase.priority || '中'
        ]);
      }
      
      // 如果没有解析到结构化数据，则按原格式输出
      if (worksheetData.length <= 1) {
        worksheetData.length = 0; // 清空
        worksheetData.push(['测试用例内容']);
        content.split('\n').forEach((line, index) => {
          if (line.trim()) {
            worksheetData.push([line.trim()]);
          }
        });
      }
      
      return worksheetData;
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

.requirement-analysis {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.manual-input-card, .upload-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  margin-bottom: 30px;
}

.manual-input-card h2, .upload-card h2 {
  color: #2c3e50;
  margin-bottom: 20px;
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #2c3e50;
}

.form-input, .form-select, .form-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.form-input:focus, .form-select:focus, .form-textarea:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.char-count {
  text-align: right;
  font-size: 0.85rem;
  color: #666;
  margin-top: 5px;
}

.required {
  color: #e74c3c;
}

.generate-manual-btn, .generate-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 15px 30px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1rem;
  transition: background 0.3s ease;
  width: 100%;
  margin-top: 10px;
}

.generate-manual-btn:hover:not(:disabled), .generate-btn:hover:not(:disabled) {
  background: #219a52;
}

.generate-manual-btn:disabled, .generate-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.divider {
  text-align: center;
  margin: 40px 0;
  position: relative;
}

.divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #ddd;
}

.divider span {
  background: white;
  padding: 0 20px;
  color: #666;
  font-size: 1rem;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  transition: border-color 0.3s ease;
  margin-bottom: 20px;
}

.upload-area.drag-over {
  border-color: #3498db;
  background: #f8f9fa;
}

.upload-placeholder {
  color: #666;
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 15px;
  display: block;
}

.upload-hint {
  color: #999;
  font-size: 0.9rem;
  margin-top: 5px;
}

.select-file-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 15px;
}

.file-selected {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 6px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.file-icon {
  font-size: 2rem;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 600;
  margin: 0;
}

.file-size {
  color: #666;
  font-size: 0.9rem;
  margin: 5px 0 0 0;
}

.remove-file {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
}

.generation-progress {
  margin: 40px 0;
}

.progress-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  text-align: center;
}

.progress-card h3 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.progress-info {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.progress-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.progress-item .label {
  font-size: 0.9rem;
  color: #666;
}

.progress-item .value {
  font-weight: 600;
  color: #2c3e50;
}

.progress-steps {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  opacity: 0.4;
  transition: opacity 0.3s ease;
}

.step.active {
  opacity: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: white;
}

.step.active .step-number {
  background: #3498db;
}

.step-text {
  font-size: 0.9rem;
  color: #666;
}

.cancel-generation-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.generation-result {
  margin: 40px 0;
}

.result-header {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.result-header h2 {
  color: #27ae60;
  margin: 0;
}

.result-summary {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.summary-item {
  color: #666;
  font-size: 0.9rem;
}

.new-generation-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.generated-testcases-section, .review-feedback-section, .final-testcases-section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  margin-bottom: 20px;
}

.generated-testcases-section h3, .review-feedback-section h3, .final-testcases-section h3 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.testcase-content, .review-content {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 20px;
  border-left: 4px solid #3498db;
}

.testcase-content pre, .review-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .result-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .progress-info, .result-summary {
    flex-direction: column;
    gap: 10px;
  }
  
  .progress-steps {
    gap: 10px;
  }
}

.actions-section {
  display: flex;
  gap: 20px;
  justify-content: center;
  margin-top: 30px;
  flex-wrap: wrap;
}

.download-btn, .save-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.download-btn {
  background-color: #1abc9c;
  color: white;
}

.download-btn:hover {
  background-color: #16a085;
}

.save-btn {
  background-color: #3498db;
  color: white;
}

.save-btn:hover {
  background-color: #2980b9;
}

@media (max-width: 768px) {
  .actions-section {
    flex-direction: column;
    align-items: center;
  }

  .download-btn, .save-btn {
    width: 100%;
    max-width: 300px;
    justify-content: center;
  }
}
</style>