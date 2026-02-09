<template>
  <div class="page-container">
    <div class="page-header">
      <h3 class="page-title">用例管理</h3>
      <div class="header-actions">
        <el-button type="primary" @click="openTestCaseDialog()">
          <el-icon><Plus /></el-icon> 新增用例
        </el-button>
        <el-button @click="fetchTestCases">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>
    
    <div class="main-content">
      <div class="card-container">
        <div class="case-layout">
          <!-- Left: Case List -->
          <div class="sidebar">
            <div class="sidebar-header">
              <el-select v-model="selectedProject" placeholder="选择项目" @change="onProjectChange" class="filter-select">
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
              <div class="sidebar-actions">
                <el-input
                  v-model="searchText"
                  placeholder="搜索用例..."
                  prefix-icon="Search"
                  clearable
                  size="small"
                />
                <el-button type="primary" size="small" @click="openTestCaseDialog()" title="新增用例">
                  <el-icon><Plus /></el-icon>
                </el-button>
              </div>
            </div>
            
            <div class="case-list" v-loading="loading">
              <div 
                v-for="testCase in filteredTestCases" 
                :key="testCase.id"
                class="case-item"
                :class="{ active: selectedCase && selectedCase.id === testCase.id }"
                @click="selectCase(testCase)"
              >
                <div class="case-item-header">
                  <span class="case-name" :title="testCase.name">{{ testCase.name }}</span>
                  <div class="item-actions">
                    <el-button link type="primary" size="small" @click.stop="openTestCaseDialog(testCase)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                    <el-button link type="danger" size="small" @click.stop="handleDeleteCase(testCase)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>
                <div class="case-item-meta">
                  <el-tag size="small" :type="getStatusType(testCase.status)">
                    {{ getStatusLabel(testCase.status) }}
                  </el-tag>
                  <el-tag size="small" :type="getPriorityType(testCase.priority)" class="priority-tag">
                    {{ getPriorityLabel(testCase.priority) }}
                  </el-tag>
                </div>
              </div>
              <el-empty v-if="filteredTestCases.length === 0" description="暂无用例" />
            </div>
          </div>

          <!-- Right: Case Detail -->
          <div class="case-detail">
            <div v-if="!selectedCase" class="empty-state">
              <el-empty description="请选择一个用例查看详情，或点击上方按钮创建新用例">
                <el-button type="primary" @click="openTestCaseDialog()">创建新用例</el-button>
              </el-empty>
            </div>
            
            <div v-else class="detail-content">
              <div class="detail-header">
                <div class="title-section">
                  <div class="title-row">
                    <h2>{{ selectedCase.name }}</h2>
                    <el-tag size="small" :type="getStatusType(selectedCase.status)">
                      {{ getStatusLabel(selectedCase.status) }}
                    </el-tag>
                  </div>
                  <p class="description">{{ selectedCase.description || '暂无描述' }}</p>
                </div>
                <div class="actions">
                  <el-button-group>
                    <el-button type="primary" @click="runCase" :loading="executing">
                      <el-icon><VideoPlay /></el-icon> 执行用例
                    </el-button>
                    <el-button @click="fetchExecutionHistory">
                      <el-icon><Timer /></el-icon> 历史记录
                    </el-button>
                    <el-button type="success" @click="openInterfaceSelector">
                      <el-icon><Plus /></el-icon> 添加步骤
                    </el-button>
                  </el-button-group>
                </div>
              </div>

              <!-- Execution Summary -->
              <div v-if="latestResult" class="execution-summary-card" :class="latestResult.status">
                <div class="summary-header">
                  <div class="status-info">
                    <el-tag :type="latestResult.status === 'passed' ? 'success' : 'danger'" size="large" effect="dark">
                      {{ latestResult.status === 'passed' ? '测试通过' : '测试失败' }}
                    </el-tag>
                    <span class="execution-time">
                      <el-icon><Clock /></el-icon> {{ new Date(latestResult.created_at).toLocaleString() }}
                    </span>
                    <span class="duration">
                      耗时: {{ (latestResult.execution_time).toFixed(2) }} ms
                    </span>
                  </div>
                  <div class="stats">
                    <span class="stat-item">总计: <strong>{{ latestResult.total_steps }}</strong></span>
                    <span class="stat-item passed">通过: <strong>{{ latestResult.passed_steps }}</strong></span>
                    <span class="stat-item failed">失败: <strong>{{ latestResult.failed_steps }}</strong></span>
                  </div>
                  <div class="report-action">
                    <el-button type="primary" link @click="showFullReport = true">
                      查看完整报告 <el-icon><ArrowRight /></el-icon>
                    </el-button>
                  </div>
                </div>
              </div>

              <div class="steps-section">
                <div class="section-header">
                  <h3>测试步骤 ({{ steps.length }})</h3>
                  <span class="tip">可拖拽步骤进行排序</span>
                </div>
                
                <div class="steps-list-container">
                  <draggable 
                    v-model="steps" 
                    item-key="id"
                    handle=".drag-handle"
                    @end="handleStepSort"
                    class="steps-draggable"
                  >
                    <template #item="{ element, index }">
                      <div class="step-card" :class="{ 
                        'has-result': getStepResult(element.step_number),
                        'passed': getStepResult(element.step_number)?.passed,
                        'failed': getStepResult(element.step_number) && !getStepResult(element.step_number).passed
                      }">
                        <div class="step-main">
                          <div class="drag-handle">
                            <el-icon><Rank /></el-icon>
                          </div>
                          <div class="step-index">{{ index + 1 }}</div>
                          <div class="step-info">
                            <div class="step-name-row">
                              <span class="step-name">{{ element.name }}</span>
                              <el-tag v-if="element.api_request" size="small" type="info" effect="plain">
                                引用接口: {{ element.api_request.name }}
                              </el-tag>
                              <!-- Step Execution Status -->
                              <template v-if="getStepResult(element.step_number)">
                                <el-tag 
                                  :type="getStepResult(element.step_number).passed ? 'success' : 'danger'" 
                                  size="small" 
                                  class="step-status-tag clickable"
                                  @click.stop="openStepResult(element)"
                                  title="点击查看执行详情"
                                >
                                  <el-icon><component :is="getStepResult(element.step_number).passed ? 'Check' : 'Close'" /></el-icon>
                                  {{ getStepResult(element.step_number).passed ? '通过' : '失败' }}
                                </el-tag>
                                <span class="step-duration">{{ getStepResult(element.step_number).response_time.toFixed(0) }}ms</span>
                              </template>
                            </div>
                            <div class="step-url-row">
                              <el-tag size="small" :type="getMethodColor(element.method)" class="method-tag">
                                {{ element.method }}
                              </el-tag>
                              <span class="step-url" :title="element.url">{{ element.url }}</span>
                            </div>
                          </div>
                          <div class="step-actions">
                            <el-switch
                              v-model="element.enable"
                              size="small"
                              @change="toggleStep(element)"
                              title="启用/禁用"
                            />
                            <el-button link type="primary" @click="editStep(element)">
                              <el-icon><Edit /></el-icon> 编辑
                            </el-button>
                            <el-button link type="danger" @click="deleteStep(element)">
                              <el-icon><Delete /></el-icon> 删除
                            </el-button>
                          </div>
                        </div>
                        
                        <!-- Step Execution Error -->
                        <div v-if="getStepResult(element.step_number)?.error" class="step-error-info">
                          <el-icon><Warning /></el-icon> {{ getStepResult(element.step_number).error }}
                        </div>

                        <div class="step-footer" v-if="element.assertions?.length || element.extract_rules?.length">
                          <div class="meta-item" v-if="element.assertions?.length">
                            <el-icon><Check /></el-icon>
                            <span>{{ element.assertions.length }} 个断言</span>
                          </div>
                          <div class="meta-item" v-if="element.extract_rules?.length">
                            <el-icon><Connection /></el-icon>
                            <span>{{ element.extract_rules.length }} 个变量提取</span>
                          </div>
                        </div>
                      </div>
                    </template>
                  </draggable>
                  
                  <div v-if="steps.length === 0" class="no-steps">
                    <el-empty description="暂无测试步骤" :image-size="100">
                      <el-button type="primary" size="small" @click="openInterfaceSelector">添加第一个步骤</el-button>
                    </el-empty>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TestCase Create/Edit Dialog -->
    <el-dialog 
      v-model="showCaseDialog" 
      :title="testCaseForm.id ? '编辑用例' : '新增用例'" 
      width="500px"
    >
      <el-form :model="testCaseForm" :rules="caseRules" ref="caseFormRef" label-width="80px">
        <el-form-item label="用例名称" prop="name">
          <el-input v-model="testCaseForm.name" placeholder="请输入用例名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="testCaseForm.description" type="textarea" :rows="3" placeholder="请输入用例描述" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="testCaseForm.priority" style="width: 100%">
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="testCaseForm.status" style="width: 100%">
            <el-option label="草稿" value="draft" />
            <el-option label="就绪" value="ready" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCaseDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTestCase" :loading="savingCase">确定</el-button>
      </template>
    </el-dialog>

    <!-- Interface Selector Dialog -->
    <el-dialog v-model="showInterfaceSelector" title="从接口库选择" width="800px" top="10vh">
      <div class="interface-selector">
        <div class="selector-header">
          <el-input
            v-model="interfaceSearchText"
            placeholder="搜索接口名称或URL..."
            prefix-icon="Search"
            clearable
          />
        </div>
        <div class="interface-list" v-loading="loadingInterfaces">
          <el-table 
            :data="filteredInterfaces" 
            max-height="400" 
            @selection-change="handleInterfaceSelectionChange"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="name" label="接口名称" min-width="150" />
            <el-table-column prop="method" label="方法" width="100">
              <template #default="{ row }">
                <el-tag :type="getMethodColor(row.method)" size="small">{{ row.method }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="url" label="URL" min-width="250" show-overflow-tooltip />
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button @click="showInterfaceSelector = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="addStepsFromInterfaces" 
          :disabled="selectedInterfaces.length === 0"
        >
          添加 ({{ selectedInterfaces.length }})
        </el-button>
      </template>
    </el-dialog>

    <!-- Step Editor Dialog -->
    <el-dialog v-model="showStepEditor" title="编辑步骤详情" width="1000px" top="5vh" custom-class="step-editor-dialog">
      <div v-if="editingStepForm" class="step-editor-container">
        <div class="step-editor-header">
          <div class="method-url-row">
            <el-tag :type="getMethodColor(editingStepForm.method)" effect="dark">{{ editingStepForm.method }}</el-tag>
            <el-input v-model="editingStepForm.url" placeholder="请求URL" class="url-input" />
          </div>
          <div class="name-row">
            <el-input v-model="editingStepForm.name" placeholder="步骤名称" class="name-input" />
            <div class="wait-time">
              <span>等待 (ms): </span>
              <el-input-number v-model="editingStepForm.wait_time" :min="0" :step="100" size="small" />
            </div>
          </div>
        </div>

        <el-tabs v-model="stepActiveTab" class="step-config-tabs">
          <el-tab-pane label="请求参数" name="params">
            <div class="config-section">
              <h4>Query 参数 (会覆盖接口库定义)</h4>
              <KeyValueEditor v-model="editingStepForm.params" />
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="请求头" name="headers">
            <div class="config-section">
              <h4>Headers (会覆盖接口库定义)</h4>
              <KeyValueEditor v-model="editingStepForm.headers" />
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="请求体" name="body">
            <div class="config-section">
              <el-radio-group v-model="editingStepForm.body.type" size="small" style="margin-bottom: 15px">
                <el-radio label="none">none</el-radio>
                <el-radio label="json">json</el-radio>
                <el-radio label="form-data">form-data</el-radio>
                <el-radio label="raw">raw</el-radio>
              </el-radio-group>
              
              <div v-if="editingStepForm.body.type === 'json' || editingStepForm.body.type === 'raw'" class="body-editor">
                <el-input
                  v-model="stepBodyRaw"
                  type="textarea"
                  :rows="12"
                  placeholder='请输入请求体内容，支持使用变量 {{variable}}'
                  class="code-input"
                />
              </div>
              <div v-else-if="editingStepForm.body.type === 'form-data'">
                <KeyValueEditor v-model="editingStepForm.body.form_data" :show-file="true" />
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="断言校验" name="assertions">
            <div class="config-section">
              <div class="section-header">
                <h4>断言规则</h4>
                <el-button type="primary" size="small" link @click="addStepAssertion">
                  <el-icon><Plus /></el-icon>添加断言
                </el-button>
              </div>
              <div class="assertion-list">
                <div v-for="(item, idx) in editingStepForm.assertions" :key="idx" class="assertion-card-edit">
                  <div class="card-header">
                    <el-input v-model="item.name" placeholder="断言名称" size="small" style="width: 200px" />
                    <el-button type="danger" link @click="editingStepForm.assertions.splice(idx, 1)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <div class="card-body">
                    <el-select v-model="item.type" placeholder="断言类型" size="small" style="width: 150px">
                      <el-option label="状态码" value="status_code" />
                      <el-option label="JSON路径" value="json_path" />
                      <el-option label="响应包含" value="contains" />
                      <el-option label="响应时间" value="response_time" />
                    </el-select>
                    <el-input v-if="item.type === 'json_path'" v-model="item.json_path" placeholder="JSONPath (e.g. $.code)" size="small" style="width: 200px" />
                    <el-select v-model="item.operator" placeholder="操作符" size="small" style="width: 120px">
                      <el-option label="等于" value="equals" />
                      <el-option label="不等于" value="not_equals" />
                      <el-option label="包含" value="contains" />
                      <el-option label="大于" value="gt" />
                      <el-option label="小于" value="lt" />
                    </el-select>
                    <el-input v-model="item.expected" placeholder="期望值" size="small" style="flex: 1" />
                  </div>
                </div>
                <el-empty v-if="!editingStepForm.assertions?.length" description="暂无断言" :image-size="60" />
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="变量提取" name="extract">
            <div class="config-section">
              <div class="section-header">
                <h4>变量提取规则</h4>
                <el-button type="primary" size="small" link @click="addStepExtract">
                  <el-icon><Plus /></el-icon>添加提取
                </el-button>
              </div>
              <div class="extract-list">
                <div v-for="(item, idx) in editingStepForm.extract_rules" :key="idx" class="extract-card-edit">
                  <div class="card-header">
                    <el-input v-model="item.variable_name" placeholder="变量名称 (后续步骤可通过 {{name}} 引用)" size="small" style="width: 300px" />
                    <el-button type="danger" link @click="editingStepForm.extract_rules.splice(idx, 1)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <div class="card-body">
                    <el-select v-model="item.type" placeholder="提取方式" size="small" style="width: 150px">
                      <el-option label="JSON路径" value="json_path" />
                      <el-option label="响应头" value="header" />
                      <el-option label="正则表达式" value="regex" />
                    </el-select>
                    <el-input v-if="item.type === 'json_path'" v-model="item.json_path" placeholder="JSONPath (e.g. $.data.token)" size="small" style="flex: 1" />
                    <el-input v-if="item.type === 'header'" v-model="item.header_name" placeholder="Header名称 (e.g. Set-Cookie)" size="small" style="flex: 1" />
                    <el-input v-if="item.type === 'regex'" v-model="item.pattern" placeholder="正则表达式" size="small" style="flex: 1" />
                  </div>
                </div>
                <el-empty v-if="!editingStepForm.extract_rules?.length" description="暂无变量提取" :image-size="60" />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      <template #footer>
        <el-button @click="showStepEditor = false">取消</el-button>
        <el-button type="primary" @click="saveStep" :loading="savingStep">保存步骤</el-button>
      </template>
    </el-dialog>

    <!-- Execute Case Dialog -->
    <el-dialog v-model="showExecuteDialog" title="执行测试用例" width="500px">
      <el-form :model="executeForm" label-width="100px">
        <el-form-item label="执行环境">
          <el-select v-model="executeForm.environment_id" placeholder="请选择环境" clearable style="width: 100%">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="执行引擎">
          <el-radio-group v-model="executeForm.engine">
            <el-radio label="requests">Requests</el-radio>
            <el-radio label="httprunner">HttpRunner</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showExecuteDialog = false">取消</el-button>
          <el-button type="primary" @click="confirmExecute" :loading="executing">
            执行
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Execution History Dialog -->
    <el-dialog v-model="showHistory" title="执行历史" width="800px">
      <el-table :data="executionHistory" v-loading="loadingResult" max-height="500">
        <el-table-column label="执行时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'passed' ? 'success' : 'danger'" size="small">
              {{ row.status === 'passed' ? '通过' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="步骤统计" width="150">
          <template #default="{ row }">
            <span class="text-success">{{ row.passed_steps }}</span> / 
            <span class="text-danger">{{ row.failed_steps }}</span> / 
            {{ row.total_steps }}
          </template>
        </el-table-column>
        <el-table-column prop="execution_time" label="耗时(ms)" width="120">
          <template #default="{ row }">
            {{ row.execution_time.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="executed_by.username" label="执行人" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewHistoryResult(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- Step Result Detail Dialog -->
    <el-dialog v-model="showResultDetail" title="步骤执行详情" width="900px" top="5vh">
      <div v-if="currentStepResult" class="result-detail-container">
        <div class="result-header">
          <div class="result-info">
            <el-tag :type="currentStepResult.passed ? 'success' : 'danger'" effect="dark">
              {{ currentStepResult.passed ? '通过' : '失败' }}
            </el-tag>
            <span class="method">{{ currentStepResult.method }}</span>
            <span class="url">{{ currentStepResult.url }}</span>
          </div>
          <div class="result-stats">
            <span class="stat">状态码: <strong>{{ currentStepResult.status_code }}</strong></span>
            <span class="stat">耗时: <strong>{{ currentStepResult.response_time.toFixed(2) }} ms</strong></span>
          </div>
        </div>

        <el-tabs type="border-card" class="result-tabs">
          <el-tab-pane label="响应体">
            <pre class="code-block">{{ formatJson(currentStepResult.response_json || currentStepResult.response_body) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="响应头">
            <pre class="code-block">{{ formatJson(currentStepResult.response_headers) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="请求体">
            <pre class="code-block">{{ formatJson(currentStepResult.request_body) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="请求头">
            <pre class="code-block">{{ formatJson(currentStepResult.request_headers) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="断言结果">
            <el-table :data="currentStepResult.assertions || []" size="small">
              <el-table-column prop="source" label="来源" width="100" />
              <el-table-column prop="property" label="属性" width="150" />
              <el-table-column prop="operator" label="操作符" width="100" />
              <el-table-column prop="expected" label="预期值" />
              <el-table-column prop="actual" label="实际值" />
              <el-table-column prop="passed" label="结果" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                    {{ row.passed ? '通过' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>

        <div v-if="currentStepResult.error" class="error-msg">
          <h4>错误详情:</h4>
          <p>{{ currentStepResult.error }}</p>
        </div>
      </div>
    </el-dialog>

    <!-- Full Execution Report Dialog -->
    <el-dialog v-model="showFullReport" title="完整执行报告" width="1000px" top="5vh">
      <div v-if="latestResult" class="full-report-container">
        <div class="report-summary">
          <el-descriptions title="执行概览" :column="3" border>
            <el-descriptions-item label="状态">
              <el-tag :type="latestResult.status === 'passed' ? 'success' : 'danger'">
                {{ latestResult.status === 'passed' ? '通过' : '失败' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="执行时间">{{ new Date(latestResult.created_at).toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="总耗时">{{ latestResult.execution_time.toFixed(2) }} ms</el-descriptions-item>
            <el-descriptions-item label="通过步骤">{{ latestResult.passed_steps }}</el-descriptions-item>
            <el-descriptions-item label="失败步骤">{{ latestResult.failed_steps }}</el-descriptions-item>
            <el-descriptions-item label="总步骤">{{ latestResult.total_steps }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="report-steps">
          <h4>步骤详情</h4>
          <el-collapse>
            <el-collapse-item 
              v-for="res in latestResult.results" 
              :key="res.step_number" 
              :name="res.step_number"
            >
              <template #title>
                <div class="step-report-title">
                  <el-tag :type="res.passed ? 'success' : 'danger'" size="small" class="m-r-10">
                    {{ res.passed ? '通过' : '失败' }}
                  </el-tag>
                  <span class="step-num">步骤 {{ res.step_number }}:</span>
                  <span class="step-name">{{ res.name }}</span>
                  <span class="step-time">{{ res.response_time.toFixed(0) }}ms</span>
                </div>
              </template>
              
              <div class="step-report-content">
                <el-tabs type="card" size="small">
                  <el-tab-pane label="请求信息">
                    <div class="info-row"><strong>URL:</strong> {{ res.url }}</div>
                    <div class="info-row"><strong>Method:</strong> {{ res.method }}</div>
                    <div class="info-group">
                      <strong>Headers:</strong>
                      <pre class="mini-code">{{ formatJson(res.request_headers) }}</pre>
                    </div>
                    <div class="info-group" v-if="res.request_body">
                      <strong>Body:</strong>
                      <pre class="mini-code">{{ formatJson(res.request_body) }}</pre>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="响应信息">
                    <div class="info-row"><strong>Status:</strong> {{ res.status_code }}</div>
                    <div class="info-group">
                      <strong>Response Body:</strong>
                      <pre class="mini-code">{{ formatJson(res.response_json || res.response_body) }}</pre>
                    </div>
                  </el-tab-pane>
                  <el-tab-pane label="断言结果">
                    <el-table :data="res.assertions || []" size="small" border>
                      <el-table-column prop="property" label="属性" width="120" />
                      <el-table-column prop="operator" label="操作" width="100" />
                      <el-table-column prop="expected" label="预期" />
                      <el-table-column prop="actual" label="实际" />
                      <el-table-column label="结果" width="80">
                        <template #default="{ row }">
                          <span :class="row.passed ? 'text-success' : 'text-danger'">
                            {{ row.passed ? '通过' : '失败' }}
                          </span>
                        </template>
                      </el-table-column>
                    </el-table>
                  </el-tab-pane>
                </el-tabs>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Search, Refresh, VideoPlay, Plus, Edit, Delete, 
  Rank, Check, Connection, Timer, Clock, Close, Warning, ArrowRight 
} from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import api from '@/utils/api'
import KeyValueEditor from './components/KeyValueEditor.vue'

// Data
const projects = ref([])
const selectedProject = ref(null)
const loading = ref(false)
const testCases = ref([])
const searchText = ref('')
const selectedCase = ref(null)
const steps = ref([])
const latestResult = ref(null)
const loadingResult = ref(false)
const executionHistory = ref([])
const showHistory = ref(false)
const showResultDetail = ref(false)
const showFullReport = ref(false)
const currentStepResult = ref(null)

// TestCase Form
const showCaseDialog = ref(false)
const savingCase = ref(false)
const caseFormRef = ref(null)
const testCaseForm = reactive({
  id: null,
  name: '',
  description: '',
  priority: 'medium',
  status: 'draft'
})
const caseRules = {
  name: [{ required: true, message: '请输入用例名称', trigger: 'blur' }]
}

// Interface Selector
const showInterfaceSelector = ref(false)
const loadingInterfaces = ref(false)
const allInterfaces = ref([])
const interfaceSearchText = ref('')
const selectedInterfaces = ref([])

// Step Editor
const showStepEditor = ref(false)
const savingStep = ref(false)
const stepActiveTab = ref('basic')
const editingStepForm = ref(null)
const stepBodyRaw = ref('')

// Execution
const showExecuteDialog = ref(false)
const executing = ref(false)
const environments = ref([])
const executeForm = ref({
  environment_id: '',
  engine: 'requests'
})

// Computed
const filteredTestCases = computed(() => {
  let list = testCases.value
  if (searchText.value) {
    const lower = searchText.value.toLowerCase()
    list = list.filter(c => 
      c.name.toLowerCase().includes(lower) || 
      (c.description && c.description.toLowerCase().includes(lower))
    )
  }
  return list
})

const filteredInterfaces = computed(() => {
  return allInterfaces.value
})

// Watchers
watch(stepBodyRaw, (newVal) => {
  if (editingStepForm.value && editingStepForm.value.body.type !== 'none') {
    try {
      if (editingStepForm.value.body.type === 'json') {
        editingStepForm.value.body.data = JSON.parse(newVal)
      } else {
        editingStepForm.value.body.data = newVal
      }
    } catch (e) {
      editingStepForm.value.body.data = newVal
    }
  }
})

// Methods - Project & Initial Load
const loadProjects = async () => {
  try {
    const res = await api.get('/api-testing/projects/')
    projects.value = res.data.results || res.data
    if (projects.value.length > 0 && !selectedProject.value) {
      selectedProject.value = projects.value[0].id
      onProjectChange()
    }
  } catch (error) {
    ElMessage.error('加载项目失败')
  }
}

const onProjectChange = () => {
  selectedCase.value = null
  steps.value = []
  fetchTestCases()
  fetchInterfaces()
}

// Methods - TestCase CRUD
const fetchTestCases = async () => {
  if (!selectedProject.value) return
  loading.value = true
  try {
    const res = await api.get('/api-testing/testcases/', {
      params: { project: selectedProject.value }
    })
    testCases.value = res.data.results || res.data
  } catch (error) {
    ElMessage.error('加载用例失败')
  } finally {
    loading.value = false
  }
}

const openTestCaseDialog = (row = null) => {
  if (row) {
    Object.assign(testCaseForm, {
      id: row.id,
      name: row.name,
      description: row.description,
      priority: row.priority,
      status: row.status
    })
  } else {
    Object.assign(testCaseForm, {
      id: null,
      name: '',
      description: '',
      priority: 'medium',
      status: 'draft'
    })
  }
  showCaseDialog.value = true
}

const saveTestCase = async () => {
  if (!caseFormRef.value) return
  await caseFormRef.value.validate(async (valid) => {
    if (!valid) return
    savingCase.value = true
    try {
      const data = { ...testCaseForm, project: selectedProject.value }
      if (testCaseForm.id) {
        await api.put(`/api-testing/testcases/${testCaseForm.id}/`, data)
        ElMessage.success('更新成功')
      } else {
        await api.post('/api-testing/testcases/', data)
        ElMessage.success('创建成功')
      }
      showCaseDialog.value = false
      fetchTestCases()
    } catch (error) {
      ElMessage.error('保存失败')
    } finally {
      savingCase.value = false
    }
  })
}

const handleDeleteCase = (row) => {
  ElMessageBox.confirm(`确定要删除用例 "${row.name}" 吗？`, '警告', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    confirmButtonClass: 'el-button--danger'
  }).then(async () => {
    try {
      await api.delete(`/api-testing/testcases/${row.id}/`)
      ElMessage.success('删除成功')
      if (selectedCase.value?.id === row.id) {
        selectedCase.value = null
        steps.value = []
      }
      fetchTestCases()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const selectCase = async (testCase) => {
  selectedCase.value = testCase
  fetchSteps(testCase.id)
  fetchLatestResult(testCase.id)
}

// Methods - Execution Results
const fetchLatestResult = async (caseId) => {
  loadingResult.value = true
  try {
    const res = await api.get(`/api-testing/testcases/${caseId}/latest-execution/`)
    latestResult.value = res.data
  } catch (error) {
    console.error('加载最新执行结果失败', error)
  } finally {
    loadingResult.value = false
  }
}

const fetchExecutionHistory = async () => {
  if (!selectedCase.value) return
  try {
    const res = await api.get(`/api-testing/testcases/${selectedCase.value.id}/executions/`)
    executionHistory.value = res.data
    showHistory.value = true
  } catch (error) {
    ElMessage.error('加载执行历史失败')
  }
}

const getStepResult = (stepNumber) => {
  if (!latestResult.value || !latestResult.value.results) return null
  return latestResult.value.results.find(r => r.step_number === stepNumber)
}

const viewHistoryResult = (execution) => {
  console.log('Loading history result:', execution)
  // 确保数据格式统一
  const resultData = {
    ...execution,
    passed_count: execution.passed_steps,
    failed_count: execution.failed_steps,
    total_count: execution.total_steps
  }
  latestResult.value = resultData
  showHistory.value = false
  ElMessage({
    message: '已加载历史执行快照，点击步骤状态可查看报文详情',
    type: 'success',
    duration: 5000,
    showClose: true
  })
}

const openStepResult = (step) => {
  const result = getStepResult(step.step_number)
  if (result) {
    currentStepResult.value = result
    showResultDetail.value = true
  }
}

const formatJson = (json) => {
  if (!json) return ''
  if (typeof json === 'string') {
    try {
      return JSON.stringify(JSON.parse(json), null, 2)
    } catch (e) {
      return json
    }
  }
  return JSON.stringify(json, null, 2)
}

// Methods - Steps
const fetchSteps = async (caseId) => {
  try {
    const res = await api.get('/api-testing/teststeps/', {
      params: { test_case: caseId }
    })
    steps.value = (res.data.results || res.data).sort((a, b) => a.step_number - b.step_number)
  } catch (error) {
    ElMessage.error('加载步骤失败')
    steps.value = []
  }
}

const handleStepSort = async () => {
  // Update step numbers
  const updatedSteps = steps.value.map((step, index) => ({
    id: step.id,
    step_number: index + 1
  }))
  
  // Send batch update if your backend supports it, otherwise update one by one
  // For simplicity, let's assume we update them sequentially or have a bulk endpoint
  try {
    for (const item of updatedSteps) {
      await api.patch(`/api-testing/teststeps/${item.id}/`, { step_number: item.step_number })
    }
    ElMessage.success('排序已更新')
  } catch (error) {
    ElMessage.error('更新排序失败')
    fetchSteps(selectedCase.value.id)
  }
}

const toggleStep = async (step) => {
  try {
    await api.patch(`/api-testing/teststeps/${step.id}/`, { enable: step.enable })
    ElMessage.success(step.enable ? '已启用' : '已禁用')
  } catch (error) {
    ElMessage.error('操作失败')
    step.enable = !step.enable
  }
}

const deleteStep = (step) => {
  ElMessageBox.confirm('确定要删除此步骤吗？', '提示', { type: 'warning' }).then(async () => {
    try {
      await api.delete(`/api-testing/teststeps/${step.id}/`)
      ElMessage.success('删除成功')
      fetchSteps(selectedCase.value.id)
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// Methods - Interface Selection & Add Steps
const fetchInterfaces = async () => {
  if (!selectedProject.value) return
  loadingInterfaces.value = true
  try {
    const params = { 
      project: selectedProject.value,
      page: 1,
      page_size: 10
    }
    // 如果有搜索文本，则添加搜索参数
    if (interfaceSearchText.value) {
      params.search = interfaceSearchText.value
    }
    
    const res = await api.get('/api-testing/requests/', { params })
    allInterfaces.value = res.data.results || res.data
  } catch (error) {
    ElMessage.error('加载接口库失败')
  } finally {
    loadingInterfaces.value = false
  }
}

// 监听搜索文本变化，触发搜索 (增加防抖)
let searchTimer = null
watch(interfaceSearchText, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchInterfaces()
  }, 300)
})

const handleInterfaceSelectionChange = (val) => {
  selectedInterfaces.value = val
}

const openInterfaceSelector = () => {
  interfaceSearchText.value = ''
  selectedInterfaces.value = []
  fetchInterfaces()
  showInterfaceSelector.value = true
}

const addStepsFromInterfaces = async () => {
  if (!selectedCase.value) return
  
  const startNum = steps.value.length + 1
  try {
    for (let i = 0; i < selectedInterfaces.value.length; i++) {
      const iface = selectedInterfaces.value[i]
      const stepData = {
        test_case: selectedCase.value.id,
        step_number: startNum + i,
        name: iface.name,
        api_request_id: iface.id,
        method: iface.method,
        url: iface.url,
        headers: iface.headers,
        params: iface.params,
        body: iface.body || { type: 'none', data: {}, form_data: [] },
        assertions: iface.assertions || [],
        extract_rules: iface.extract_rules || []
      }
      await api.post('/api-testing/teststeps/', stepData)
    }
    ElMessage.success(`成功添加 ${selectedInterfaces.value.length} 个步骤`)
    showInterfaceSelector.value = false
    selectedInterfaces.value = []
    fetchSteps(selectedCase.value.id)
  } catch (error) {
    ElMessage.error('添加步骤失败')
  }
}

// Methods - Step Editing
const editStep = (step) => {
  editingStepForm.value = JSON.parse(JSON.stringify(step))
  // Ensure objects exist
  if (!editingStepForm.value.headers) editingStepForm.value.headers = []
  if (!editingStepForm.value.params) editingStepForm.value.params = []
  if (!editingStepForm.value.body) {
    editingStepForm.value.body = { type: 'none', data: {}, form_data: [] }
  } else if (!editingStepForm.value.body.form_data) {
    editingStepForm.value.body.form_data = []
  }
  
  // Format body for editor
  if (editingStepForm.value.body.type === 'json') {
    stepBodyRaw.value = JSON.stringify(editingStepForm.value.body.data, null, 2)
  } else {
    stepBodyRaw.value = editingStepForm.value.body.data || ''
  }
  
  stepActiveTab.value = 'basic'
  showStepEditor.value = true
}

const saveStep = async () => {
  savingStep.value = true
  try {
    // Validate JSON if type is json
    if (editingStepForm.value.body.type === 'json' && stepBodyRaw.value) {
      try {
        editingStepForm.value.body.data = JSON.parse(stepBodyRaw.value)
      } catch (e) {
        ElMessage.error('JSON格式错误')
        savingStep.value = false
        return
      }
    } else {
      editingStepForm.value.body.data = stepBodyRaw.value
    }

    const data = {
      ...editingStepForm.value,
      api_request_id: editingStepForm.value.api_request?.id || null
    }
    delete data.api_request // Use api_request_id for update

    await api.put(`/api-testing/teststeps/${editingStepForm.value.id}/`, data)
    ElMessage.success('步骤保存成功')
    showStepEditor.value = false
    fetchSteps(selectedCase.value.id)
  } catch (error) {
    ElMessage.error('保存步骤失败')
  } finally {
    savingStep.value = false
  }
}

const addStepAssertion = () => {
  if (!editingStepForm.value.assertions) editingStepForm.value.assertions = []
  editingStepForm.value.assertions.push({ name: '新断言', type: 'status_code', expected: '200' })
}

const addStepExtract = () => {
  if (!editingStepForm.value.extract_rules) editingStepForm.value.extract_rules = []
  editingStepForm.value.extract_rules.push({ variable_name: '', type: 'json_path', json_path: '' })
}

// Methods - Execution
const fetchEnvironments = async () => {
  try {
    const res = await api.get('/api-testing/environments/')
    environments.value = res.data.results || res.data
  } catch (error) {
    ElMessage.error('加载环境列表失败')
  }
}

const runCase = () => {
  if (!selectedCase.value) return
  fetchEnvironments()
  showExecuteDialog.value = true
}

const confirmExecute = async () => {
  executing.value = true
  try {
    const res = await api.post(`/api-testing/testcases/${selectedCase.value.id}/execute/`, executeForm.value)
    ElMessage.success('执行成功')
    latestResult.value = res.data
    showExecuteDialog.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '执行失败')
  } finally {
    executing.value = false
  }
}

// Helpers
const getStatusType = (s) => {
  const map = { draft: 'info', ready: 'success', running: 'warning', passed: 'success', failed: 'danger' }
  return map[s] || 'info'
}
const getStatusLabel = (s) => {
  const map = { draft: '草稿', ready: '就绪', running: '执行中', passed: '通过', failed: '失败' }
  return map[s] || s
}
const getPriorityType = (p) => {
  const map = { high: 'danger', medium: 'warning', low: 'info' }
  return map[p] || 'info'
}
const getPriorityLabel = (p) => {
  const map = { high: '高', medium: '中', low: '低' }
  return map[p] || p
}
const getMethodColor = (m) => {
  const map = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return map[m] || 'info'
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped lang="scss">
.page-container {
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
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
  &::before {
    content: "";
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 4px;
    height: 20px;
    background: #409eff;
    border-radius: 2px;
  }
}

.main-content {
  flex: 1;
  overflow: hidden;
  display: flex;
}

.card-container {
  flex: 1;
  width: 100%;
  height: 100%;
  background-color: #fff;
  display: flex;
  flex-direction: column;
}

.case-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 320px;
  border-right: 1px solid #e4e7ed;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 15px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
  .filter-select {
    width: 100%;
    margin-bottom: 10px;
  }
  .sidebar-actions {
    display: flex;
    gap: 8px;
  }
}

.case-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.case-item {
  padding: 12px;
  border-radius: 6px;
  background: white;
  border: 1px solid #ebeef5;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
  &:hover {
    border-color: #409eff;
    background: #f0f7ff;
    .item-actions { opacity: 1; }
  }
  &.active {
    border-color: #409eff;
    background: #ecf5ff;
    box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  }
}

.case-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  .case-name {
    font-weight: 600;
    color: #303133;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .item-actions {
    opacity: 0;
    transition: opacity 0.2s;
    display: flex;
    gap: 4px;
  }
}

.case-item-meta {
  display: flex;
  gap: 8px;
  .priority-tag {
    font-size: 10px;
  }
}

.case-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
}

.detail-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
  .title-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
    h2 { margin: 0; font-size: 22px; }
  }
  .description {
    color: #909399;
    font-size: 14px;
    margin: 0;
  }
}

.steps-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  .section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    h3 { margin: 0; font-size: 18px; }
    .tip { font-size: 12px; color: #909399; }
  }
}

.steps-list-container {
  flex: 1;
}

.step-card {
  background: white;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 12px;
  transition: box-shadow 0.2s;
  &:hover {
    box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  }
}

.step-main {
  display: flex;
  align-items: center;
  padding: 16px;
  .drag-handle {
    cursor: grab;
    color: #c0c4cc;
    margin-right: 12px;
    &:active { cursor: grabbing; }
  }
  .step-index {
    width: 24px;
    height: 24px;
    background: #f0f2f5;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    color: #909399;
    margin-right: 16px;
  }
  .step-info {
    flex: 1;
    overflow: hidden;
    .step-name-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
      .step-name { font-weight: 600; font-size: 15px; }
    }
    .step-url-row {
      display: flex;
      align-items: center;
      gap: 8px;
      .method-tag { font-weight: bold; }
      .step-url {
        font-size: 13px;
        color: #606266;
        font-family: monospace;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
  .step-actions {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-left: 20px;
  }
}

.step-footer {
  padding: 8px 16px;
  background: #fafafa;
  border-top: 1px solid #f0f2f5;
  display: flex;
  gap: 20px;
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #909399;
  }
}

.assertion-item-row, .extract-item-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-steps {
  padding: 40px 0;
}

/* Execution Summary Styles */
.execution-summary-card {
  margin-bottom: 24px;
  padding: 16px 20px;
  border-radius: 8px;
  border-left: 5px solid #dcdfe6;
  background: #f8f9fa;
  
  &.passed {
    border-left-color: #67c23a;
    background: #f0f9eb;
  }
  
  &.failed {
    border-left-color: #f56c6c;
    background: #fef0f0;
  }
  
  .summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .status-info {
    display: flex;
    align-items: center;
    gap: 16px;
    
    .execution-time {
      font-size: 14px;
      color: #606266;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    
    .duration {
      font-size: 14px;
      color: #909399;
    }
  }
  
  .stats {
    display: flex;
    gap: 20px;
    font-size: 14px;
    
    .stat-item {
      strong { font-size: 16px; }
      &.passed strong { color: #67c23a; }
      &.failed strong { color: #f56c6c; }
    }
  }
}

.step-card {
  &.has-result {
    border-left: 3px solid #dcdfe6;
    &.passed { border-left-color: #67c23a; }
    &.failed { border-left-color: #f56c6c; }
  }
}

.step-status-tag {
  margin-left: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.step-duration {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.step-error-info {
  margin: 0 16px 12px 16px;
  padding: 8px 12px;
  background: #fff5f5;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }

.clickable {
  cursor: pointer;
  &:hover {
    opacity: 0.8;
  }
}

.result-detail-container {
  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid #ebeef5;
    
    .result-info {
      display: flex;
      align-items: center;
      gap: 12px;
      .method { font-weight: bold; color: #409eff; }
      .url { color: #606266; font-size: 14px; }
    }
    
    .result-stats {
      display: flex;
      gap: 20px;
      font-size: 14px;
      .stat strong { color: #303133; }
    }
  }
  
  .result-tabs {
    margin-bottom: 20px;
  }
  
  .code-block {
    background: #282c34;
    color: #abb2bf;
    padding: 15px;
    border-radius: 4px;
    margin: 0;
    max-height: 400px;
    overflow: auto;
    font-family: 'Courier New', Courier, monospace;
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-all;
  }
  
  .error-msg {
    margin-top: 20px;
    padding: 12px;
    background: #fef0f0;
    border-left: 4px solid #f56c6c;
    color: #f56c6c;
    h4 { margin: 0 0 8px 0; }
    p { margin: 0; font-size: 13px; }
  }
}

.full-report-container {
  .report-summary {
    margin-bottom: 24px;
  }
  
  .report-steps {
    h4 { margin-bottom: 16px; color: #303133; }
  }
  
  .step-report-title {
    display: flex;
    align-items: center;
    width: 100%;
    .m-r-10 { margin-right: 10px; }
    .step-num { color: #909399; font-size: 13px; margin-right: 8px; }
    .step-name { font-weight: 500; flex: 1; }
    .step-time { color: #909399; font-size: 12px; margin-right: 20px; }
  }
  
  .step-report-content {
    padding: 10px;
    
    .info-row {
      margin-bottom: 10px;
      font-size: 13px;
      strong { width: 80px; display: inline-block; color: #606266; }
    }
    
    .info-group {
      margin-top: 10px;
      strong { display: block; margin-bottom: 5px; color: #606266; font-size: 13px; }
    }
    
    .mini-code {
      background: #f8f9fa;
      padding: 10px;
      border-radius: 4px;
      font-size: 12px;
      max-height: 200px;
      overflow: auto;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
      border: 1px solid #e4e7ed;
    }
  }
}

/* Step Editor Styles */
.step-editor-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.step-editor-header {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  .method-url-row {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
    align-items: center;
  }
  .url-input { flex: 1; }
  .name-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .name-input {
      flex: 1;
      margin-right: 20px;
      :deep(.el-input__inner) { font-size: 16px; font-weight: bold; }
    }
  }
}

.config-section {
  padding: 10px 0;
  h4 { margin: 0 0 15px 0; font-size: 14px; color: #606266; }
}

.assertion-card-edit, .extract-card-edit {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 15px;
  background: white;
  .card-header {
    padding: 8px 12px;
    background: #fafafa;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .card-body {
    padding: 12px;
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }
}

.code-input :deep(.el-textarea__inner) {
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  background: #fafafa;
}
</style>
