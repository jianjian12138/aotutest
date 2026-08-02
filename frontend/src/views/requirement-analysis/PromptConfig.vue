<template>
  <BasePage title="提示词配置">
    <template #actions>
      <button class="load-defaults-btn" @click="loadDefaultPrompts">
        📂 加载默认提示词
      </button>
      <button class="add-config-btn" @click="openAddModal">
        ➕ 添加配置
      </button>
    </template>

    <div class="card-container main-content">
      <!-- 配置列表 -->
      <div class="configs-section">
        <div class="section-header">
          <h2>提示词配置列表</h2>
          <div class="header-actions">
            <button class="load-defaults-btn" @click="loadDefaultPrompts">
              📂 加载默认提示词
            </button>
            <button class="add-config-btn" @click="openAddModal">
              ➕ 添加配置
            </button>
          </div>
        </div>

        <div class="configs-grid">
          <div v-for="config in configs" :key="config.id" class="config-card">
            <div class="config-header">
              <div class="config-title">
                <h3>{{ config.name }}</h3>
                <div class="config-badges">
                  <span class="type-badge" :class="config.prompt_type">
                    {{ config.prompt_type_display }}
                  </span>
                  <span class="status-badge" :class="{ active: config.is_active }">
                    {{ config.is_active ? '启用' : '禁用' }}
                  </span>
                </div>
              </div>
              <div class="config-actions">
                <button class="preview-btn" @click="previewPrompt(config)">👁️ 预览</button>
                <button class="edit-btn" @click="editConfig(config)">✏️ 编辑</button>
                <button class="delete-btn" @click="deleteConfig(config.id)">🗑️ 删除</button>
              </div>
            </div>
            
            <div class="config-details">
              <div class="prompt-preview">
                <label>提示词内容预览:</label>
                <div class="content-preview">
                  {{ truncateContent(config.content, 200) }}
                </div>
              </div>
              <div class="config-meta">
                <div class="meta-item">
                  <label>创建时间:</label>
                  <span>{{ formatDateTime(config.created_at) }}</span>
                </div>
                <div class="meta-item">
                  <label>更新时间:</label>
                  <span>{{ formatDateTime(config.updated_at) }}</span>
                </div>
                <div class="meta-item">
                  <label>创建者:</label>
                  <span>{{ config.created_by_name || '未知' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="configs.length === 0" class="empty-state">
          <div class="empty-icon">📝</div>
          <h3>暂无提示词配置</h3>
          <p>请添加提示词配置以自定义AI的行为和输出格式</p>
          <div class="empty-actions">
            <button class="add-first-config-btn" @click="openAddModal">
              ➕ 添加第一个配置
            </button>
            <button class="load-defaults-first-btn" @click="loadDefaultPrompts">
              📂 加载默认提示词
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加/编辑配置弹窗 -->
    <div v-if="showAddModal || showEditModal" class="config-modal" @click="closeModals">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>{{ isEditing ? '编辑' : '添加' }}提示词配置</h3>
          <button class="close-btn" @click="closeModals">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveConfig">
            <div class="form-group">
              <label>配置名称 <span class="required">*</span></label>
              <input 
                v-model="configForm.name" 
                type="text" 
                class="form-input"
                placeholder="例如：测试用例编写提示词 v1.0"
                required>
            </div>

            <div class="form-group">
              <label>提示词类型 <span class="required">*</span></label>
              <select v-model="configForm.prompt_type" class="form-select" required>
                <option value="">请选择提示词类型</option>
                <option value="writer">用例编写提示词</option>
                <option value="reviewer">用例评审提示词</option>
              </select>
            </div>

            <div class="form-group">
              <label>提示词内容 <span class="required">*</span></label>
              <div class="textarea-container">
                <textarea 
                  v-model="configForm.content" 
                  class="form-textarea large"
                  rows="20"
                  placeholder="输入提示词内容，支持Markdown格式"
                  required></textarea>
                <div class="char-count">{{ configForm.content.length }} 字符</div>
              </div>
              <div class="textarea-tips">
                <p><strong>提示词编写建议：</strong></p>
                <ul>
                  <li>明确定义AI的角色和专业领域</li>
                  <li>详细说明输出格式要求</li>
                  <li>提供具体的示例和模板</li>
                  <li>说明需要考虑的测试场景和边界条件</li>
                </ul>
              </div>
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input 
                  v-model="configForm.is_active" 
                  type="checkbox">
                <span class="checkmark"></span>
                启用此配置
              </label>
              <div class="checkbox-hint">
                注意：每种类型只能有一个启用的配置
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="cancel-btn" @click="closeModals">取消</button>
              <button 
                type="submit" 
                class="confirm-btn"
                :disabled="isSaving">
                <span v-if="isSaving">🔄 保存中...</span>
                <span v-else>💾 保存配置</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <div v-if="showPreviewModal" class="preview-modal" @click="closePreview">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>提示词预览 - {{ previewConfig.name }}</h3>
          <button class="close-btn" @click="closePreview">×</button>
        </div>
        <div class="modal-body">
          <div class="preview-content">
            <div class="preview-meta">
              <div class="meta-item">
                <label>类型:</label>
                <span class="type-badge" :class="previewConfig.prompt_type">
                  {{ previewConfig.prompt_type_display }}
                </span>
              </div>
              <div class="meta-item">
                <label>状态:</label>
                <span class="status-badge" :class="{ active: previewConfig.is_active }">
                  {{ previewConfig.is_active ? '启用' : '禁用' }}
                </span>
              </div>
            </div>
            <div class="content-display">
              <label>提示词内容:</label>
              <div class="content-text">{{ previewConfig.content }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 默认提示词预览弹窗 -->
    <div v-if="showDefaultsModal" class="defaults-modal" @click="closeDefaultsModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>默认提示词预览</h3>
          <button class="close-btn" @click="closeDefaultsModal">×</button>
        </div>
        <div class="modal-body">
          <div class="defaults-content">
            <div class="tabs">
              <button 
                class="tab-btn" 
                :class="{ active: activeTab === 'writer' }"
                @click="activeTab = 'writer'">
                📝 编写提示词
              </button>
              <button 
                class="tab-btn" 
                :class="{ active: activeTab === 'reviewer' }"
                @click="activeTab = 'reviewer'">
                🔍 评审提示词
              </button>
            </div>
            
            <div class="tab-content">
              <div class="content-display">
                <div class="content-text">{{ defaultPrompts[activeTab] || '暂无内容' }}</div>
              </div>
            </div>
          </div>
          
          <div class="modal-actions">
            <button class="cancel-btn" @click="closeDefaultsModal">取消</button>
            <button 
              class="confirm-btn" 
              @click="confirmLoadDefaults"
              :disabled="isLoadingDefaults">
              <span v-if="isLoadingDefaults">🔄 加载中...</span>
              <span v-else>📂 确认加载</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </BasePage>
</template>
<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'PromptConfig',
  data() {
    return {
      configs: [],
      showAddModal: false,
      showEditModal: false,
      showPreviewModal: false,
      showDefaultsModal: false,
      isEditing: false,
      isSaving: false,
      isLoadingDefaults: false,
      editingConfigId: null,
      previewConfig: {},
      defaultPrompts: {
        writer: '',
        reviewer: ''
      },
      activeTab: 'writer',
      configForm: {
        name: '',
        prompt_type: '',
        content: '',
        is_active: true
      }
    }
  },

  mounted() {
    this.loadConfigs()
  },

  methods: {
    openAddModal() {
      console.log('openAddModal clicked')
      this.resetForm()
      this.isEditing = false
      this.showAddModal = true
      console.log('showAddModal set to:', this.showAddModal)
    },

    async loadConfigs() {
      try {
        console.log('Loading prompt configs...')
        const response = await api.get('/requirement-analysis/api/prompts/')
        console.log('Prompts API response:', response.data)
        
        // 处理分页API响应格式
        if (response.data && response.data.results && Array.isArray(response.data.results)) {
          this.configs = response.data.results
          console.log('Loaded configs from results:', this.configs)
        } else if (response.data && Array.isArray(response.data)) {
          // 直接数组格式的fallback
          this.configs = response.data
          console.log('Loaded configs from direct array:', this.configs)
        } else {
          console.warn('Unexpected API response format:', response.data)
          this.configs = []
        }
        
        console.log('Final configs count:', this.configs.length)
      } catch (error) {
        console.error('加载配置失败:', error)
        this.configs = [] // 确保configs始终是数组
        
        if (error.response?.status === 401) {
          ElMessage.error('请先登录')
        } else {
          ElMessage.error('加载配置失败: ' + (error.response?.data?.error || error.message))
        }
      }
    },

    async loadDefaultPrompts() {
      console.log('loadDefaultPrompts clicked')
      try {
        const response = await api.get('/requirement-analysis/api/prompts/load_defaults/')
        console.log('Default prompts response:', response.data)
        this.defaultPrompts = response.data.defaults
        this.showDefaultsModal = true
        console.log('showDefaultsModal set to:', this.showDefaultsModal)
      } catch (error) {
        console.error('加载默认提示词失败:', error)
        ElMessage.error('加载默认提示词失败: ' + (error.response?.data?.error || error.message))
      }
    },

    async confirmLoadDefaults() {
      this.isLoadingDefaults = true
      
      try {
        // 创建编写提示词配置
        if (this.defaultPrompts.writer) {
          await api.post('/requirement-analysis/api/prompts/', {
            name: '默认用例编写提示词',
            prompt_type: 'writer',
            content: this.defaultPrompts.writer,
            is_active: true
          })
        }

        // 创建评审提示词配置
        if (this.defaultPrompts.reviewer) {
          await api.post('/requirement-analysis/api/prompts/', {
            name: '默认用例评审提示词',
            prompt_type: 'reviewer',
            content: this.defaultPrompts.reviewer,
            is_active: true
          })
        }

        ElMessage.success('默认提示词加载成功')
        this.closeDefaultsModal()
        this.loadConfigs()
      } catch (error) {
        console.error('加载默认提示词失败:', error)
        ElMessage.error('加载失败: ' + (error.response?.data?.error || error.message))
      } finally {
        this.isLoadingDefaults = false
      }
    },

    resetForm() {
      this.configForm = {
        name: '',
        prompt_type: '',
        content: '',
        is_active: true
      }
    },

    editConfig(config) {
      this.isEditing = true
      this.editingConfigId = config.id
      this.configForm = {
        name: config.name,
        prompt_type: config.prompt_type,
        content: config.content,
        is_active: config.is_active
      }
      this.showEditModal = true
    },

    previewPrompt(config) {
      this.previewConfig = config
      this.showPreviewModal = true
    },

    async saveConfig() {
      this.isSaving = true
      
      try {
        if (this.isEditing) {
          await api.patch(`/requirement-analysis/api/prompts/${this.editingConfigId}/`, this.configForm)
          ElMessage.success('配置更新成功')
        } else {
          await api.post('/requirement-analysis/api/prompts/', this.configForm)
          ElMessage.success('配置添加成功')
        }
        
        this.closeModals()
        this.loadConfigs()
      } catch (error) {
        console.error('保存配置失败:', error)
        ElMessage.error('保存失败: ' + (error.response?.data?.error || error.message))
      } finally {
        this.isSaving = false
      }
    },

    async deleteConfig(configId) {
      if (!confirm('确定要删除此配置吗？')) {
        return
      }

      try {
        await api.delete(`/requirement-analysis/api/prompts/${configId}/`)
        ElMessage.success('配置删除成功')
        this.loadConfigs()
      } catch (error) {
        console.error('删除配置失败:', error)
        ElMessage.error('删除失败: ' + (error.response?.data?.error || error.message))
      }
    },

    closeModals() {
      this.showAddModal = false
      this.showEditModal = false
      this.isEditing = false
      this.editingConfigId = null
      this.resetForm()
    },

    closePreview() {
      this.showPreviewModal = false
      this.previewConfig = {}
    },

    closeDefaultsModal() {
      this.showDefaultsModal = false
      this.defaultPrompts = { writer: '', reviewer: '' }
      this.activeTab = 'writer'
    },

    truncateContent(content, maxLength) {
      if (!content) return ''
      if (content.length <= maxLength) return content
      return content.substring(0, maxLength) + '...'
    },

    formatDateTime(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
/* 页面特定样式 */
.prompt-config {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.section-header h2 {
  color: #2c3e50;
  margin: 0;
}

.load-defaults-btn {
  background: #9b59b6;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.3s ease;
}

.load-defaults-btn:hover {
  background: #8e44ad;
}

.add-config-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.3s ease;
}

.add-config-btn:hover {
  background: #219a52;
}

.configs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
  gap: 20px;
}

.config-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.config-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.15);
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.config-title h3 {
  color: #2c3e50;
  margin: 0 0 10px 0;
  font-size: 1.3rem;
}

.config-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.type-badge, .status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.type-badge.writer {
  background: #e8f5e8;
  color: #388e3c;
}

.type-badge.reviewer {
  background: #fff3e0;
  color: #f57c00;
}

.status-badge {
  background: #ffebee;
  color: #d32f2f;
}

.status-badge.active {
  background: #e8f5e8;
  color: #388e3c;
}

.config-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-btn, .edit-btn, .delete-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.3s ease;
}

.preview-btn {
  background: #3498db;
  color: white;
}

.preview-btn:hover {
  background: #2980b9;
}

.edit-btn {
  background: #f39c12;
  color: white;
}

.edit-btn:hover {
  background: #e67e22;
}

.delete-btn {
  background: #e74c3c;
  color: white;
}

.delete-btn:hover {
  background: #c0392b;
}

.config-details {
  margin-top: 20px;
}

.prompt-preview {
  margin-bottom: 15px;
}

.prompt-preview label {
  font-size: 0.85rem;
  color: #666;
  font-weight: 600;
  display: block;
  margin-bottom: 8px;
}

.content-preview {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  color: #2c3e50;
  font-size: 0.9rem;
  line-height: 1.5;
  border-left: 4px solid #3498db;
}

.config-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item label {
  font-size: 0.85rem;
  color: #666;
  font-weight: 600;
}

.meta-item span {
  color: #2c3e50;
  font-size: 0.9rem;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #666;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.empty-state h3 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.empty-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-top: 20px;
  flex-wrap: wrap;
}

.add-first-config-btn, .load-defaults-first-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 15px 30px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1rem;
  transition: background 0.3s ease;
}

.add-first-config-btn:hover {
  background: #2980b9;
}

.load-defaults-first-btn {
  background: #9b59b6;
}

.load-defaults-first-btn:hover {
  background: #8e44ad;
}

.config-modal, .preview-modal, .defaults-modal {
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
  padding: 0;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content.large {
  max-width: 900px;
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

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #2c3e50;
}

.form-input, .form-select {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.textarea-container {
  position: relative;
}

.form-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  resize: vertical;
  min-height: 200px;
  transition: border-color 0.3s ease;
}

.form-textarea.large {
  min-height: 400px;
}

.form-textarea:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.char-count {
  text-align: right;
  font-size: 0.8rem;
  color: #666;
  margin-top: 5px;
}

.textarea-tips {
  margin-top: 10px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #3498db;
}

.textarea-tips p {
  margin: 0 0 10px 0;
  color: #2c3e50;
  font-weight: 600;
}

.textarea-tips ul {
  margin: 0;
  padding-left: 20px;
}

.textarea-tips li {
  color: #666;
  margin-bottom: 5px;
  line-height: 1.4;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
}

.checkbox-hint {
  margin-top: 5px;
  font-size: 0.85rem;
  color: #666;
  font-style: italic;
}

.required {
  color: #e74c3c;
}

.modal-actions {
  display: flex;
  gap: 15px;
  justify-content: flex-end;
  margin-top: 30px;
}

.cancel-btn {
  background: #95a5a6;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.cancel-btn:hover {
  background: #7f8c8d;
}

.confirm-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.confirm-btn:hover:not(:disabled) {
  background: #219a52;
}

.confirm-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.preview-content, .defaults-content {
  margin-bottom: 20px;
}

.preview-meta {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
}

.preview-meta .meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.content-display {
  margin-bottom: 20px;
}

.content-display label {
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 10px;
  display: block;
}

.content-text {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 6px;
  color: #2c3e50;
  line-height: 1.6;
  white-space: pre-wrap;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9rem;
  border-left: 4px solid #3498db;
  max-height: 400px;
  overflow-y: auto;
}

.tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 20px;
  border-bottom: 1px solid #ddd;
}

.tab-btn {
  background: none;
  border: none;
  padding: 12px 20px;
  cursor: pointer;
  color: #666;
  font-size: 1rem;
  border-bottom: 2px solid transparent;
  transition: all 0.3s ease;
}

.tab-btn.active {
  color: #3498db;
  border-bottom-color: #3498db;
  background: #f8f9fa;
}

.tab-btn:hover {
  background: #f8f9fa;
}

@media (max-width: 768px) {
  .configs-grid {
    grid-template-columns: 1fr;
  }
  
  .config-header {
    flex-direction: column;
    gap: 15px;
    align-items: flex-start;
  }
  
  .empty-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .preview-meta {
    flex-direction: column;
    gap: 10px;
  }
}
</style>
