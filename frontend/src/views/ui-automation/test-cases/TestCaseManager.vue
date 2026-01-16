<template>
  <div class="test-case-manager">
    <div class="page-header">
      <h1 class="page-title">测试用例管理</h1>
      <div class="header-actions">
        <el-select v-model="projectId" placeholder="选择项目" style="width: 200px; margin-right: 15px" @change="onProjectChange">
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建测试用例
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <!-- 左侧：测试用例列表 -->
      <div class="left-panel">
        <div class="panel-header">
          <h3>测试用例列表</h3>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索测试用例..."
            clearable
            size="small"
            style="width: 200px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <div class="test-case-list">
          <div
            v-for="testCase in filteredTestCases"
            :key="testCase.id"
            class="test-case-item"
            :class="{ active: selectedTestCase?.id === testCase.id }"
            @click="selectTestCase(testCase)"
          >
            <div class="case-header">
              <div class="case-info">
                <h4 class="case-name">{{ testCase.name }}</h4>
                <p class="case-description">{{ testCase.description || '暂无描述' }}</p>
              </div>
              <div class="case-actions">
                <el-button size="small" text @click.stop="runTestCase(testCase)">
                  <el-icon><CaretRight /></el-icon>
                </el-button>
                <el-button size="small" text @click.stop="editTestCase(testCase)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button size="small" text @click.stop="copyTestCase(testCase)">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
                <el-button size="small" text type="danger" @click.stop="deleteTestCase(testCase)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <div class="case-meta">
              <!-- 移除状态显示 -->
              <span class="step-count">{{ testCase.steps?.length || 0 }} 步骤</span>
              <span class="update-time">{{ formatTime(testCase.updated_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：测试用例详情和步骤编辑 -->
      <div class="right-panel">
        <div v-if="selectedTestCase" class="test-case-detail">
          <div class="detail-header">
            <h3>{{ selectedTestCase.name }}</h3>
            <div class="detail-actions">
              <el-button size="small" @click="addStep">
                <el-icon><Plus /></el-icon>
                添加步骤
              </el-button>
              <el-button size="small" type="primary" @click="saveTestCase">
                <el-icon><Check /></el-icon>
                保存
              </el-button>
              <el-select v-model="selectedEngine" placeholder="选择引擎" size="small" style="width: 130px; margin-right: 10px">
                <el-option label="Playwright" value="playwright" />
                <el-option label="Selenium" value="selenium" />
                <el-option label="Appium" value="appium" />
              </el-select>
              <el-select v-model="selectedBrowser" placeholder="选择浏览器" size="small" style="width: 120px; margin-right: 10px" v-show="selectedEngine !== 'appium'">
                <el-option label="Chrome" value="chrome" />
                <el-option label="Firefox" value="firefox" />
                <el-option label="Safari" value="safari" />
                <el-option label="Edge" value="edge" />
              </el-select>
              <el-select v-model="headlessMode" placeholder="运行模式" size="small" style="width: 110px; margin-right: 10px" v-show="selectedEngine !== 'appium'">
                <el-option label="有头模式" :value="false" />
                <el-option label="无头模式" :value="true" />
              </el-select>
              <el-button size="small" type="success" @click="runTestCase(selectedTestCase)" :loading="isRunning">
                <el-icon v-if="!isRunning"><CaretRight /></el-icon>
                {{ isRunning ? '执行中...' : '运行' }}
              </el-button>
              <el-button size="small" v-if="executionResult" @click="toggleView">
                <el-icon><component :is="showSteps ? 'View' : 'Edit'" /></el-icon>
                {{ showSteps ? '查看执行结果' : '编辑步骤' }}
              </el-button>
              <el-button
                size="small"
                v-if="executionResult && !showSteps"
                type="success"
                @click="runTestCase(selectedTestCase)"
                :loading="isRunning"
              >
                <el-icon v-if="!isRunning"><Refresh /></el-icon>
                重新运行
              </el-button>
            </div>
          </div>

          <!-- 测试步骤编辑 -->
          <div class="steps-container" v-show="showSteps">
            <div class="steps-header">
              <h4>测试步骤</h4>
              <el-button size="small" text @click="expandAllSteps">
                {{ allStepsExpanded ? '折叠全部' : '展开全部' }}
              </el-button>
            </div>

            <div class="steps-scroll-container">
              <div class="steps-list">
                <draggable
                  v-model="currentSteps"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onStepsReorder"
                >
                  <template #item="{ element, index }">
                    <div class="step-item" :class="{ expanded: element.expanded }">
                      <div class="step-header">
                        <div class="step-left">
                          <el-icon class="drag-handle"><Rank /></el-icon>
                          <span class="step-number">{{ index + 1 }}</span>
                          <el-select
                            v-model="element.action_type"
                            placeholder="选择操作"
                            size="small"
                            style="width: 120px"
                            @change="onActionTypeChange(element)"
                          >
                            <el-option label="点击" value="click" />
                            <el-option label="输入文本" value="fill" />
                            <el-option label="获取文本" value="getText" />
                            <el-option label="等待元素" value="waitFor" />
                            <el-option label="悬停" value="hover" />
                            <el-option label="滚动" value="scroll" />
                            <el-option label="截图" value="screenshot" />
                            <el-option label="断言" value="assert" />
                            <el-option label="等待" value="wait" />
                            <el-option label="切换标签页" value="switchTab" />
                          </el-select>
                          <el-select
                            v-if="needsElement(element)"
                            v-model="element.element_id"
                            placeholder="选择元素"
                            size="small"
                            style="width: 200px"
                            filterable
                            @change="onElementChange(element)"
                          >
                            <el-option
                              v-for="elem in availableElements"
                              :key="elem.id"
                              :label="`${elem.name} (${elem.locator_value})`"
                              :value="elem.id"
                            />
                          </el-select>
                        </div>
                        <div class="step-right">
                          <el-button
                            size="small"
                            text
                            @click="element.expanded = !element.expanded"
                          >
                            <el-icon>
                              <component :is="element.expanded ? 'ArrowUp' : 'ArrowDown'" />
                            </el-icon>
                          </el-button>
                          <el-button size="small" text type="danger" @click="removeStep(index)">
                            <el-icon><Delete /></el-icon>
                          </el-button>
                        </div>
                      </div>

                      <div v-if="element.expanded" class="step-content">
                        <!-- 输入参数 -->
                        <div v-if="needsInputValue(element.action_type)" class="step-param">
                          <label>输入值：</label>
                          <div style="display: flex; gap: 5px; flex: 1">
                            <el-input
                              v-model="element.input_value"
                              :placeholder="element.action_type === 'switchTab' ? '输入索引(0,1...)或留空切换到最新' : '请输入内容，支持变量如 ${random_phone()}'"
                              size="small"
                            />
                            <el-tooltip content="插入动态变量" placement="top" v-if="element.action_type !== 'switchTab'">
                              <el-button size="small" @click="openVariableHelper(element, 'input_value')">
                                <el-icon><MagicStick /></el-icon>
                              </el-button>
                            </el-tooltip>
                          </div>
                        </div>

                        <!-- 等待时间 -->
                        <div v-if="needsWaitTime(element.action_type)" class="step-param">
                          <label>等待时间（毫秒）：</label>
                          <el-input-number
                            v-model="element.wait_time"
                            :min="100"
                            :max="30000"
                            :step="100"
                            size="small"
                          />
                        </div>

                        <!-- 断言参数 -->
                        <div v-if="element.action_type === 'assert'" class="step-param">
                          <label>断言类型：</label>
                          <el-select v-model="element.assert_type" size="small" style="width: 150px">
                            <el-option label="文本包含" value="textContains" />
                            <el-option label="文本等于" value="textEquals" />
                            <el-option label="元素可见" value="isVisible" />
                            <el-option label="元素存在" value="exists" />
                            <el-option label="属性值" value="hasAttribute" />
                            <el-option label="数据库断言" value="database" />
                          </el-select>
                          
                          <!-- 普通断言的值输入 -->
                          <div v-if="element.assert_type !== 'database'" style="display: flex; align-items: center; margin-left: 10px; width: 240px">
                            <el-input
                              v-model="element.assert_value"
                              placeholder="期望值"
                              size="small"
                              style="flex: 1"
                            />
                            <el-tooltip content="插入动态变量" placement="top">
                              <el-button size="small" style="margin-left: 5px" @click="openVariableHelper(element, 'assert_value')">
                                <el-icon><MagicStick /></el-icon>
                              </el-button>
                            </el-tooltip>
                          </div>
                        </div>
                        
                        <!-- 数据库断言参数 (当assert_type为database时显示) -->
                        <div v-if="element.action_type === 'assert' && element.assert_type === 'database'" class="step-param-group">
                          <div class="step-param">
                            <label>数据库配置：</label>
                            <el-select v-model="element.db_config_id" placeholder="选择数据库配置" size="small" style="width: 200px">
                              <el-option
                                v-for="db in databaseConfigs"
                                :key="db.id"
                                :label="db.name"
                                :value="db.id"
                              />
                            </el-select>
                          </div>

                          <div class="step-param">
                            <label>查询方式：</label>
                            <el-radio-group v-model="element.query_mode" size="small">
                              <el-radio label="sql">SQL语句</el-radio>
                              <el-radio label="natural_language">自然语言(AI)</el-radio>
                            </el-radio-group>
                          </div>

                          <div class="step-param" v-if="element.query_mode !== 'natural_language'">
                            <label>SQL查询：</label>
                            <el-input
                              v-model="element.sql_query"
                              type="textarea"
                              :rows="2"
                              placeholder="SELECT count(*) FROM table WHERE ..."
                              size="small"
                              style="width: 100%"
                            />
                          </div>

                          <div class="step-param" v-else>
                            <label>AI需求：</label>
                            <div style="width: 100%">
                              <div style="display: flex; gap: 5px; margin-bottom: 5px;">
                                <el-input
                                  v-model="element.prompt"
                                  type="textarea"
                                  :rows="2"
                                  placeholder="请输入查询需求，例如：查询用户数量"
                                  size="small"
                                  style="flex: 1"
                                />
                                <el-button 
                                  type="primary" 
                                  size="small" 
                                  @click="handleGenerateSqlInline(element)"
                                  :disabled="!element.db_config_id || !element.prompt"
                                  :loading="element.generating"
                                >
                                  生成
                                </el-button>
                              </div>
                              <div v-if="element.sql_query" style="background-color: #f5f7fa; padding: 5px; border-radius: 4px; font-size: 12px;">
                                <div style="color: #909399; margin-bottom: 2px;">生成的SQL:</div>
                                <code style="word-break: break-all;">{{ element.sql_query }}</code>
                              </div>
                            </div>
                          </div>

                          <div class="step-param">
                            <label>期望结果：</label>
                            <div style="display: flex; align-items: center; width: 100%">
                              <el-input
                                v-model="element.assert_value"
                                placeholder="期望的结果"
                                size="small"
                                style="flex: 1"
                              />
                              <el-tooltip content="插入动态变量" placement="top">
                                <el-button size="small" style="margin-left: 5px" @click="openVariableHelper(element, 'assert_value')">
                                  <el-icon><MagicStick /></el-icon>
                                </el-button>
                              </el-tooltip>
                            </div>
                          </div>
                        </div>

                        <!-- 数据库断言参数 -->
                        <div v-if="element.action_type === 'database_assert'" class="step-param-group">
                          <div class="step-param">
                            <label>数据库配置：</label>
                            <el-select v-model="element.db_config_id" placeholder="选择数据库配置" size="small" style="width: 200px">
                              <el-option
                                v-for="db in databaseConfigs"
                                :key="db.id"
                                :label="db.name"
                                :value="db.id"
                              />
                            </el-select>
                          </div>
                          <div class="step-param">
                            <label>SQL查询：</label>
                            <el-input
                              v-model="element.sql_query"
                              type="textarea"
                              :rows="2"
                              placeholder="SELECT count(*) FROM table WHERE ..."
                              size="small"
                              style="width: 100%"
                            />
                          </div>
                          <div class="step-param">
                            <label>断言类型：</label>
                            <el-select v-model="element.assert_type" size="small" style="width: 150px">
                              <el-option label="相等" value="equal" />
                              <el-option label="包含" value="contain" />
                              <el-option label="大于" value="gt" />
                              <el-option label="小于" value="lt" />
                            </el-select>
                          </div>
                          <div class="step-param">
                            <label>期望值：</label>
                            <div style="display: flex; align-items: center; width: 100%">
                              <el-input
                                v-model="element.assert_value"
                                placeholder="期望的结果"
                                size="small"
                                style="flex: 1"
                              />
                              <el-tooltip content="插入动态变量" placement="top">
                                <el-button size="small" style="margin-left: 5px" @click="openVariableHelper(element, 'assert_value')">
                                  <el-icon><MagicStick /></el-icon>
                                </el-button>
                              </el-tooltip>
                            </div>
                          </div>
                        </div>

                        <!-- 步骤描述 -->
                        <div class="step-param">
                          <label>步骤描述：</label>
                          <el-input
                            v-model="element.description"
                            placeholder="描述这个步骤的作用"
                            size="small"
                          />
                        </div>
                      </div>
                    </div>
                  </template>
                </draggable>
              </div>
            </div>
          </div>

          <!-- 执行结果 -->
          <div v-if="executionResult" class="execution-result" v-show="!showSteps">
            <div class="result-header">
              <h4>执行结果</h4>
              <el-tag :type="executionResult.success ? 'success' : 'danger'">
                {{ executionResult.success ? '执行成功' : '执行失败' }}
              </el-tag>
            </div>
            <div class="result-content">
              <el-tabs v-model="resultActiveTab">
                <el-tab-pane label="执行日志" name="logs">
                  <div class="logs-container">
                    <div v-if="parsedExecutionLogs.length > 0">
                      <div v-for="(step, index) in parsedExecutionLogs" :key="index" class="log-item">
                        <div class="log-header">
                          <el-tag :type="step.success ? 'success' : 'danger'" size="small">
                            步骤 {{ step.step_number }}
                          </el-tag>
                          <span class="log-action">{{ getActionText(step.action_type) }}</span>
                          <span class="log-desc">{{ step.description }}</span>
                        </div>
                        <div v-if="step.error" class="log-error">
                          <el-icon><WarningFilled /></el-icon>
                          <pre class="error-message">{{ step.error }}</pre>
                        </div>
                      </div>
                    </div>
                    <el-empty v-else description="暂无执行日志" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="失败截图" name="screenshots" v-if="executionResult.screenshots && executionResult.screenshots.length > 0">
                  <div class="screenshots-container">
                    <div
                      v-for="(screenshot, index) in executionResult.screenshots"
                      :key="index"
                      class="screenshot-item"
                      @click="previewScreenshot(screenshot)"
                    >
                      <div class="screenshot-wrapper">
                        <img
                          :src="screenshot.url"
                          :alt="`截图 ${index + 1}`"
                          :data-index="index"
                          @error="handleImageError"
                          @load="handleImageLoad"
                        />
                        <div class="screenshot-placeholder" v-if="!screenshot.loaded">
                          <el-icon><Picture /></el-icon>
                          <span>加载中...</span>
                        </div>
                        <div class="screenshot-error" v-if="screenshot.error">
                          <el-icon><Warning /></el-icon>
                          <span>图片加载失败</span>
                        </div>
                        <div class="screenshot-overlay">
                          <el-icon class="zoom-icon"><ZoomIn /></el-icon>
                        </div>
                      </div>
                      <div class="screenshot-info">
                        <p class="screenshot-description">{{ screenshot.description || `截图 ${index + 1}` }}</p>
                        <p class="screenshot-meta" v-if="screenshot.step_number">步骤 {{ screenshot.step_number }}</p>
                        <p class="screenshot-time" v-if="screenshot.timestamp">{{ formatTime(screenshot.timestamp) }}</p>
                      </div>
                    </div>
                  </div>
                </el-tab-pane>
                <el-tab-pane label="错误信息" name="errors" v-if="executionResult.errors && executionResult.errors.length > 0">
                  <div class="errors-container">
                    <div
                      v-for="(error, index) in executionResult.errors"
                      :key="index"
                      class="error-item"
                    >
                      <div class="error-header">
                        <el-tag type="danger" size="large">
                          <el-icon><WarningFilled /></el-icon>
                          {{ error.message || error }}
                        </el-tag>
                        <span v-if="error.step_number" class="error-step">
                          步骤 {{ error.step_number }}
                        </span>
                      </div>

                      <div v-if="error.action_type || error.element || error.description" class="error-meta">
                        <div v-if="error.action_type" class="meta-item">
                          <span class="meta-label">操作类型:</span>
                          <span class="meta-value">{{ error.action_type }}</span>
                        </div>
                        <div v-if="error.element" class="meta-item">
                          <span class="meta-label">目标元素:</span>
                          <span class="meta-value">{{ error.element }}</span>
                        </div>
                        <div v-if="error.description" class="meta-item">
                          <span class="meta-label">步骤描述:</span>
                          <span class="meta-value">{{ error.description }}</span>
                        </div>
                      </div>

                      <div v-if="error.details || error.stack" class="error-details">
                        <div class="details-header">详细错误信息:</div>
                        <pre class="details-content">{{ error.details || error.stack }}</pre>
                      </div>
                    </div>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </div>
          </div>
        </div>

        <div v-else class="no-selection">
          <el-empty description="请选择一个测试用例" />
        </div>
      </div>
    </div>

    <!-- 新建/编辑测试用例对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTestCase ? '编辑测试用例' : '新建测试用例'"
      width="500px"
    >
      <el-form :model="testCaseForm" label-width="100px">
        <el-form-item label="用例名称" required>
          <el-input v-model="testCaseForm.name" placeholder="请输入测试用例名称" />
        </el-form-item>
        <el-form-item label="用例描述">
          <el-input
            v-model="testCaseForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入测试用例描述"
          />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="testCaseForm.priority" style="width: 100%">
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="saveTestCaseForm">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 截图预览对话框 -->
    <el-dialog
      v-model="showScreenshotPreview"
      title="失败截图预览"
      width="80%"
      :close-on-click-modal="true"
    >
      <div v-if="currentScreenshot" class="screenshot-preview">
        <div class="preview-info">
          <h4>{{ currentScreenshot.description }}</h4>
          <p v-if="currentScreenshot.step_number">失败步骤: 步骤 {{ currentScreenshot.step_number }}</p>
          <p v-if="currentScreenshot.timestamp">截图时间: {{ formatTime(currentScreenshot.timestamp) }}</p>
        </div>
        <div class="preview-image">
          <img :src="currentScreenshot.url" :alt="currentScreenshot.description" />
        </div>
      </div>
    </el-dialog>

    <!-- 变量助手对话框 -->
    <el-dialog
      v-model="showVariableHelper"
      title="变量助手 (点击插入)"
      width="800px"
    >
      <el-tabs tab-position="left" style="height: 400px">
        <el-tab-pane
          v-for="(category, index) in variableCategories"
          :key="index"
          :label="category.label"
        >
          <div style="height: 400px; overflow-y: auto">
            <el-table :data="category.variables" style="width: 100%" @row-click="insertVariable" highlight-current-row cursor="pointer">
              <el-table-column prop="name" label="函数名" width="150">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="desc" label="描述" width="150" />
              <el-table-column prop="syntax" label="语法" show-overflow-tooltip />
              <el-table-column label="操作" width="80">
                <template #default="{ row }">
                  <el-button link type="primary" size="small">插入</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, Edit, Delete, Check, CaretRight, ArrowUp, ArrowDown, Rank, Picture, Warning, View, ZoomIn, Refresh, WarningFilled, MagicStick
} from '@element-plus/icons-vue'
import draggable from 'vuedraggable'

import {
  getUiProjects,
  getElements,
  createTestCase,
  updateTestCase,
  deleteTestCase as deleteTestCaseApi,
  getTestCases,
  runTestCase as runTestCaseApi,
  copyTestCase as copyTestCaseApi,
  getLocatorStrategies
} from '@/api/ui_automation'
import { getVannaConfigs, generateSql } from '@/api/data-factory'

// 响应式数据
const projects = ref([])
const projectId = ref('')
const testCases = ref([])
const selectedTestCase = ref(null)
const currentSteps = ref([])
const availableElements = ref([])
const databaseConfigs = ref([])
const searchKeyword = ref('')
const showCreateDialog = ref(false)
const editingTestCase = ref(null)
const executionResult = ref(null)
const resultActiveTab = ref('logs')
const allStepsExpanded = ref(false)
const showSteps = ref(true)
const showScreenshotPreview = ref(false)
const currentScreenshot = ref(null)
const isRunning = ref(false)
const selectedEngine = ref('playwright')  // 默认使用Playwright
const selectedBrowser = ref('chrome')  // 默认使用Chrome
const headlessMode = ref(false)  // 默认使用有头模式
const showVariableHelper = ref(false)
const currentEditingStep = ref(null)
const currentEditingField = ref('')

// 表单数据
const testCaseForm = reactive({
  name: '',
  description: '',
  priority: 'medium'
})

// 计算属性
const filteredTestCases = computed(() => {
  if (!searchKeyword.value) return testCases.value
  return testCases.value.filter(tc =>
    tc.name.includes(searchKeyword.value) ||
    tc.description?.includes(searchKeyword.value)
  )
})

// 解析执行日志
const parsedExecutionLogs = computed(() => {
  if (!executionResult.value || !executionResult.value.logs) return []
  try {
    return typeof executionResult.value.logs === 'string'
      ? JSON.parse(executionResult.value.logs)
      : executionResult.value.logs
  } catch (e) {
    console.error('解析执行日志失败:', e)
    return []
  }
})

// 方法定义
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    projects.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('获取项目列表失败')
    console.error('获取项目列表失败:', error)
  }
}

const loadTestCases = async () => {
  if (!projectId.value) {
    testCases.value = []
    return
  }

  try {
    const response = await getTestCases({ project: projectId.value })
    testCases.value = response.data.results || response.data
  } catch (error) {
    console.error('获取测试用例失败:', error)
  }
}

const loadElements = async () => {
  if (!projectId.value) {
    availableElements.value = []
    return
  }

  try {
    const response = await getElements({ project: projectId.value })
    availableElements.value = response.data.results || response.data
  } catch (error) {
    console.error('获取元素列表失败:', error)
  }
}

const loadDatabaseConfigs = async () => {
  try {
    const res = await getVannaConfigs({ page_size: 100 })
    databaseConfigs.value = res.data.results || res.data
  } catch (error) {
    console.error('加载数据库配置失败', error)
  }
}

const handleGenerateSqlInline = async (element) => {
  if (!element.prompt) {
    ElMessage.warning('请输入查询需求')
    return
  }
  
  if (!element.db_config_id) {
    ElMessage.warning('请先选择数据库配置')
    return
  }
  
  element.generating = true
  try {
    const res = await generateSql({
      prompt: element.prompt,
      db_config_id: element.db_config_id
    })
    
    if (res.data && res.data.sql) {
      element.sql_query = res.data.sql
      ElMessage.success('SQL生成成功')
    } else {
      ElMessage.error('生成失败：未返回SQL')
    }
  } catch (error) {
    ElMessage.error('生成SQL失败: ' + (error.response?.data?.error || error.message))
  } finally {
    element.generating = false
  }
}

const onProjectChange = async () => {
  selectedTestCase.value = null
  currentSteps.value = []
  executionResult.value = null

  await Promise.all([
    loadTestCases(),
    loadElements()
  ])
}

const selectTestCase = (testCase) => {
  // 如果点击的是同一个用例，不做任何处理
  if (selectedTestCase.value && selectedTestCase.value.id === testCase.id) {
    return
  }

  selectedTestCase.value = testCase
  // 确保步骤数据格式正确，添加前端需要的字段
  if (testCase.steps && testCase.steps.length > 0) {
    currentSteps.value = testCase.steps.map(step => ({
      ...step,
      element_id: step.element || '',
      expanded: false
    }))
  } else {
    currentSteps.value = []
  }
  // 只有在切换到不同用例时才清空执行结果
  executionResult.value = null
  showSteps.value = true
}

const addStep = () => {
  const newStep = {
    id: Date.now(),
    action_type: 'click',
    element_id: '',
    input_value: '',
    wait_time: 1000,
    assert_type: 'textContains',
    assert_value: '',
    description: '',
    db_config_id: null,
    sql_query: '',
    query_mode: 'sql',
    prompt: '',
    expanded: true
  }
  currentSteps.value.push(newStep)
}

const removeStep = (index) => {
  currentSteps.value.splice(index, 1)
}

const onStepsReorder = () => {
  // 步骤重新排序后的处理
  console.log('步骤已重新排序')
}

const onActionTypeChange = (step) => {
  // 根据操作类型重置相关参数
  if (step.action_type !== 'fill') {
    step.input_value = ''
  }
  if (step.action_type !== 'wait') {
    step.wait_time = 1000
  }
  if (step.action_type !== 'assert' && step.action_type !== 'database_assert') {
    step.assert_type = 'textContains'
    step.assert_value = ''
  }
  if (step.action_type === 'database_assert') {
    step.assert_type = 'equal'
  }
}

const onElementChange = (step) => {
  // 元素变化时的处理
  const element = availableElements.value.find(e => e.id === step.element_id)
  if (element && !step.description) {
    step.description = `${getActionTypeText(step.action_type)}${element.name}`
  }
}

const needsInputValue = (actionType) => {
  return ['fill', 'switchTab'].includes(actionType)
}

const needsWaitTime = (actionType) => {
  return ['wait', 'waitFor'].includes(actionType)
}

const needsElement = (step) => {
  const actionType = step.action_type || step
  // 如果是assert且断言类型为database，不需要元素
  if (actionType === 'assert' && step.assert_type === 'database') {
    return false
  }
  return !['wait', 'switchTab', 'screenshot', 'database_assert'].includes(actionType)
}

const expandAllSteps = () => {
  allStepsExpanded.value = !allStepsExpanded.value
  currentSteps.value.forEach(step => {
    step.expanded = allStepsExpanded.value
  })
}

const saveTestCase = async () => {
  if (!selectedTestCase.value) return

  try {
    const updateData = {
      ...selectedTestCase.value,
      steps: currentSteps.value
    }

    await updateTestCase(selectedTestCase.value.id, updateData)
    ElMessage.success('测试用例保存成功')

    // 更新本地数据
    const index = testCases.value.findIndex(tc => tc.id === selectedTestCase.value.id)
    if (index !== -1) {
      testCases.value[index] = { ...updateData }
      selectedTestCase.value = { ...updateData }
    }
  } catch (error) {
    console.error('保存测试用例失败:', error)
    ElMessage.error('保存测试用例失败')
  }
}

const runTestCase = async (testCase) => {
  isRunning.value = true
  try {
    const modeText = headlessMode.value ? '无头模式' : '有头模式'
    ElMessage.info(`开始执行测试用例... (引擎: ${selectedEngine.value.toUpperCase()}, 浏览器: ${selectedBrowser.value.toUpperCase()}, ${modeText})`)

    const response = await runTestCaseApi(testCase.id, {
      project_id: projectId.value,
      engine: selectedEngine.value,
      browser: selectedBrowser.value,
      headless: headlessMode.value
    })

    executionResult.value = response.data
    resultActiveTab.value = 'logs'
    showSteps.value = false  // 自动切换到结果视图

    if (response.data.success) {
      ElMessage.success('测试用例执行成功')
    } else {
      ElMessage.error('测试用例执行失败')
      // 如果有截图，自动切换到截图标签页
      if (response.data.screenshots && response.data.screenshots.length > 0) {
        resultActiveTab.value = 'screenshots'
      }
    }
  } catch (error) {
    console.error('执行测试用例失败:', error)

    // 即使出错也要设置执行结果,显示错误信息
    const errorMessage = error.response?.data?.message || error.message || '执行失败'
    const errorLogs = error.response?.data?.logs || `测试用例执行出错\n\n错误信息: ${errorMessage}`

    // 格式化错误信息为统一的对象格式
    const errors = error.response?.data?.errors || [{
      message: errorMessage,
      details: error.stack || '',
      step_number: null,
      action_type: '',
      element: '',
      description: ''
    }]

    executionResult.value = {
      success: false,
      logs: errorLogs,
      screenshots: error.response?.data?.screenshots || [],
      execution_time: 0,
      errors: errors
    }
    resultActiveTab.value = 'logs'
    showSteps.value = false  // 切换到结果视图显示错误

    ElMessage.error(`执行测试用例失败: ${errorMessage}`)
  } finally {
    isRunning.value = false
  }
}

const toggleView = () => {
  showSteps.value = !showSteps.value
}

const editTestCase = (testCase) => {
  editingTestCase.value = testCase
  testCaseForm.name = testCase.name
  testCaseForm.description = testCase.description || ''
  testCaseForm.priority = testCase.priority || 'medium'
  showCreateDialog.value = true
}

const deleteTestCase = async (testCase) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除测试用例"${testCase.name}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteTestCaseApi(testCase.id)
    ElMessage.success('删除成功')

    // 从列表中移除
    const index = testCases.value.findIndex(tc => tc.id === testCase.id)
    if (index !== -1) {
      testCases.value.splice(index, 1)
    }

    // 如果删除的是当前选中的用例，清空选择
    if (selectedTestCase.value?.id === testCase.id) {
      selectedTestCase.value = null
      currentSteps.value = []
      executionResult.value = null
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除测试用例失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const copyTestCase = async (testCase) => {
  try {
    await ElMessageBox.confirm(
      `确定要复制测试用例"${testCase.name}"吗？`,
      '确认复制',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    const response = await copyTestCaseApi(testCase.id)
    ElMessage.success('复制成功')

    // 找到原用例的位置
    const index = testCases.value.findIndex(tc => tc.id === testCase.id)
    if (index !== -1) {
      // 在原用例下方插入新用例
      testCases.value.splice(index + 1, 0, response.data)
    } else {
      // 如果找不到，就添加到末尾
      testCases.value.push(response.data)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('复制测试用例失败:', error)
      ElMessage.error('复制失败')
    }
  }
}

const variableCategories = [
  {
    label: '随机数',
    variables: [
      { name: 'random_int', syntax: '${random_int(min, max)}', desc: '生成随机整数', example: '${random_int(100, 999)}' },
      { name: 'random_float', syntax: '${random_float(min, max, decimals)}', desc: '生成随机浮点数', example: '${random_float(0, 1, 2)}' },
      { name: 'random_digits', syntax: '${random_digits(length)}', desc: '生成随机数字字符串', example: '${random_digits(6)}' }
    ]
  },
  {
    label: '随机字符串',
    variables: [
      { name: 'random_string', syntax: '${random_string(length)}', desc: '生成随机字母数字字符串', example: '${random_string(8)}' },
      { name: 'random_letters', syntax: '${random_letters(length)}', desc: '生成随机字母字符串', example: '${random_letters(8)}' },
      { name: 'random_chinese', syntax: '${random_chinese(length)}', desc: '生成随机中文字符', example: '${random_chinese(2)}' }
    ]
  },
  {
    label: '业务数据',
    variables: [
      { name: 'random_phone', syntax: '${random_phone()}', desc: '生成随机手机号', example: '${random_phone()}' },
      { name: 'random_email', syntax: '${random_email()}', desc: '生成随机邮箱', example: '${random_email()}' },
      { name: 'random_id_card', syntax: '${random_id_card()}', desc: '生成随机身份证号', example: '${random_id_card()}' },
      { name: 'random_name', syntax: '${random_name()}', desc: '生成随机中文姓名', example: '${random_name()}' },
      { name: 'random_company', syntax: '${random_company()}', desc: '生成随机公司名称', example: '${random_company()}' },
      { name: 'random_address', syntax: '${random_address()}', desc: '生成随机地址', example: '${random_address()}' }
    ]
  },
  {
    label: '时间日期',
    variables: [
      { name: 'timestamp', syntax: '${timestamp()}', desc: '当前时间戳(毫秒)', example: '${timestamp()}' },
      { name: 'datetime', syntax: '${datetime(format)}', desc: '格式化日期时间', example: '${datetime(YYYY-MM-DD HH:mm:ss)}' },
      { name: 'date', syntax: '${date(format)}', desc: '格式化日期', example: '${date(YYYY-MM-DD)}' },
      { name: 'time', syntax: '${time(format)}', desc: '格式化时间', example: '${time(HH:mm:ss)}' },
      { name: 'date_offset', syntax: '${date_offset(days, format)}', desc: '日期偏移', example: '${date_offset(1, YYYY-MM-DD)}' }
    ]
  },
  {
    label: '其他',
    variables: [
      { name: 'uuid', syntax: '${uuid()}', desc: '生成UUID', example: '${uuid()}' },
      { name: 'base64', syntax: '${base64(text)}', desc: 'Base64编码', example: '${base64(123456)}' },
      { name: 'md5', syntax: '${md5(text)}', desc: 'MD5哈希', example: '${md5(123456)}' }
    ]
  }
]

const openVariableHelper = (step, field) => {
  currentEditingStep.value = step
  currentEditingField.value = field
  showVariableHelper.value = true
}

const insertVariable = (variable) => {
  if (currentEditingStep.value && currentEditingField.value) {
    const example = variable.example
    const currentValue = currentEditingStep.value[currentEditingField.value] || ''
    
    // 简单起见，这里直接追加到末尾，或者如果为空则替换
    if (!currentValue) {
      currentEditingStep.value[currentEditingField.value] = example
    } else {
      currentEditingStep.value[currentEditingField.value] = currentValue + example
    }
    
    ElMessage.success(`已插入变量: ${variable.name}`)
    showVariableHelper.value = false
  }
}

const saveTestCaseForm = async () => {
  if (!testCaseForm.name.trim()) {
    ElMessage.warning('请输入测试用例名称')
    return
  }

  try {
    const data = {
      name: testCaseForm.name,
      description: testCaseForm.description,
      priority: testCaseForm.priority,
      project: projectId.value,
      steps: []
    }

    if (editingTestCase.value) {
      // 编辑现有用例
      await updateTestCase(editingTestCase.value.id, data)
      ElMessage.success('测试用例更新成功')

      // 更新本地数据
      const index = testCases.value.findIndex(tc => tc.id === editingTestCase.value.id)
      if (index !== -1) {
        testCases.value[index] = { ...testCases.value[index], ...data }
      }
    } else {
      // 创建新用例
      const response = await createTestCase(data)
      ElMessage.success('测试用例创建成功')
      testCases.value.push(response.data)
    }

    showCreateDialog.value = false
    editingTestCase.value = null
    resetForm()
  } catch (error) {
    console.error('保存测试用例失败:', error)
    ElMessage.error('保存失败')
  }
}

const resetForm = () => {
  testCaseForm.name = ''
  testCaseForm.description = ''
  testCaseForm.priority = 'medium'
}

// 辅助方法
const getStatusTag = (status) => {
  const tagMap = {
    'draft': 'info',
    'ready': 'success',
    'running': 'warning',
    'passed': 'success',
    'failed': 'danger'
  }
  return tagMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'draft': '草稿',
    'ready': '就绪',
    'running': '执行中',
    'passed': '通过',
    'failed': '失败'
  }
  return textMap[status] || '未知'
}

const getActionTypeText = (actionType) => {
  const textMap = {
    'click': '点击',
    'fill': '输入',
    'getText': '获取文本',
    'waitFor': '等待',
    'hover': '悬停',
    'scroll': '滚动',
    'screenshot': '截图',
    'assert': '断言',
    'wait': '等待',
    'database_assert': '数据库断言'
  }
  return textMap[actionType] || actionType
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString()
}

// 获取操作类型文本
const getActionText = (actionType) => {
  const actionMap = {
    'click': '点击',
    'fill': '填写',
    'getText': '获取文本',
    'waitFor': '等待元素',
    'hover': '悬停',
    'scroll': '滚动',
    'screenshot': '截图',
    'assert': '断言',
    'wait': '等待',
    'database_assert': '数据库断言'
  }
  return actionMap[actionType] || actionType
}

// 图片处理方法
const handleImageError = (event) => {
  const img = event.target
  const screenshotIndex = parseInt(img.dataset.index)
  if (executionResult.value && executionResult.value.screenshots) {
    executionResult.value.screenshots[screenshotIndex].error = true
    executionResult.value.screenshots[screenshotIndex].loaded = true
  }
}

const handleImageLoad = (event) => {
  const img = event.target
  const screenshotIndex = parseInt(img.dataset.index)
  if (executionResult.value && executionResult.value.screenshots) {
    executionResult.value.screenshots[screenshotIndex].loaded = true
    executionResult.value.screenshots[screenshotIndex].error = false
  }
}

const previewScreenshot = (screenshot) => {
  currentScreenshot.value = screenshot
  showScreenshotPreview.value = true
}

// 组件挂载
onMounted(async () => {
  await loadProjects()
  loadDatabaseConfigs()

  if (projects.value.length > 0) {
    projectId.value = projects.value[0].id
    await onProjectChange()
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
  padding: 20px;
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
  padding: 10px;
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

.test-case-item.active {
  border-color: #409eff;
  background-color: #f0f8ff;
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
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
}

.step-count {
  color: #409eff;
  font-weight: 500;
}

.right-panel {
  flex: 1;
  background: white;
  display: flex;
  flex-direction: column;
}

.test-case-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow: hidden;
  height: 100%;
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

.steps-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  margin-bottom: 20px;
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  background: #fafafa;
  overflow: hidden;
}

.steps-container.has-steps {
  max-height: 50%;
}

.steps-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.steps-header h4 {
  margin: 0;
}

.steps-list {
  padding: 10px;
  padding-bottom: 20px;
}

.steps-scroll-container {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  padding: 10px;
  padding-right: 5px;
}

.steps-scroll-container::-webkit-scrollbar {
  width: 6px;
}

.steps-scroll-container::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 3px;
}

.steps-scroll-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.steps-scroll-container::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.step-item {
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  margin-bottom: 10px;
  background: white;
  transition: all 0.3s;
}

.step-item:hover {
  border-color: #409eff;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: #fafafa;
  border-radius: 6px 6px 0 0;
}

.step-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.drag-handle {
  cursor: move;
  color: #999;
}

.step-number {
  background: #409eff;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.step-right {
  display: flex;
  gap: 5px;
}

.step-content {
  padding: 15px;
  border-top: 1px solid #e6e6e6;
}

.step-param {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  gap: 10px;
}

.step-param label {
  width: 120px;
  font-weight: 500;
  color: #333;
}

.execution-result {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  background: white;
  overflow: hidden;
}

.execution-result.with-steps {
  margin-top: 0;
}

.execution-result .result-header {
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
  background: #fafafa;
  border-radius: 6px 6px 0 0;
}

.execution-result .result-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 15px;
}

.result-content {
  flex: 1;
  overflow: hidden;
}

/* 为el-tabs和el-tab-pane添加flex布局支持 */
.result-content :deep(.el-tabs) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.result-content :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.result-content :deep(.el-tab-pane) {
  height: 100%;
  overflow: auto;
}

/* .result-header 已在 .execution-result 中定义 */

.result-header h4 {
  margin: 0;
}

.logs-container {
  max-height: 500px;
  overflow-y: auto;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}

.log-item {
  margin-bottom: 15px;
  padding: 12px;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.log-item:last-child {
  margin-bottom: 0;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.log-action {
  font-weight: 500;
  color: #606266;
}

.log-desc {
  color: #909399;
  font-size: 14px;
}

.log-error {
  display: flex;
  align-items: flex-start;  /* 改为 flex-start，适配多行文本 */
  gap: 8px;
  color: #f56c6c;
  background: #fef0f0;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 8px;
  font-size: 14px;

  .error-message {
    margin: 0;
    padding: 0;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;  /* 保留换行符和空格 */
    word-break: break-word;  /* 长单词换行 */
    flex: 1;
  }

  .el-icon {
    margin-top: 2px;  /* 图标与文本顶部对齐 */
    flex-shrink: 0;  /* 图标不缩小 */
  }
}

.screenshots-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  padding: 10px;
}

.screenshot-item {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.screenshot-item:hover {
  transform: translateY(-4px);
}

.screenshot-wrapper {
  position: relative;
  width: 100%;
  min-height: 200px;
  background: #f5f5f5;
  border-radius: 8px;
  border: 2px solid #e6e6e6;
  overflow: hidden;
  transition: border-color 0.3s ease;
}

.screenshot-item:hover .screenshot-wrapper {
  border-color: #409eff;
}

.screenshot-wrapper img {
  width: 100%;
  height: auto;
  display: block;
  transition: opacity 0.3s ease;
}

.screenshot-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.screenshot-item:hover .screenshot-overlay {
  opacity: 1;
}

.zoom-icon {
  font-size: 48px;
  color: white;
}

.screenshot-placeholder,
.screenshot-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #999;
  font-size: 14px;
}

.screenshot-placeholder .el-icon,
.screenshot-error .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.screenshot-error {
  color: #f56c6c;
}

.screenshot-info {
  margin-top: 10px;
}

.screenshot-description {
  margin: 0 0 5px 0;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  text-align: left;
}

.screenshot-meta {
  margin: 0 0 3px 0;
  font-size: 12px;
  color: #666;
  text-align: left;
}

.screenshot-time {
  margin: 0;
  font-size: 11px;
  color: #999;
  text-align: left;
}

/* 截图预览对话框样式 */
.screenshot-preview {
  display: flex;
  flex-direction: column;
}

.preview-info {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 6px;
}

.preview-info h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #333;
}

.preview-info p {
  margin: 5px 0;
  font-size: 14px;
  color: #666;
}

.preview-image {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 20px;
  max-height: 70vh;
  overflow: auto;
}

.preview-image img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.errors-container {
  padding: 10px;
  height: 100%;
  overflow-y: auto;
}

.error-item {
  background: #fff;
  border: 2px solid #f56c6c;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 15px;
}

.error-item:last-child {
  margin-bottom: 0;
}

.error-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #f5f5f5;
}

.error-header .el-tag {
  font-size: 16px;
  padding: 10px 15px;
  font-weight: 600;
}

.error-header .el-icon {
  margin-right: 5px;
}

.error-step {
  background: #fef0f0;
  color: #f56c6c;
  padding: 5px 12px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 14px;
}

.error-meta {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 15px;
}

.meta-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
}

.meta-item:last-child {
  margin-bottom: 0;
}

.meta-label {
  font-weight: 600;
  color: #606266;
  min-width: 80px;
  margin-right: 10px;
}

.meta-value {
  color: #303133;
  flex: 1;
}

.error-details {
  background: #2d2d2d;
  border-radius: 6px;
  overflow: hidden;
}

.details-header {
  background: #1e1e1e;
  color: #fff;
  padding: 10px 15px;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid #3d3d3d;
}

.details-content {
  color: #ff6b6b;
  padding: 15px;
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.details-content::-webkit-scrollbar {
  width: 6px;
}

.details-content::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.details-content::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

.details-content::-webkit-scrollbar-thumb:hover {
  background: #777;
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>