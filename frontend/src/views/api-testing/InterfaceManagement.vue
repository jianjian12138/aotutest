<template>
  <BasePage title="接口管理">
    <template #actions>
      <el-select v-model="selectedProject" placeholder="选择项目" @change="onProjectChange" style="width: 200px; margin-right: 8px;">
        <el-option
          v-for="project in projects"
          :key="project.id"
          :label="project.name"
          :value="project.id"
        />
      </el-select>
      <el-button type="primary" @click="createEmptyRequest">
        <el-icon><DocumentAdd /></el-icon>
        新建接口
      </el-button>
      <el-button @click="showCreateCollectionDialog = true">
        <el-icon><FolderAdd /></el-icon>
        新建分组
      </el-button>
      <el-button @click="showImportDialog = true">
        <el-icon><Download /></el-icon>
        导入接口
      </el-button>
    </template>
    <div class="interface-manage-page">
      <div class="interface-layout">
      <!-- 左侧集合树 -->
      <div class="sidebar">
              <div class="sidebar-header">
                <el-select v-model="selectedProject" placeholder="选择项目" @change="onProjectChange" class="project-select">
                  <el-option
                    v-for="project in projects"
                    :key="project.id"
                    :label="project.name"
                    :value="project.id"
                  />
                </el-select>
              </div>
              
              <div class="sidebar-toolbar">
                <el-input 
                  v-model="searchText" 
                  placeholder="搜索接口..." 
                  :prefix-icon="Search" 
                  clearable 
                  size="small" 
                  class="search-input"
                />
                <div class="toolbar-actions">
                  <el-dropdown trigger="click">
                    <el-button size="small" circle>
                      <el-icon><Plus /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item @click="createEmptyRequest">
                          <el-icon><DocumentAdd /></el-icon>新建接口
                        </el-dropdown-item>
                        <el-dropdown-item @click="showCreateCollectionDialog = true">
                          <el-icon><FolderAdd /></el-icon>新建分组
                        </el-dropdown-item>
                        <el-dropdown-item divided @click="showImportDialog = true">
                          <el-icon><Download /></el-icon>导入接口
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
          
              <div class="collection-tree-container">
                <el-tree
                  ref="treeRef"
                  :data="filteredTreeData"
                  :props="defaultProps"
                  node-key="id"
                  :expand-on-click-node="false"
                  :default-expanded-keys="expandedKeys"
                  @node-click="onNodeClick"
                  @node-contextmenu="onNodeRightClick"
                  @node-expand="onNodeExpand"
                  @node-collapse="onNodeCollapse"
                  class="custom-tree"
                >
                  <template #default="{ node, data }">
                    <div class="tree-node" :class="{ 'is-active': selectedRequest?.id === data.id }">
                      <!-- 上传中节点 -->
                      <template v-if="data.type === 'uploading'">
                        <el-icon v-if="data.status === 'uploading'" class="uploading-icon">
                          <UploadFilled />
                        </el-icon>
                        <el-icon v-else-if="data.status === 'processing'" class="processing-icon">
                          <Loading />
                        </el-icon>
                        <span class="node-label uploading-node">{{ node.label }}</span>
                      </template>
                      
                      <!-- 分组节点 -->
                      <template v-else-if="data.type === 'collection' || data.children">
                        <el-icon class="folder-icon"><Folder /></el-icon>
                        <span class="node-label">{{ node.label }}</span>
                      </template>
                      
                      <!-- 接口节点 -->
                      <template v-else>
                        <span class="method-indicator" :class="data.method?.toLowerCase()">
                          {{ data.method }}
                        </span>
                        <span class="node-label" :title="node.label">{{ node.label }}</span>
                      </template>
                    </div>
                  </template>
                </el-tree>
              </div>
            </div>

            <!-- 右侧请求详情 -->
            <div class="request-content">
              <div v-if="!selectedRequest" class="empty-state">
                <el-empty description="请选择一个接口查看详情，或点击上方绿色按钮创建新接口">
                  <el-button type="primary" @click="createEmptyRequest">创建新接口</el-button>
                </el-empty>
              </div>
              
              <div v-else class="request-detail">
                <!-- 请求基本信息 -->
                <div class="request-header-area">
                  <div class="header-top">
                    <div class="title-container">
                      <el-input 
                        v-model="selectedRequest.name" 
                        placeholder="接口名称" 
                        class="interface-title-input"
                      />
                    </div>
                    <div class="header-actions">
                      <el-select v-model="selectedEnvironment" placeholder="选择环境" size="small" class="env-selector">
                        <el-option label="无环境" :value="null" />
                        <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
                      </el-select>
                      <el-button-group class="action-btns">
                        <el-button type="primary" @click="saveRequest" :loading="saving">
                          <el-icon><CircleCheck /></el-icon>保存
                        </el-button>
                        <el-dropdown trigger="click">
                          <el-button type="primary" class="more-btn">
                            <el-icon><ArrowDown /></el-icon>
                          </el-button>
                          <template #dropdown>
                            <el-dropdown-menu>
                              <el-dropdown-item @click="copyCurl">复制 cURL</el-dropdown-item>
                              <el-dropdown-item @click="deleteNode">删除接口</el-dropdown-item>
                            </el-dropdown-menu>
                          </template>
                        </el-dropdown>
                      </el-button-group>
                    </div>
                  </div>

                  <div class="url-bar">
                    <div class="method-url-group">
                      <el-select 
                        v-model="selectedRequest.method" 
                        class="method-selector-compact"
                        :class="selectedRequest.method.toLowerCase()"
                      >
                        <el-option v-for="method in availableMethods" :key="method" :label="method" :value="method" />
                      </el-select>
                      <el-input 
                        v-model="selectedRequest.url" 
                        placeholder="输入请求URL，支持 {{variable}} 语法" 
                        class="url-input-compact" 
                      />
                    </div>
                    <el-button type="primary" @click="sendRequest" :loading="sending" class="send-button-large">
                      <span>发送</span>
                      <el-icon class="el-icon--right"><Promotion /></el-icon>
                    </el-button>
                  </div>
                </div>

                <!-- 模式切换 -->
                <el-tabs v-model="modeTab" class="mode-tabs">
                  <el-tab-pane label="文档 / 设计" name="design">
                    <div class="design-container">
                      <div class="design-section">
                        <div class="section-title">请求参数</div>
                        <el-tabs v-model="activeTab" class="design-tabs">
                          <el-tab-pane label="Query 参数" name="params">
                            <div class="tab-pane-content">
                              <KeyValueEditor v-model="selectedRequest.params" />
                            </div>
                          </el-tab-pane>
                          <el-tab-pane label="Headers" name="headers">
                            <div class="tab-pane-content">
                              <KeyValueEditor ref="headersEditorRef" v-model="selectedRequest.headers" />
                            </div>
                          </el-tab-pane>
                          <el-tab-pane label="Body" name="body" v-if="hasBody">
                            <div class="tab-pane-content">
                              <el-radio-group v-model="bodyType" size="small" style="margin-bottom: 15px;">
                                <el-radio value="none">none</el-radio>
                                <el-radio value="json">json</el-radio>
                                <el-radio value="form-data">form-data</el-radio>
                              </el-radio-group>
                              
                              <div v-if="bodyType === 'json'" class="body-editor-container">
                                <el-input
                                  v-model="rawBody"
                                  type="textarea"
                                  :rows="12"
                                  placeholder='{"key": "value"}'
                                  class="code-input"
                                />
                              </div>
                              <div v-else-if="bodyType === 'form-data'">
                                <KeyValueEditor v-model="formData" :show-file="true" />
                              </div>
                            </div>
                          </el-tab-pane>
                          <el-tab-pane label="断言规则" name="assertions">
                            <div class="tab-pane-content">
                              <div class="action-bar">
                                <el-button type="primary" size="small" @click="addAssertion">
                                  <el-icon><Plus /></el-icon>添加断言
                                </el-button>
                              </div>
                              <div class="rules-list">
                                <div v-for="(assertion, index) in selectedRequest.assertions" :key="index" class="rule-card">
                                  <div class="rule-header">
                                    <el-input v-model="assertion.name" placeholder="断言名称" size="small" class="rule-name-input" />
                                    <el-button type="danger" size="small" link @click="removeAssertion(index)">
                                      <el-icon><Delete /></el-icon>
                                    </el-button>
                                  </div>
                                  <div class="rule-body">
                                    <el-select v-model="assertion.type" placeholder="断言类型" size="small" style="width: 140px">
                                      <el-option label="状态码" value="status_code" />
                                      <el-option label="响应时间" value="response_time" />
                                      <el-option label="JSON路径" value="json_path" />
                                      <el-option label="包含文本" value="contains" />
                                    </el-select>
                                    <el-input v-if="assertion.type === 'json_path'" v-model="assertion.json_path" placeholder="JSONPath 表达式" size="small" style="flex: 1" />
                                    <el-input v-model="assertion.expected" placeholder="期望值" size="small" style="width: 200px" />
                                  </div>
                                </div>
                              </div>
                            </div>
                          </el-tab-pane>
                          <el-tab-pane label="提取变量" name="extract">
                            <div class="tab-pane-content">
                              <div class="action-bar">
                                <el-button type="primary" size="small" @click="addExtractRule">
                                  <el-icon><Plus /></el-icon>添加提取
                                </el-button>
                              </div>
                              <div class="rules-list">
                                <div v-for="(rule, index) in selectedRequest.extract_rules" :key="index" class="rule-card">
                                  <div class="rule-header">
                                    <el-input v-model="rule.variable_name" placeholder="变量名" size="small" class="rule-name-input" />
                                    <el-button type="danger" size="small" link @click="removeExtractRule(index)">
                                      <el-icon><Delete /></el-icon>
                                    </el-button>
                                  </div>
                                  <div class="rule-body">
                                    <el-select v-model="rule.type" placeholder="提取方式" size="small" style="width: 140px">
                                      <el-option label="JSON路径" value="json_path" />
                                      <el-option label="正则" value="regex" />
                                    </el-select>
                                    <el-input v-model="rule.json_path" placeholder="表达式" size="small" style="flex: 1" />
                                  </div>
                                </div>
                              </div>
                            </div>
                          </el-tab-pane>
                        </el-tabs>
                      </div>
                    </div>
                  </el-tab-pane>

                  <el-tab-pane label="运行 / 调试" name="debug">
                    <div class="debug-container">
                      <div class="debug-request-pane">
                        <div class="pane-header">请求配置</div>
                        <el-tabs v-model="debugActiveTab" class="compact-tabs">
                          <el-tab-pane label="Query 参数" name="params">
                            <KeyValueEditor v-model="selectedRequest.params" size="small" />
                          </el-tab-pane>
                          <el-tab-pane label="Headers" name="headers">
                            <KeyValueEditor v-model="selectedRequest.headers" size="small" />
                          </el-tab-pane>
                          <el-tab-pane label="Body" name="body" v-if="hasBody">
                            <div class="debug-body-editor">
                              <el-radio-group v-model="bodyType" size="small" class="body-type-selector">
                                <el-radio value="none">none</el-radio>
                                <el-radio value="json">json</el-radio>
                                <el-radio value="form-data">form-data</el-radio>
                              </el-radio-group>
                              <el-input
                                v-if="bodyType === 'json'"
                                v-model="rawBody"
                                type="textarea"
                                :rows="8"
                                placeholder='{"key": "value"}'
                                class="monospaced-input"
                              />
                              <KeyValueEditor v-if="bodyType === 'form-data'" v-model="formData" :show-file="true" size="small" />
                            </div>
                          </el-tab-pane>
                        </el-tabs>
                      </div>
                      
                      <div class="debug-response-pane">
                        <div class="pane-header">
                          <span>响应结果</span>
                          <div v-if="response" class="response-meta-tags">
                            <el-tag :type="getStatusType(response.status_code)" effect="dark" size="small">
                              {{ response.status_code }} {{ response.status_text || 'OK' }}
                            </el-tag>
                            <el-tag type="info" size="small">{{ response.response_time?.toFixed(0) }} ms</el-tag>
                            <el-tag type="info" size="small">{{ formatSize(response.response_data?.size) }}</el-tag>
                          </div>
                        </div>

                        <div v-if="response" class="response-content-area">
                          <el-tabs v-model="responseActiveTab" class="compact-tabs">
                            <el-tab-pane label="请求信息" name="request">
                              <div class="response-viewer">
                                <div class="request-info-section">
                                  <div class="info-item">
                                    <span class="info-label">请求地址:</span>
                                    <el-tag size="small" type="info" class="info-value">{{ response.request_data?.url }}</el-tag>
                                  </div>
                                  <div class="info-item">
                                    <span class="info-label">请求方法:</span>
                                    <el-tag size="small" :type="getStatusType(200)" class="info-value">{{ response.request_data?.method }}</el-tag>
                                  </div>
                                </div>
                                <div class="request-detail-section">
                                  <div class="detail-title">请求头 (Headers)</div>
                                  <pre class="code-block small">{{ JSON.stringify(response.request_data?.headers, null, 2) }}</pre>
                                </div>
                                <div class="request-detail-section" v-if="response.request_data?.body">
                                  <div class="detail-title">请求体 (Body)</div>
                                  <pre class="code-block small">{{ typeof response.request_data?.body === 'string' ? response.request_data?.body : JSON.stringify(response.request_data?.body, null, 2) }}</pre>
                                </div>
                              </div>
                            </el-tab-pane>
                            <el-tab-pane label="响应 Body" name="body">
                              <div class="response-body-toolbar">
                                <el-radio-group v-model="responseViewMode" size="small">
                                  <el-radio-button label="pretty">Pretty</el-radio-button>
                                  <el-radio-button label="raw">Raw</el-radio-button>
                                  <el-radio-button label="preview">Preview</el-radio-button>
                                </el-radio-group>
                                <el-button size="small" link @click="copyResponse">
                                  <el-icon><CopyDocument /></el-icon>复制
                                </el-button>
                              </div>
                              <div class="response-viewer">
                                <pre v-if="responseViewMode === 'pretty'" class="code-block">{{ responseBody }}</pre>
                                <pre v-else-if="responseViewMode === 'raw'" class="code-block">{{ response.response_data?.body }}</pre>
                                <div v-else-if="responseViewMode === 'preview'" class="preview-block" v-html="response.response_data?.body"></div>
                              </div>
                            </el-tab-pane>
                            <el-tab-pane label="Headers" name="headers">
                              <div class="response-headers-table">
                                <div v-for="(value, key) in response.response_headers" :key="key" class="header-item">
                                  <span class="header-key">{{ key }}:</span>
                                  <span class="header-value">{{ value }}</span>
                                </div>
                              </div>
                            </el-tab-pane>
                            <el-tab-pane label="断言结果" name="assertions">
                              <div class="assertion-results-list">
                                <div v-if="!response.assertion_results?.length" class="empty-results">未配置断言</div>
                                <div v-for="(res, idx) in response.assertion_results" :key="idx" 
                                     class="assertion-result-row" :class="res.status">
                                  <el-icon><CircleCheck v-if="res.status === 'passed'" /><CircleClose v-else /></el-icon>
                                  <span class="assertion-desc">{{ res.message }}</span>
                                </div>
                              </div>
                            </el-tab-pane>
                          </el-tabs>
                        </div>
                        <div v-else class="response-empty">
                          <el-empty description="点击“发送”按钮以获取响应数据" :image-size="100" />
                        </div>
                      </div>
                    </div>
                  </el-tab-pane>
                </el-tabs>
              </div>
            </div>
          </div> <!-- Close interface-layout -->

    <!-- 创建集合对话框 -->
    <el-dialog v-model="showCreateCollectionDialog" title="创建集合" width="500px">
      <el-form ref="collectionFormRef" :model="collectionForm" :rules="collectionRules" label-width="80px">
        <el-form-item label="集合名称" prop="name">
          <el-input v-model="collectionForm.name" placeholder="请输入集合名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="collectionForm.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="父级集合" prop="parent">
          <el-select v-model="collectionForm.parent" placeholder="选择父级集合（可选）" clearable>
            <el-option
              v-for="collection in flatCollections"
              :key="collection.id"
              :label="collection.name"
              :value="collection.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateCollectionDialog = false">取消</el-button>
        <el-button type="primary" @click="createCollection">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑集合对话框 -->
    <el-dialog v-model="showEditCollectionDialog" title="编辑集合" width="500px">
      <el-form ref="editCollectionFormRef" :model="editCollectionForm" :rules="collectionRules" label-width="80px">
        <el-form-item label="集合名称" prop="name">
          <el-input v-model="editCollectionForm.name" placeholder="请输入集合名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="editCollectionForm.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="父级集合" prop="parent">
          <el-select v-model="editCollectionForm.parent" placeholder="选择父级集合（可选）" clearable>
            <el-option
              v-for="collection in flatCollections.filter(c => c.id !== editCollectionForm.id)"
              :key="collection.id"
              :label="collection.name"
              :value="collection.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showEditCollectionDialog = false">取消</el-button>
        <el-button type="primary" @click="updateCollection">保存</el-button>
      </template>
    </el-dialog>

    <!-- 右键菜单 -->
    <ul v-show="showContextMenu" class="context-menu" :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }">
      <li @click="addRequest">添加请求</li>
      <li @click="addCollection">添加子集合</li>
      <li @click="editNode">编辑</li>
      <li @click="deleteNode">删除</li>
    </ul>

    <!-- 导入对话框 -->
    <el-dialog v-model="showImportDialog" title="导入接口" width="600px">
      <el-form ref="importFormRef" :model="importForm" :rules="importRules" label-width="100px">
        <el-form-item label="数据格式" prop="format">
          <el-radio-group v-model="importForm.format">
            <el-radio label="postman">Postman</el-radio>
            <el-radio label="apifox">Apifox</el-radio>
            <el-radio label="jmeter">JMeter</el-radio>
            <el-radio label="swagger">Swagger</el-radio>
            <el-radio label="custom">自定义</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="导入模式" prop="mode">
          <el-radio-group v-model="importForm.mode">
            <el-radio label="overwrite">覆盖现有数据</el-radio>
            <el-radio label="append">追加到现有数据</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="选择文件" prop="file">
          <el-upload
            ref="uploadRef"
            drag
            action="#"
            :auto-upload="false"
            :show-file-list="true"
            :on-change="handleFileChange"
            :before-upload="beforeUpload"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持上传JSON/YAML/JMX/Excel/CSV格式文件，大小不超过50MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing">导入</el-button>
      </template>
    </el-dialog>

    <!-- AI生成SQL对话框 -->
    <el-dialog v-model="showGenerateSqlDialog" title="AI生成SQL" width="500px">
      <div style="margin-bottom: 15px;">
        <p style="margin-bottom: 10px; color: #606266;">请输入您的自然语言需求，AI将根据选定的数据库配置自动生成SQL语句。</p>
        <el-input 
          v-model="generateSqlPrompt" 
          type="textarea" 
          :rows="4" 
          placeholder="例如：查询用户表(users)中状态为active的用户数量" 
        />
      </div>
      <template #footer>
        <el-button @click="showGenerateSqlDialog = false">取消</el-button>
        <el-button type="primary" @click="handleGenerateSql" :loading="generatingSql">生成SQL</el-button>
      </template>
    </el-dialog>
  </div>
  </BasePage>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Folder, Document, UploadFilled, Close, DocumentAdd, Download, Search, CircleCheck, ArrowDown, Promotion, CopyDocument, CircleClose, Loading, Delete, FolderAdd } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { getVannaConfigs, generateSql } from '@/api/data-factory'
import KeyValueEditor from './components/KeyValueEditor.vue'
import '@/assets/css/global.scss'

const treeRef = ref(null)
const expandedKeys = ref([])
const projects = ref([])
const selectedProject = ref(null)
const collections = ref([])
const flatCollections = ref([])
const environments = ref([])
const selectedEnvironment = ref(null)
const executionEngine = ref('requests')
const selectedRequest = ref(null)
const response = ref(null)
const sending = ref(false)
const saving = ref(false)
const activeTab = ref('params')
const responseActiveTab = ref('body')
const responseViewMode = ref('pretty')
const debugActiveTab = ref('params')

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
const showCreateCollectionDialog = ref(false)
const showEditCollectionDialog = ref(false)
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const rightClickedNode = ref(null)
const headersEditorRef = ref(null)
const editingNodeId = ref(null)
const editingNodeName = ref('')
const editInputRef = ref(null)

// 模式切换
const modeTab = ref('design')
const searchText = ref('')

// 过滤后的集合树
const filteredTreeData = computed(() => {
  if (!searchText.value) return collections.value
  
  const search = searchText.value.toLowerCase()
  const filterNode = (nodes) => {
    const result = []
    for (const node of nodes) {
      const matchName = node.name && node.name.toLowerCase().includes(search)
      let filteredChildren = []
      
      if (node.children && node.children.length > 0) {
        filteredChildren = filterNode(node.children)
      }
      
      if (matchName || filteredChildren.length > 0) {
        result.push({
          ...node,
          children: filteredChildren
        })
      }
    }
    return result
  }
  
  return filterNode(collections.value)
})

// 数据库配置
const vannaConfigs = ref([])

// 导入相关数据
const showImportDialog = ref(false)
const importFormRef = ref(null)
const uploadRef = ref(null)
const importing = ref(false)
const importForm = reactive({
  format: 'postman',
  mode: 'overwrite',
  file: null
})
const importRules = {
  format: [{ required: true, message: '请选择数据格式', trigger: 'change' }],
  mode: [{ required: true, message: '请选择导入模式', trigger: 'change' }],
  file: [{ required: true, message: '请选择要导入的文件', trigger: 'change' }]
}
const selectedFile = ref(null)

// 辅助函数：将对象或数组转换为键值对数组（用于KeyValueEditor组件）
const convertObjectToKeyValueArray = (obj) => {
  if (!obj) return []
  
  // 如果已经是数组格式（新的完整格式），直接返回
  if (Array.isArray(obj)) {
    console.log('Input is already array format:', obj)
    return obj.map(item => ({
      key: item.key || '',
      value: item.value || '',
      enabled: item.enabled !== false,
      description: item.description || ''
    }))
  }
  
  // 如果是对象格式（旧的简单key-value格式），转换为数组
  if (typeof obj === 'object') {
    console.log('Converting object to array:', obj)
    return Object.entries(obj).map(([key, value]) => ({
      key,
      value: String(value),
      enabled: true,
      description: ''
    }))
  }
  
  return []
}

// 辅助函数：将键值对数组转换为对象（保存时使用）
const convertKeyValueArrayToObject = (input) => {
  console.log('convertKeyValueArrayToObject input:', input)
  
  // 如果输入已经是普通对象，直接返回
  if (input && typeof input === 'object' && !Array.isArray(input)) {
    console.log('Input is already an object, returning as-is')
    return input
  }
  
  // 如果输入是数组，转换为对象
  if (!Array.isArray(input)) return {}
  
  const obj = {}
  input.forEach(item => {
    console.log('Processing item:', item, 'enabled:', item.enabled)
    if (item.enabled !== false && item.key) {
      obj[item.key] = item.value || ''
      console.log('Added to obj:', item.key, '=', item.value)
    }
  })
  console.log('convertKeyValueArrayToObject output:', obj)
  return obj
}

const httpMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
const websocketMethods = ['CONNECT', 'SUBSCRIBE', 'UNSUBSCRIBE', 'SEND', 'PING', 'PONG']

const availableMethods = computed(() => {
  return selectedRequest.value && selectedRequest.value.request_type === 'WEBSOCKET' 
    ? websocketMethods 
    : httpMethods
})

// 处理请求类型变更
const onRequestTypeChange = () => {
  if (!selectedRequest.value) return
  
  const request = selectedRequest.value
  
  // 更新默认方法
  if (request.request_type === 'WEBSOCKET') {
    request.method = 'CONNECT'
    // 更新URL格式（如果当前URL不是WebSocket格式）
    if (!request.url.startsWith('ws://') && !request.url.startsWith('wss://')) {
      request.url = 'ws://{{host}}/websocket'
    }
    // 更新请求头
    request.headers = convertObjectToKeyValueArray({})
  } else {
    request.method = 'GET'
    // 更新URL格式（如果当前URL是WebSocket格式）
    if (request.url.startsWith('ws://') || request.url.startsWith('wss://')) {
      request.url = '{{base_url}}/api/new-endpoint'
    }
    // 更新请求头
    request.headers = convertObjectToKeyValueArray({
      'Content-Type': 'application/json'
    })
  }
  
  // 重置响应
  response.value = null
  
  // 重置WebSocket连接
  if (websocketConnectionStatus.value !== 'disconnected') {
    disconnectWebSocket()
  }
  
  // 重置body相关设置
  bodyType.value = 'none'
  rawBody.value = ''
  
  ElMessage.success(`已切换至${request.request_type}请求类型`)
}

// WebSocket消息相关数据
const websocketMessageType = ref('text')
const websocketMessageContent = ref('')
const websocketBinaryFile = ref(null)
const websocketConnectionStatus = ref('disconnected') // disconnected, connecting, connected
const websocketConnection = ref(null)
const websocketMessages = ref([]) // WebSocket消息历史记录
const bodyType = ref('none')
const rawType = ref('json')
const formData = ref({})
const formUrlEncoded = ref({})
const rawBody = ref('')

const defaultProps = {
  children: 'children',
  label: 'name'
}

const collectionForm = reactive({
  name: '',
  description: '',
  parent: null
})

const editCollectionForm = reactive({
  id: null,
  name: '',
  description: '',
  parent: null
})

const collectionRules = {
  name: [{ required: true, message: '请输入集合名称', trigger: 'blur' }]
}

const hasBody = computed(() => {
  return selectedRequest.value && ['POST', 'PUT', 'PATCH'].includes(selectedRequest.value.method)
})

const responseBody = computed(() => {
  if (!response.value?.response_data) return ''
  
  try {
    if (response.value.response_data.json) {
      return JSON.stringify(response.value.response_data.json, null, 2)
    } else {
      return response.value.response_data.body || ''
    }
  } catch (e) {
    return response.value.response_data.body || ''
  }
})

const getStatusType = (status) => {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'warning'
  if (status >= 400) return 'danger'
  return 'info'
}

const loadProjects = async () => {
  try {
    const res = await api.get('/api-testing/projects/')
    projects.value = res.data.results || res.data
    if (projects.value.length > 0 && !selectedProject.value) {
      selectedProject.value = projects.value[0].id
      await onProjectChange()
    }
  } catch (error) {
    ElMessage.error('加载项目失败')
  }
}

// 保存上传中节点到localStorage
const saveUploadingNodes = () => {
  const uploadingNodes = collections.value.filter(node => node.type === 'uploading')
  localStorage.setItem(`uploadingNodes_${selectedProject.value}`, JSON.stringify(uploadingNodes))
}

// 从localStorage加载上传中节点
const loadUploadingNodes = () => {
  if (!selectedProject.value) return []
  const savedNodes = localStorage.getItem(`uploadingNodes_${selectedProject.value}`)
  return savedNodes ? JSON.parse(savedNodes) : []
}

// 停止上传中节点
const stopUploadingNode = (node) => {
  // 更新节点状态为失败
  node.status = 'failed'
  node.name = `已取消 - ${node.name.replace(/^上传中 - |^处理中 - /, '')}`
  
  // 更新localStorage
  saveUploadingNodes()
  
  // 显示提示信息
  ElMessage.success('上传任务已停止')
  
  // 刷新集合列表，获取最新状态
  setTimeout(() => {
    loadCollections()
  }, 500)
}

// 删除上传中节点
const removeUploadingNode = (node) => {
  // 从集合列表中移除节点
  const index = collections.value.indexOf(node)
  if (index > -1) {
    collections.value.splice(index, 1)
  }
  
  // 更新localStorage
  saveUploadingNodes()
  
  // 显示提示信息
  ElMessage.success('上传节点已删除')
}

const loadCollections = async (preserveExpandState = true) => {
  if (!selectedProject.value) return
  
  try {
    const res = await api.get('/api-testing/collections/', {
      params: { 
        project: selectedProject.value,
        page_size: 1000 // 获取所有集合以构建完整树
      }
    })
    const collectionsData = res.data.results || res.data
    console.log('Backend collections data:', collectionsData)
    
    // 构建树形结构，合并从localStorage加载的上传中节点
    const savedUploadingNodes = loadUploadingNodes()
    
    // 使用buildTree函数构建树形结构，确保集合正确显示
    let newCollections = buildTree(collectionsData)
    
    // 合并上传中节点
    collections.value = [...savedUploadingNodes, ...newCollections]
    flatCollections.value = collectionsData
    
    // 加载每个集合的请求
    await loadRequests()
    
    // 如果不保留展开状态，清空展开键
    if (!preserveExpandState) {
      expandedKeys.value = []
    }
    
    // 检查上传中的节点，如果已经完成或超过5分钟，自动移除
    const now = Date.now()
    const fiveMinutesAgo = now - 5 * 60 * 1000
    
    collections.value = collections.value.filter(node => {
      // 保留正常节点
      if (node.type !== 'uploading') return true
      
      // 保留上传中或处理中的节点
      if (node.status === 'uploading' || node.status === 'processing') return true
      
      // 移除超过5分钟的失败节点
      const nodeTime = new Date(node.created_at).getTime()
      if (nodeTime < fiveMinutesAgo) {
        return false
      }
      
      return true
    })
    
    // 保存更新后的上传中节点到localStorage
    saveUploadingNodes()
    
  } catch (error) {
    ElMessage.error('加载集合失败')
  }
}

const loadRequests = async () => {
  if (!selectedProject.value) return
  
  try {
    const res = await api.get('/api-testing/requests/', {
      params: { 
        project: selectedProject.value,
        page_size: 1000 // 获取所有请求以构建完整树
      }
    })
    const requests = res.data.results || res.data
    
    // 确保requests是数组
    const requestsArray = Array.isArray(requests) ? requests : []
    
    // 清空所有集合的子请求（递归清空）
    collections.value.forEach(collection => {
      clearCollectionChildren(collection)
    })
    
    // 创建一个请求映射，按集合ID分组
    const requestsByCollection = {}
    requestsArray.forEach(request => {
      const collectionId = request.collection
      if (!requestsByCollection[collectionId]) {
        requestsByCollection[collectionId] = []
      }
      requestsByCollection[collectionId].push(request)
    })
    
    // 递归地将请求添加到对应的集合中
    const addRequestsToCollection = (collection) => {
      const collectionId = collection.id
      const collectionRequests = requestsByCollection[collectionId] || []
      
      console.log(`Adding ${collectionRequests.length} requests to collection: ${collection.name} (ID: ${collectionId})`)
      
      // 将请求添加到集合的children中
      collectionRequests.forEach(request => {
        collection.children.push({
          ...request,
          type: 'request',
          name: request.name || '未命名请求'
        })
      })
      
      // 递归处理子集合
      if (collection.children && collection.children.length > 0) {
        collection.children.forEach(child => {
          if (child.type === 'collection') {
            addRequestsToCollection(child)
          }
        })
      }
    }
    
    // 遍历所有集合，添加请求
    collections.value.forEach(collection => {
      // 这里的集合可能是 root 集合，也可能是带 type 的 node
      addRequestsToCollection(collection)
    })
    
  } catch (error) {
    console.error('加载请求失败:', error)
    ElMessage.error(`加载请求失败: ${error.response?.data?.detail || error.message || '未知错误'}`)
  }
}

const clearCollectionChildren = (collection) => {
  if (collection.children) {
    // 保留上传中节点和集合节点
    // 集合节点可能来自后端，没有type字段，所以需要检查是否有children字段或者type是否为'collection'
    collection.children = collection.children.filter(child => 
      child.type === 'collection' || 
      child.type === 'uploading' || 
      child.children
    )
    collection.children.forEach(child => {
      // 只对集合节点递归处理，避免影响上传中节点
      if (child.type === 'collection' || child.children) {
        clearCollectionChildren(child)
      }
    })
  }
}

const loadEnvironments = async () => {
  try {
    // 获取全局环境 + 当前项目环境，不传递project参数
    const res = await api.get('/api-testing/environments/')
    const allEnvironments = res.data.results || res.data
    
    // 过滤全局环境和当前项目环境
    environments.value = allEnvironments.filter(env => 
      env.scope === 'GLOBAL' || 
      (env.scope === 'LOCAL' && (!selectedProject.value || env.project === selectedProject.value))
    )
  } catch (error) {
    ElMessage.error('加载环境失败')
  }
}

const buildTree = (items) => {
  const map = {} 
  const roots = []
  
  // 保留现有的上传中节点
  const existingUploadingNodes = collections.value.filter(node => node.type === 'uploading')
  
  // 构建新的树结构
  items.forEach(item => {
    // 检查item是否已经是处理过的节点（有children数组）
    if (!item.children) {
      item.children = []
    }
    // 确保类型正确
    if (!item.type) {
      item.type = 'collection'
    }
    map[item.id] = item
  })
  
  items.forEach(item => {
    if (item.parent && map[item.parent]) {
      // 避免重复添加
      if (!map[item.parent].children.includes(item)) {
        map[item.parent].children.push(item)
      }
    } else {
      // 如果没有父级，或者父级不在当前列表中，则作为根节点
      roots.push(item)
    }
  })
  
  // 合并现有上传中节点 - 保留所有上传中节点，不管它们是否在原数组中
  return [...existingUploadingNodes, ...roots]
}

const findCollectionById = (collections, id) => {
  for (const collection of collections) {
    // 进行类型转换，确保数字和字符串类型的id可以正确匹配
    if (collection.id === id || String(collection.id) === String(id)) return collection
    if (collection.children) {
      const found = findCollectionById(collection.children, id)
      if (found) return found
    }
  }
  return null
}

const onProjectChange = async () => {
  await Promise.all([loadCollections(false), loadEnvironments()])
}

const onNodeClick = (data) => {
  if (data.type === 'request') {
    console.log('onNodeClick - original data.headers:', data.headers)
    const convertedHeaders = convertObjectToKeyValueArray(data.headers || {})
    console.log('onNodeClick - converted headers:', convertedHeaders)
    
    selectedRequest.value = {
      ...data,
      params: convertObjectToKeyValueArray(data.params || {}),
      headers: convertedHeaders,
      body: data.body || {},
      auth: data.auth || {},
      assertions: data.assertions || [],
      extract_rules: data.extract_rules || []
    }
    
    console.log('onNodeClick - selectedRequest.value.headers:', selectedRequest.value.headers)
    
    // 解析body数据
    if (data.body) {
      if (data.body.type === 'json') {
        bodyType.value = 'json'
        rawBody.value = typeof data.body.data === 'string' ? data.body.data : JSON.stringify(data.body.data, null, 2)
      } else if (data.body.type === 'raw') {
        bodyType.value = 'json' // 兼容旧数据，统一转为json展示
        rawBody.value = typeof data.body.data === 'string' ? data.body.data : JSON.stringify(data.body.data, null, 2)
      } else if (data.body.type === 'form-data') {
        bodyType.value = 'form-data'
        formData.value = data.body.data || {}
      } else {
        bodyType.value = 'none'
        rawBody.value = ''
      }
    } else {
      bodyType.value = 'none'
      rawBody.value = ''
    }
    
    response.value = null
  }
}

const onNodeRightClick = (event, data) => {
  event.preventDefault()
  rightClickedNode.value = data
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  showContextMenu.value = true
  
  nextTick(() => {
    document.addEventListener('click', hideContextMenu)
  })
}

const hideContextMenu = () => {
  showContextMenu.value = false
  document.removeEventListener('click', hideContextMenu)
}

const startEditCollection = (collection) => {
  editingNodeId.value = collection.id
  editingNodeName.value = collection.name
  nextTick(() => {
    if (editInputRef.value) {
      editInputRef.value.focus()
    }
  })
}

const saveCollectionName = async () => {
  if (!editingNodeId.value || !editingNodeName.value.trim()) {
    cancelEdit()
    return
  }

  try {
    const collection = flatCollections.value.find(c => c.id === editingNodeId.value)
    if (!collection) {
      ElMessage.error('集合不存在')
      cancelEdit()
      return
    }

    const data = {
      name: editingNodeName.value.trim(),
      description: collection.description,
      parent: collection.parent,
      project: selectedProject.value
    }

    await api.put(`/api-testing/collections/${editingNodeId.value}/`, data)
    
    // 直接更新本地数据，避免重新加载
    const updateCollectionName = (collections, id, newName) => {
      for (const collection of collections) {
        // 只更新集合类型的节点，跳过接口类型的节点
        if (collection.type === 'collection' && collection.id === id) {
          collection.name = newName
          return true
        }
        if (collection.children && updateCollectionName(collection.children, id, newName)) {
          return true
        }
      }
      return false
    }
    
    // 更新树中的集合名称
    updateCollectionName(collections.value, editingNodeId.value, editingNodeName.value.trim())
    
    // 更新平均集合列表
    const flatCollection = flatCollections.value.find(c => c.id === editingNodeId.value)
    if (flatCollection) {
      flatCollection.name = editingNodeName.value.trim()
    }
    
    ElMessage.success('集合名称更新成功')
    cancelEdit()
  } catch (error) {
    ElMessage.error('更新失败')
    cancelEdit()
  }
}

const cancelEdit = () => {
  editingNodeId.value = null
  editingNodeName.value = ''
}

const onNodeExpand = (data) => {
  if (!expandedKeys.value.includes(data.id)) {
    expandedKeys.value.push(data.id)
  }
}

const onNodeCollapse = (data) => {
  const index = expandedKeys.value.indexOf(data.id)
  if (index > -1) {
    expandedKeys.value.splice(index, 1)
  }
}

const addRequest = () => {
  // 创建新请求
  const newRequest = {
    name: '新建请求',
    method: 'GET',
    url: '',
    headers: {},
    params: {},
    body: {},
    collection: rightClickedNode.value.type === 'collection' ? rightClickedNode.value.id : rightClickedNode.value.collection,
    type: 'request'
  }
  selectedRequest.value = newRequest
  hideContextMenu()
}

const addCollection = () => {
  collectionForm.parent = rightClickedNode.value.type === 'collection' ? rightClickedNode.value.id : null
  showCreateCollectionDialog.value = true
  hideContextMenu()
}

const editNode = () => {
  if (rightClickedNode.value.type === 'request') {
    // 使用与onNodeClick相同的逻辑来正确设置selectedRequest
    const data = rightClickedNode.value
    console.log('editNode - original data.headers:', data.headers)
    const convertedHeaders = convertObjectToKeyValueArray(data.headers || {})
    console.log('editNode - converted headers:', convertedHeaders)
    
    selectedRequest.value = {
      ...data,
      params: convertObjectToKeyValueArray(data.params || {}),
      headers: convertedHeaders,
      body: data.body || {},
      auth: data.auth || {}
    }
    
    console.log('editNode - selectedRequest.value.headers:', selectedRequest.value.headers)
    
    // 解析body数据
    if (data.body) {
      if (data.body.type === 'json') {
        bodyType.value = 'json'
        rawBody.value = typeof data.body.data === 'string' ? data.body.data : JSON.stringify(data.body.data, null, 2)
      } else if (data.body.type === 'raw') {
        bodyType.value = 'json' // 兼容旧数据
        rawBody.value = typeof data.body.data === 'string' ? data.body.data : JSON.stringify(data.body.data, null, 2)
      } else if (data.body.type === 'form-data') {
        bodyType.value = 'form-data'
        formData.value = data.body.data || {}
      } else {
        bodyType.value = 'none'
        rawBody.value = ''
      }
    } else {
      bodyType.value = 'none'
      rawBody.value = ''
    }
    
    response.value = null
  } else if (rightClickedNode.value.type === 'collection') {
    // 启动集合内联编辑
    startEditCollection(rightClickedNode.value)
  }
  hideContextMenu()
}

const deleteNode = async () => {
  // 优先使用右键点击的节点，如果没有（说明是在详情页点击的按钮），则使用当前选中的节点
  const targetNode = rightClickedNode.value || (selectedRequest.value ? { ...selectedRequest.value, type: 'request' } : null)
  
  if (!targetNode) {
    hideContextMenu()
    return
  }

  const nodeType = targetNode.type
  const nodeName = targetNode.name
  const nodeId = targetNode.id
  
  // 显示确认对话框
  try {
    await ElMessageBox.confirm(
      `确定要删除${nodeType === 'collection' ? '集合' : '接口'} "${nodeName}" 吗？${nodeType === 'collection' ? '删除集合会同时删除其中的所有接口。' : ''}`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    // 用户确认删除，执行删除操作
    if (nodeType === 'collection') {
      await deleteCollection(nodeId)
    } else if (nodeType === 'request') {
      await deleteRequest(nodeId)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除操作失败:', error)
      ElMessage.error('删除失败')
    }
  }
  
  hideContextMenu()
}

const deleteCollection = async (collectionId) => {
  try {
    await api.delete(`/api-testing/collections/${collectionId}/`)
    ElMessage.success('集合删除成功')
    
    // 如果当前选中的请求属于被删除的集合，清空选中状态
    if (selectedRequest.value && selectedRequest.value.collection === collectionId) {
      selectedRequest.value = null
      response.value = null
    }
    
    // 直接从树中移除集合，而不是重新加载
    const removeCollectionFromTree = (collections, id) => {
      for (let i = 0; i < collections.length; i++) {
        if (collections[i].id === id) {
          collections.splice(i, 1)
          return true
        }
        if (collections[i].children && removeCollectionFromTree(collections[i].children, id)) {
          return true
        }
      }
      return false
    }
    
    removeCollectionFromTree(collections.value, collectionId)
    
    // 从平集合列表中移除
    const index = flatCollections.value.findIndex(c => c.id === collectionId)
    if (index > -1) {
      flatCollections.value.splice(index, 1)
    }
    
    // 从展开键中移除
    const expandedIndex = expandedKeys.value.indexOf(collectionId)
    if (expandedIndex > -1) {
      expandedKeys.value.splice(expandedIndex, 1)
    }
    
  } catch (error) {
    ElMessage.error('删除集合失败')
    console.error('Delete collection error:', error)
  }
}

const deleteRequest = async (requestId) => {
  try {
    await api.delete(`/api-testing/requests/${requestId}/`)
    ElMessage.success('接口删除成功')
    
    // 如果当前选中的是被删除的请求，清空选中状态
    if (selectedRequest.value && selectedRequest.value.id === requestId) {
      selectedRequest.value = null
      response.value = null
    }
    
    // 直接从树中移除请求，而不是重新加载
    const removeRequestFromTree = (collections, requestId) => {
      for (const collection of collections) {
        if (collection.children) {
          const requestIndex = collection.children.findIndex(child => child.type === 'request' && child.id === requestId)
          if (requestIndex > -1) {
            collection.children.splice(requestIndex, 1)
            return true
          }
        }
        if (collection.children && removeRequestFromTree(collection.children, requestId)) {
          return true
        }
      }
      return false
    }
    
    removeRequestFromTree(collections.value, requestId)
    
  } catch (error) {
    ElMessage.error('删除接口失败')
    console.error('Delete request error:', error)
  }
}

const createCollection = async () => {
  try {
    const data = {
      ...collectionForm,
      project: selectedProject.value
    }
    const res = await api.post('/api-testing/collections/', data)
    const newCollection = res.data
    
    ElMessage.success('创建成功')
    showCreateCollectionDialog.value = false
    Object.assign(collectionForm, { name: '', description: '', parent: null })
    
    // 直接添加到本地数据，避免重新加载
    const newTreeNode = {
      ...newCollection,
      type: 'collection',
      children: []
    }
    
    // 添加到平集合列表
    flatCollections.value.push(newCollection)
    
    // 添加到树结构
    if (newCollection.parent) {
      // 找到父节点并添加
      const findAndAddToParent = (collections, parentId, newNode) => {
        for (const collection of collections) {
          if (collection.id === parentId) {
            if (!collection.children) collection.children = []
            collection.children.push(newNode)
            return true
          }
          if (collection.children && findAndAddToParent(collection.children, parentId, newNode)) {
            return true
          }
        }
        return false
      }
      
      findAndAddToParent(collections.value, newCollection.parent, newTreeNode)
      
      // 自动展开父节点
      if (!expandedKeys.value.includes(newCollection.parent)) {
        expandedKeys.value.push(newCollection.parent)
      }
    } else {
      // 添加到根级
      collections.value.push(newTreeNode)
    }
    
    // 自动展开新创建的集合
    if (!expandedKeys.value.includes(newCollection.id)) {
      expandedKeys.value.push(newCollection.id)
    }
    
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

// 断言相关方法
const addAssertion = () => {
  if (!selectedRequest.value.assertions) {
    selectedRequest.value.assertions = []
  }
  
  selectedRequest.value.assertions.push({
    name: `断言${selectedRequest.value.assertions.length + 1}`,
    type: '',
    expected: null,
    json_path: '',
    header_name: ''
  })
}

const removeAssertion = (index) => {
  if (selectedRequest.value.assertions) {
    selectedRequest.value.assertions.splice(index, 1)
  }
}

const onAssertionTypeChange = (assertion) => {
  // 重置断言参数
  assertion.expected = null
  assertion.json_path = ''
  assertion.header_name = ''
}

// 提取变量相关方法
const addExtractRule = () => {
  if (!selectedRequest.value.extract_rules) {
    selectedRequest.value.extract_rules = []
  }
  
  selectedRequest.value.extract_rules.push({
    variable_name: '',
    type: '',
    json_path: '',
    header_name: '',
    pattern: ''
  })
}

const removeExtractRule = (index) => {
  if (selectedRequest.value.extract_rules) {
    selectedRequest.value.extract_rules.splice(index, 1)
  }
}

const onExtractRuleTypeChange = (rule) => {
  // 重置提取规则参数
  rule.json_path = ''
  rule.header_name = ''
  rule.pattern = ''
}

// WebSocket消息处理函数
const handleWebSocketFileUpload = (file) => {
  websocketBinaryFile.value = file.raw
  return false
}

const clearWebSocketBinaryFile = () => {
  websocketBinaryFile.value = null
}

const sendWebSocketMessage = () => {
  if (websocketConnectionStatus.value !== 'connected') {
    ElMessage.warning('请先建立WebSocket连接')
    return
  }
  
  if (!websocketConnection.value) {
    ElMessage.error('WebSocket连接不存在')
    return
  }
  
  try {
    let messageToSend = ''
    
    if (websocketMessageType.value === 'text' || websocketMessageType.value === 'json') {
      messageToSend = websocketMessageContent.value
    } else if (websocketMessageType.value === 'binary' && websocketBinaryFile.value) {
      // 对于二进制文件，需要读取文件内容
      const reader = new FileReader()
      reader.onload = (e) => {
        websocketConnection.value.send(e.target.result)
        addWebSocketMessage('sent', '[二进制数据]')
        ElMessage.success('二进制消息已发送')
      }
      reader.onerror = () => {
        ElMessage.error('读取文件失败')
      }
      reader.readAsArrayBuffer(websocketBinaryFile.value)
      return
    } else {
      ElMessage.warning('请输入消息内容或选择文件')
      return
    }
    
    websocketConnection.value.send(messageToSend)
    addWebSocketMessage('sent', messageToSend)
    ElMessage.success('消息已发送')
    
  } catch (error) {
    const errorMsg = '发送消息失败: ' + error.message
    addWebSocketMessage('error', errorMsg)
    ElMessage.error(errorMsg)
  }
}

const clearWebSocketMessage = () => {
  websocketMessageContent.value = ''
  websocketBinaryFile.value = null
  websocketMessageType.value = 'text'
}

// WebSocket消息历史记录相关方法
const addWebSocketMessage = (type, content) => {
  const timestamp = new Date().toLocaleTimeString()
  websocketMessages.value.push({
    type,
    content,
    timestamp
  })
}

const clearWebSocketMessages = () => {
  websocketMessages.value = []
}

const isJsonString = (str) => {
  try {
    JSON.parse(str)
    return true
  } catch (e) {
    return false
  }
}

const formatJson = (str) => {
  try {
    return JSON.stringify(JSON.parse(str), null, 2)
  } catch (e) {
    return str
  }
}

// WebSocket连接管理函数
const toggleWebSocketConnection = () => {
  if (websocketConnectionStatus.value === 'disconnected') {
    connectWebSocket()
  } else {
    disconnectWebSocket()
  }
}

const connectWebSocket = () => {
  if (!selectedRequest.value || !selectedRequest.value.url) {
    ElMessage.warning('请输入WebSocket连接地址')
    return
  }
  
  websocketConnectionStatus.value = 'connecting'
  
  try {
    // 替换环境变量
    let url = selectedRequest.value.url
    if (selectedEnvironment.value) {
      const env = environments.value.find(e => e.id === selectedEnvironment.value)
      if (env && env.variables) {
        Object.entries(env.variables).forEach(([key, value]) => {
          url = url.replace(`{{${key}}}`, value.currentValue || value.initialValue || '')
        })
      }
    }
    
    // 创建WebSocket连接
    websocketConnection.value = new WebSocket(url)
    
    websocketConnection.value.onopen = () => {
      websocketConnectionStatus.value = 'connected'
      // 添加连接成功的特殊消息
      addWebSocketMessage('connected', `Websocket已连接至${url}`)
      ElMessage.success('WebSocket连接成功')
    }
    
    websocketConnection.value.onmessage = (event) => {
      // 处理接收到的消息
      console.log('WebSocket message received:', event.data)
      addWebSocketMessage('received', event.data)
      ElMessage.info('收到WebSocket消息')
    }
    
    websocketConnection.value.onclose = () => {
      websocketConnectionStatus.value = 'disconnected'
      addWebSocketMessage('info', 'WebSocket连接已关闭')
      ElMessage.info('WebSocket连接已关闭')
    }
    
    websocketConnection.value.onerror = (error) => {
      websocketConnectionStatus.value = 'disconnected'
      const errorMsg = 'WebSocket连接错误: ' + (error.message || '连接失败')
      addWebSocketMessage('error', errorMsg)
      ElMessage.error(errorMsg)
    }
    
  } catch (error) {
    websocketConnectionStatus.value = 'disconnected'
    const errorMsg = 'WebSocket连接失败: ' + error.message
    addWebSocketMessage('error', errorMsg)
    ElMessage.error(errorMsg)
  }
}

const disconnectWebSocket = () => {
  if (websocketConnection.value) {
    websocketConnection.value.close()
    websocketConnection.value = null
  }
  websocketConnectionStatus.value = 'disconnected'
  // 清空消息历史
  clearWebSocketMessages()
}

const createEmptyRequest = async () => {
  // 检查是否有选中的项目
  if (!selectedProject.value) {
    ElMessage.warning('请先选择一个项目')
    return
  }
  
  // 检查是否有可用的集合
  if (!flatCollections.value || flatCollections.value.length === 0) {
    ElMessage.warning('请先创建一个集合')
    return
  }
  
  // 使用第一个集合作为默认集合
  const defaultCollection = flatCollections.value[0]
  
  // 获取当前项目信息
  const currentProject = projects.value.find(p => p.id === selectedProject.value)
  const isWebSocketProject = currentProject && currentProject.project_type === 'WEBSOCKET'
  
  saving.value = true
  try {
    // 创建一个空的接口，参照"获取宠物列表"的样式
    const data = {
      name: '新建接口',
      method: isWebSocketProject ? 'CONNECT' : 'GET',
      url: isWebSocketProject ? 'ws://{{host}}/websocket' : '{{base_url}}/api/new-endpoint',
      description: '',
      collection: defaultCollection.id,
      project: selectedProject.value,
      request_type: isWebSocketProject ? 'WEBSOCKET' : 'HTTP',
      params: {},
      headers: isWebSocketProject ? {} : {
        'Content-Type': 'application/json'
      },
      body: {},
      auth: {},
      pre_request_script: '',
      post_request_script: ''
    }
    
    const res = await api.post('/api-testing/requests/', data)
    ElMessage.success('创建成功')
    
    // 重新加载集合和请求
    await Promise.all([loadCollections(), loadRequests()])
    
    // 自动选中新创建的请求并进入编辑状态
    selectedRequest.value = {
      id: res.data.id,
      name: res.data.name,
      method: res.data.method,
      url: res.data.url,
      description: res.data.description || '',
      collection: res.data.collection,
      project: res.data.project,
      request_type: res.data.request_type,
      params: convertObjectToKeyValueArray(res.data.params || {}),
      headers: convertObjectToKeyValueArray(res.data.headers || {}),
      body: res.data.body || {},
      auth: res.data.auth || {},
      pre_request_script: res.data.pre_request_script || '',
      post_request_script: res.data.post_request_script || ''
    }
    
    // 默认进入params标签页
    activeTab.value = 'params'
    
    // 初始化body相关变量
    bodyType.value = 'none'
    rawType.value = 'json'
    formData.value = {}
    formUrlEncoded.value = {}
    rawBody.value = ''
    
  } catch (error) {
    ElMessage.error('创建失败')
    console.error('Create request error:', error)
  } finally {
    saving.value = false
  }
}

const sendRequest = async () => {
  if (!selectedRequest.value) return
  
  // 检查是否为WebSocket接口
  if (selectedRequest.value.request_type === 'WEBSOCKET') {
    ElMessage.warning('WebSocket接口暂不支持在此界面直接执行，请使用专门的WebSocket测试工具')
    return
  }
  
  // 检查是否选择了环境
  if (!selectedEnvironment.value) {
    ElMessage.warning('请选择环境')
    return
  }
  
  sending.value = true
  try {
    // 发送请求前先自动保存当前的修改
    await saveRequest()
    
    // 准备请求体数据
    let bodyData = {}
    if (hasBody.value) {
      if (bodyType.value === 'json' && rawBody.value) {
        try {
          bodyData = {
            type: 'json',
            data: JSON.parse(rawBody.value)
          }
        } catch (e) {
          bodyData = {
            type: 'raw',
            data: rawBody.value
          }
        }
      } else if (bodyType.value === 'form-data') {
        bodyData = {
          type: 'form-data',
          data: formData.value
        }
      }
    }
    
    const requestData = {
      ...selectedRequest.value,
      params: convertKeyValueArrayToObject(selectedRequest.value.params || []),
      headers: selectedRequest.value.headers,  // 现在直接使用数组格式
      body: bodyData,
      environment_id: selectedEnvironment.value,
      engine: executionEngine.value
    }
    
    const res = await api.post(`/api-testing/requests/${selectedRequest.value.id}/execute/`, requestData)
    response.value = res.data
    ElMessage.success('请求发送成功')
  } catch (error) {
    ElMessage.error('请求发送失败')
    if (error.response?.data) {
      response.value = error.response.data
    }
  } finally {
    sending.value = false
  }
}

const onHeadersUpdate = (newHeaders) => {
  console.log('Headers updated:', newHeaders)
  if (selectedRequest.value) {
    // 强制更新整个selectedRequest对象以触发响应式更新
    selectedRequest.value = {
      ...selectedRequest.value,
      headers: newHeaders
    }
    console.log('Updated selectedRequest.headers:', selectedRequest.value.headers)
  }
}

const saveRequest = async () => {
  if (!selectedRequest.value) return
  
  saving.value = true
  try {
    // 准备保存的数据
    let bodyData = {}
    if (hasBody.value && bodyType.value === 'json' && rawBody.value) {
      try {
        bodyData = {
          type: 'json',
          data: JSON.parse(rawBody.value)
        }
      } catch (e) {
        bodyData = {
          type: 'raw',
          data: rawBody.value
        }
      }
    } else if (hasBody.value && bodyType.value === 'form-data') {
      bodyData = {
        type: 'form-data',
        data: formData.value
      }
    }
    
    // 直接从KeyValueEditor组件获取当前headers（完整数组格式）
    let finalHeaders = []
    console.log('headersEditorRef.value:', headersEditorRef.value)
    if (headersEditorRef.value) {
      // 直接访问KeyValueEditor的rows数据，保持完整的数组格式
      const rows = headersEditorRef.value.rows || []
      console.log('Direct access to headers rows:', rows)
      finalHeaders = rows
        .filter(row => row.enabled && row.key && row.key.trim())
        .map(row => ({
          key: row.key.trim(),
          value: row.value || '',
          description: row.description || '',
          enabled: row.enabled !== false
        }))
      console.log('Final headers array format:', finalHeaders)
    } else {
      console.log('headersEditorRef.value is null or undefined')
      // 如果无法获取，使用selectedRequest中的headers
      if (selectedRequest.value.headers && Array.isArray(selectedRequest.value.headers)) {
        finalHeaders = selectedRequest.value.headers.filter(item => item.enabled && item.key)
      }
    }
    
    console.log('Final headers to save:', finalHeaders)
    console.log('selectedRequest.value.params:', selectedRequest.value.params)
    
    const data = {
      ...selectedRequest.value,
      params: convertKeyValueArrayToObject(selectedRequest.value.params || []),
      headers: finalHeaders,  // 保存完整的数组格式，包含description
      body: bodyData
    }
    
    console.log('Data being sent to backend:', data)
    
    console.log('Final save data:', data)
    console.log('Headers being saved:', data.headers)
    
    if (selectedRequest.value.id) {
      const res = await api.put(`/api-testing/requests/${selectedRequest.value.id}/`, data)
      const updatedRequest = res.data
      
      // 更新树中的请求完整数据，避免重新加载
      const updateRequestInTree = (collections, requestId, newData) => {
        for (const collection of collections) {
          if (collection.children) {
            const index = collection.children.findIndex(child => child.type === 'request' && child.id === requestId)
            if (index > -1) {
              // 保留 type 属性，合并其他新数据
              collection.children[index] = {
                ...newData,
                type: 'request'
              }
              return true
            }
          }
          if (collection.children && updateRequestInTree(collection.children, requestId, newData)) {
            return true
          }
        }
        return false
      }
      
      updateRequestInTree(collections.value, selectedRequest.value.id, updatedRequest)
    } else {
      const res = await api.post('/api-testing/requests/', data)
      selectedRequest.value.id = res.data.id
      // 新建的请求需要重新加载树以显示新请求
      await loadCollections()
    }
    
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const onBodyTypeChange = () => {
  if (bodyType.value === 'raw') {
    rawType.value = 'json'
    rawBody.value = ''
  }
}

const formatResponse = () => {
  // 格式化响应内容
  try {
    if (response.value?.response_data?.json) {
      response.value.response_data.body = JSON.stringify(response.value.response_data.json, null, 2)
    }
  } catch (e) {
    ElMessage.error('格式化失败')
  }
}

const copyResponse = () => {
  if (responseBody.value) {
    navigator.clipboard.writeText(responseBody.value)
    ElMessage.success('已复制到剪贴板')
  }
}

const copyCurl = () => {
  if (!selectedRequest.value) return
  
  const { method, url, headers, params, body } = selectedRequest.value
  let curl = `curl --location --request ${method} '${url}'`
  
  // Add params if any
  const queryParams = convertKeyValueArrayToObject(params)
  if (Object.keys(queryParams).length > 0) {
    const searchParams = new URLSearchParams(queryParams)
    curl = curl.replace(url, `${url}?${searchParams.toString()}`)
  }
  
  // Add headers
  if (Array.isArray(headers)) {
    headers.forEach(h => {
      if (h.enabled && h.key) {
        curl += ` \\\n--header '${h.key}: ${h.value}'`
      }
    })
  }
  
  // Add body
  if (hasBody.value && bodyType.value === 'raw' && rawBody.value) {
    curl += ` \\\n--data-raw '${rawBody.value.replace(/'/g, "'\\''")}'`
  }
  
  navigator.clipboard.writeText(curl)
  ElMessage.success('cURL 已复制到剪贴板')
}

const handleGenerateSqlInline = async (assertion) => {
  if (!assertion.prompt) {
    ElMessage.warning('请输入需求描述')
    return
  }
  
  if (!assertion.db_config_id) {
    ElMessage.warning('请先选择数据库配置')
    return
  }
  
  assertion.generating = true
  try {
    const res = await generateSql({
      prompt: assertion.prompt,
      db_config_id: assertion.db_config_id
    })
    
    if (res.data && res.data.sql) {
      assertion.sql = res.data.sql
      ElMessage.success('SQL生成成功')
    } else {
      ElMessage.error('生成失败：未返回SQL')
    }
  } catch (error) {
    ElMessage.error('生成SQL失败: ' + (error.response?.data?.error || error.message))
  } finally {
    assertion.generating = false
  }
}

const showGenerateSqlDialog = ref(false)
const generateSqlPrompt = ref('')
const generatingSql = ref(false)
const currentAssertion = ref(null)

const openGenerateSqlDialog = (assertion) => {
  currentAssertion.value = assertion
  generateSqlPrompt.value = ''
  showGenerateSqlDialog.value = true
}

const handleGenerateSql = async () => {
  if (!generateSqlPrompt.value) {
    ElMessage.warning('请输入需求描述')
    return
  }
  
  if (!currentAssertion.value || !currentAssertion.value.db_config_id) {
    ElMessage.warning('请先选择数据库配置')
    return
  }
  
  generatingSql.value = true
  try {
    const res = await generateSql({
      prompt: generateSqlPrompt.value,
      db_config_id: currentAssertion.value.db_config_id
    })
    
    if (res.data && res.data.sql) {
      currentAssertion.value.sql = res.data.sql
      ElMessage.success('SQL生成成功')
      showGenerateSqlDialog.value = false
    } else {
      ElMessage.error('生成失败：未返回SQL')
    }
  } catch (error) {
    ElMessage.error('生成SQL失败: ' + (error.response?.data?.error || error.message))
  } finally {
    generatingSql.value = false
  }
}

const loadVannaConfigs = async () => {
  try {
    const res = await getVannaConfigs({ page_size: 100 })
    vannaConfigs.value = res.data.results || res.data
  } catch (error) {
    console.error('加载数据库配置失败', error)
  }
}

onMounted(() => {
  loadProjects()
  loadVannaConfigs()
})

// 导入相关方法
const handleFileChange = (file) => {
  // 保存选中的文件
  selectedFile.value = file.raw
  importForm.file = file.raw
  return false
}

const beforeUpload = (file) => {
  // 验证文件类型
  const allowedExtensions = ['.json', '.yaml', '.yml', '.jmx', '.xlsx', '.xls', '.csv']
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowedExtensions.includes(fileExtension)) {
    ElMessage.error('只支持上传JSON/YAML/JMX/Excel/CSV格式的文件')
    return false
  }
  
  // 验证文件大小
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过50MB')
    return false
  }
  
  return true
}

const handleImport = async () => {
  if (!importFormRef.value) return
  
  // 验证表单
  await importFormRef.value.validate().then(async () => {
    if (!selectedProject.value) {
      ElMessage.error('请先选择项目')
      return
    }
    
    if (!selectedFile.value) {
      ElMessage.error('请选择要导入的文件')
      return
    }
    
    // 添加上传中状态的临时节点
    const uploadNode = {
      id: `uploading-${Date.now()}`,
      name: `上传中 - ${selectedFile.value.name}`,
      type: 'uploading',
      status: 'uploading',
      children: [],
      parent: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    
    // 添加到树的根节点
    collections.value.push(uploadNode)
    
    // 保存上传中节点到localStorage
    saveUploadingNodes()
    
    importing.value = true
    
    try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)
        formData.append('format', importForm.format)
        formData.append('mode', importForm.mode)
        
        // 调用后端同步导入API，添加进度监听
        // 使用空路径，让后端根据文件内容确定项目
        const res = await api.post(`/api-testing/projects/import/`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          // 添加进度监听
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
              // 更新上传节点的名称，显示进度
              uploadNode.name = `上传中 - ${selectedFile.value.name} (${percent}%)`
              // 保存更新后的上传中节点到localStorage
              saveUploadingNodes()
            }
          }
        })
      
        ElMessage.success('导入成功')
        showImportDialog.value = false
        
        // 移除上传中节点
        const index = collections.value.indexOf(uploadNode)
        if (index > -1) {
          collections.value.splice(index, 1)
        }
        
        // 更新localStorage，移除上传中节点
        saveUploadingNodes()
        
        // 清空导入表单
        importForm.format = 'postman'
        importForm.mode = 'overwrite'
        importForm.file = null
        selectedFile.value = null
        if (uploadRef.value) {
          uploadRef.value.clearFiles()
        }
        
        // 更新选中的项目
        const newProjectId = res.data.project_id
        if (newProjectId && newProjectId !== selectedProject.value) {
          selectedProject.value = newProjectId
        }
        
        // 刷新项目列表和集合列表
        await loadProjects()
        await loadCollections()
        await loadEnvironments()
    } catch (error) {
      console.error('导入任务提交失败:', error)
      ElMessage.error(`导入任务提交失败: ${error.response?.data?.error || error.message || '未知错误'}`)
      
      // 更新节点状态为失败
      uploadNode.name = `上传失败 - ${selectedFile.value.name}`
      uploadNode.status = 'failed'
      uploadNode.error = error.response?.data?.error || error.message || '未知错误'
      
      // 保存更新后的上传中节点到localStorage
      saveUploadingNodes()
      
      // 刷新集合列表，获取最新状态
      setTimeout(() => {
        loadCollections()
      }, 500)
    } finally {
      importing.value = false
    }
  }).catch((error) => {
    console.error('表单验证失败:', error)
  })
}

onBeforeUnmount(() => {
  // 清理WebSocket连接
  if (websocketConnection.value) {
    websocketConnection.value.close()
    websocketConnection.value = null
  }
})
</script>

<style scoped>
/* 页面整体布局 */
.interface-manage-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: white;
  overflow: hidden;
}

.interface-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
  height: 100%;
}

.sidebar {
  width: 300px;
  border-right: 1px solid #e4e7ed;
  background: #fcfcfc;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 12px;
  background: white;
}

.sidebar-toolbar {
  padding: 8px 12px;
  display: flex;
  gap: 8px;
  align-items: center;
  background: white;
  border-bottom: 1px solid #f0f0f0;
}

.search-input {
  flex: 1;
}

.toolbar-actions {
  flex-shrink: 0;
}

.collection-tree-container {
  flex: 1;
  overflow: auto;
  padding: 8px 0;
}

.custom-tree {
  background: transparent;
}

.custom-tree :deep(.el-tree-node__content) {
  height: 32px;
  margin: 2px 8px;
  border-radius: 4px;
}

.custom-tree :deep(.el-tree-node__content:hover) {
  background-color: #f0f2f5;
}

.custom-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background-color: #e6f7ff;
  color: #1890ff;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  overflow: hidden;
  font-size: 13px;
}

.tree-node.is-active {
  color: #1890ff;
  font-weight: 500;
}

.folder-icon {
  color: #ffca28;
  font-size: 14px;
}

.method-indicator {
  font-size: 10px;
  font-weight: bold;
  min-width: 32px;
  text-align: center;
  padding: 0 4px;
  border-radius: 2px;
  text-transform: uppercase;
  transform: scale(0.9);
}

.method-indicator.get { color: #61affe; background: rgba(97, 175, 254, 0.1); }
.method-indicator.post { color: #49cc90; background: rgba(73, 204, 144, 0.1); }
.method-indicator.put { color: #fca130; background: rgba(252, 161, 48, 0.1); }
.method-indicator.delete { color: #f93e3e; background: rgba(249, 62, 62, 0.1); }
.method-indicator.patch { color: #50e3c2; background: rgba(80, 227, 194, 0.1); }

.node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uploading-node {
  color: #909399;
  font-style: italic;
}

.request-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
}

.request-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.request-header-area {
  padding: 12px 20px;
  background: white;
  border-bottom: 1px solid #f0f0f0;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.title-container {
  flex: 1;
  margin-right: 20px;
}

.interface-title-input :deep(.el-input__wrapper) {
  box-shadow: none;
  padding: 0;
}

.interface-title-input :deep(.el-input__inner) {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.env-selector {
  width: 140px;
}

.url-bar {
  display: flex;
  gap: 12px;
}

.method-url-group {
  flex: 1;
  display: flex;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.method-url-group:focus-within {
  border-color: #409eff;
}

.method-selector-compact {
  width: 100px;
}

.method-selector-compact :deep(.el-input__wrapper) {
  box-shadow: none;
  background: #f5f7fa;
  border-radius: 0;
}

.method-selector-compact :deep(.el-input__inner) {
  font-weight: bold;
  text-align: center;
}

.method-selector-compact.get :deep(.el-input__inner) { color: #61affe; }
.method-selector-compact.post :deep(.el-input__inner) { color: #49cc90; }
.method-selector-compact.put :deep(.el-input__inner) { color: #fca130; }
.method-selector-compact.delete :deep(.el-input__inner) { color: #f93e3e; }

.url-input-compact :deep(.el-input__wrapper) {
  box-shadow: none;
}

.send-button-large {
  width: 100px;
  height: 32px;
  font-weight: bold;
}

.mode-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mode-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 20px;
  background: white;
  border-bottom: 1px solid #f0f0f0;
}

.mode-tabs :deep(.el-tabs__item) {
  height: 40px;
  line-height: 40px;
  font-size: 14px;
}

.mode-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.mode-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: 3px;
}

.mode-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.mode-tabs :deep(.el-tab-pane) {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 设计模式样式 */
.design-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 24px;
  background: white;
}

.design-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 4px solid #409eff;
}

.design-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.design-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.design-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
  padding: 20px 0;
}

.tab-pane-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.body-editor-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rule-card {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.rule-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.rule-header {
  padding: 8px 12px;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rule-name-input {
  width: 200px;
}

.rule-name-input :deep(.el-input__wrapper) {
  box-shadow: none;
  background: transparent;
}

.rule-body {
  padding: 12px;
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 调试面板样式 */
.debug-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #fcfcfc;
}

.debug-request-pane, .debug-response-pane {
  display: flex;
  flex-direction: column;
  background: white;
  margin: 8px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  box-shadow: none;
  overflow: hidden;
}

.debug-request-pane {
  flex: 0 0 auto;
  max-height: 40%;
}

.debug-response-pane {
  flex: 1;
}

.pane-header {
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
  font-weight: bold;
  color: #606266;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.compact-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 16px;
  background: white;
}

.compact-tabs :deep(.el-tabs__content) {
  padding: 12px 16px;
  overflow-y: auto;
}

.debug-body-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.monospaced-input :deep(.el-textarea__inner) {
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 12px;
  background: #fafafa;
}

.response-meta-tags {
  display: flex;
  gap: 8px;
}

.response-content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.response-body-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.response-viewer {
  flex: 1;
  background: #fcfcfc;
  border-radius: 4px;
  overflow: auto;
  padding: 12px;
  border: 1px solid #f0f0f0;
}

.code-block {
  margin: 0;
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
}

.response-headers-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-item {
  display: flex;
  font-size: 12px;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.header-key {
  font-weight: bold;
  color: #606266;
  margin-right: 8px;
  min-width: 120px;
}

.header-value {
  color: #303133;
  word-break: break-all;
}

.assertion-results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assertion-result-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
}

.assertion-result-row.passed {
  background: #f0f9eb;
  color: #67c23a;
}

.assertion-result-row.failed {
  background: #fef0f0;
  color: #f56c6c;
}

.response-viewer {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
  min-height: 200px;
}

.request-info-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.request-detail-section {
  margin-bottom: 20px;
}

.detail-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-label {
  font-size: 13px;
  color: #909399;
  width: 70px;
  flex-shrink: 0;
}

.info-value {
  font-family: monospace;
}

.code-block.small {
  font-size: 12px;
  padding: 12px;
  max-height: 300px;
}

.response-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.extract-list {
  padding: 10px 0;
}

.extract-item {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
  background: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
}

.response-section {
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 200px;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-shrink: 0;
}

.response-info {
  display: flex;
  gap: 10px;
  align-items: center;
}

.response-time {
  color: #909399;
  font-size: 12px;
}

.response-body {
  position: relative;
}

.response-actions {
  margin-bottom: 10px;
}

.response-content {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}

.response-headers {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 4px;
}

.header-row {
  margin-bottom: 5px;
  font-size: 12px;
}

/* 断言样式 */
.assertions-editor {
  padding: 10px;
}

.assertions-header {
  margin-bottom: 15px;
}

.assertion-item {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 15px;
  background: #fafafa;
}

.assertion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
}

.assertion-name {
  flex: 1;
  margin-right: 10px;
}

.assertion-config {
  padding: 10px;
}

.assertion-config .el-select {
  width: 100%;
  margin-bottom: 10px;
}

.assertion-params {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assertion-input {
  margin-bottom: 5px;
}

.no-assertions {
  text-align: center;
  padding: 30px;
  color: #909399;
}

/* WebSocket信息样式 */
.websocket-info-section {
  padding: 20px;
}

.websocket-tips {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.websocket-tips h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.websocket-tips ul {
  margin: 0;
  padding-left: 20px;
}

.websocket-tips li {
  margin-bottom: 5px;
}

/* WebSocket消息样式 */
.message-container {
  padding: 15px;
}

.message-input-section {
  margin-bottom: 20px;
}

.uploaded-file {
  margin-top: 10px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* WebSocket响应区域样式 */
.websocket-response-section {
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
}

.websocket-response-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
}

.websocket-messages {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 15px;
}

.websocket-message-item {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 10px;
  background-color: #fafafa;
}

.websocket-message-item.sent {
  border-left: 3px solid #409eff;
}

.websocket-message-item.received {
  border-left: 3px solid #67c23a;
}

.websocket-message-item.info {
  border-left: 3px solid #909399;
}

.websocket-message-item.error {
  border-left: 3px solid #f56c6c;
}

.websocket-message-item.connected {
  border-left: 3px solid #67c23a;
}

.message-header {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 12px;
}

.message-type.sent {
  color: #409eff;
  font-weight: bold;
}

.message-type.received {
  color: #67c23a;
  font-weight: bold;
}

.message-type.info {
  color: #909399;
  font-weight: bold;
}

.message-type.error {
  color: #f56c6c;
  font-weight: bold;
}

.message-type.connected {
  color: #67c23a;
  font-weight: bold;
}

.message-time {
  color: #909399;
}

.message-content {
  padding: 10px 12px;
}

.message-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
}

/* WebSocket URL样式 */
.websocket-url {
  flex: 1;
}

/* 断言结果样式 */
.assertions-results {
  padding: 15px;
}

.assertion-result-item {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 10px;
  padding: 10px;
}

.assertion-result-item.passed {
  border-color: #67c23a;
  background-color: #f0f9ff;
}

.assertion-result-item.failed {
  border-color: #f56c6c;
  background-color: #fef0f0;
}

.assertion-result-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.assertion-name {
  margin-left: 8px;
  font-weight: 500;
}

.assertion-result-details {
  padding-left: 24px;
  font-size: 12px;
}

.result-row {
  display: flex;
  margin-bottom: 4px;
}

.label {
  width: 50px;
  font-weight: 500;
}

.value {
  flex: 1;
  word-break: break-all;
}

.value.error {
  color: #f56c6c;
}

/* 提取变量样式 */
.extract-variables-editor {
  padding: 10px;
}

.extract-variables-header {
  margin-bottom: 15px;
}

.extract-rules-list {
  padding: 10px;
}

.extract-rule-item {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 15px;
  background: #fafafa;
}

.extract-rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
}

.extract-rule-name {
  flex: 1;
  margin-right: 10px;
}

.extract-rule-config {
  padding: 10px;
}

.extract-rule-config .el-select {
  width: 100%;
  margin-bottom: 10px;
}

.extract-rule-params {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.extract-rule-input {
  margin-bottom: 5px;
}

.no-extract-rules {
  text-align: center;
  padding: 30px;
  color: #909399;
}

.context-menu {
  position: fixed;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 5px 0;
  margin: 0;
  list-style: none;
  z-index: 9999;
}

.context-menu li {
  padding: 8px 15px;
  cursor: pointer;
  font-size: 14px;
}

.context-menu li:hover {
  background: #f5f7fa;
}

/* 上传中节点样式 */
.uploading-node {
  font-style: italic;
}

.status-uploading {
  color: #409EFF;
}

.status-processing {
  color: #E6A23C;
}

.status-failed {
  color: #F56C6C;
}

.uploading-icon {
  color: #409EFF;
  animation: spin 1.5s linear infinite;
}

.processing-icon {
  color: #E6A23C;
  animation: spin 1.5s linear infinite;
}

.failed-icon {
  color: #F56C6C;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
