<template>
  <BasePage title="SQL 生成">
    <template #actions>
      <el-button type="primary" size="small" @click="generateSqlAction">
        <el-icon><ChatDotRound /></el-icon>
        生成 SQL
      </el-button>
      <el-button size="small" @click="executeSqlAction" :disabled="!generatedSql">
        <el-icon><VideoPlay /></el-icon>
        执行 SQL
      </el-button>
      <el-button size="small" @click="saveQueryDialogVisible = true" :disabled="!generatedSql">
        <el-icon><Document /></el-icon>
        保存查询
      </el-button>
    </template>
    
    <div class="generation-content">
      <!-- 配置选择和自然语言输入 -->
      <div class="input-section">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="SQL生成配置">
              <el-select
                v-model="selectedConfig"
                placeholder="选择 AI SQL 配置"
                style="width: 100%"
                @change="handleConfigChange"
              >
                <el-option
                  v-for="config in configs"
                  :key="config.id"
                  :label="config.name"
                  :value="config.id"
                >
                  <span>{{ config.name }}</span>
                  <span v-if="!config.is_active" style="color: #909399; font-size: 12px; margin-left: 10px;">(已停用)</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="自然语言查询">
          <el-input
            v-model="naturalLanguage"
            type="textarea"
            :rows="4"
            placeholder="请输入您的查询需求，例如：查询最近7天的活跃用户数量"
            resize="vertical"
          />
        </el-form-item>
      </div>
      
      <!-- 生成的SQL和执行结果 -->
      <div class="result-section">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="生成的SQL" name="sql">
            <div class="sql-content">
              <div v-if="loading" class="loading-sql">
                <el-skeleton :rows="10" animated />
              </div>
              <div v-else-if="errorMessage" class="error-message">
                <el-alert
                  title="生成失败"
                  :description="errorMessage"
                  type="error"
                  show-icon
                  :closable="false"
                />
              </div>
              <div v-else-if="generatedSql" class="generated-sql">
                <pre><code>{{ generatedSql }}</code></pre>
              </div>
              <div v-else class="empty-sql">
                <el-empty description="输入自然语言查询后点击生成按钮" />
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="执行结果" name="result">
            <div class="execution-result">
              <div v-if="executionLoading" class="loading-result">
                <el-skeleton :rows="15" animated />
              </div>
              <div v-else-if="executionError" class="error-message">
                <el-alert
                  title="执行失败"
                  :description="executionError"
                  type="error"
                  show-icon
                  :closable="false"
                />
              </div>
              <div v-else-if="executionResult" class="result-data">
                <div class="result-header">
                  <div class="result-stats">
                    <span class="stat-item">
                      <el-icon><Document /></el-icon>
                      行数: {{ executionResult.row_count || 0 }}
                    </span>
                    <span class="stat-item">
                      <el-icon><Timer /></el-icon>
                      执行时间: {{ executionResult.execution_time || 0 }}ms
                    </span>
                  </div>
                  <el-button size="small" type="primary" @click="exportResult">
                    <el-icon><Download /></el-icon>
                    导出结果
                  </el-button>
                </div>
                
                <el-table :data="executionResult.rows || []" stripe style="width: 100%" max-height="500px">
                  <el-table-column
                    v-for="(col, index) in executionResult.columns || []"
                    :key="index"
                    :prop="col"
                    :label="col"
                    sortable
                    show-overflow-tooltip
                  />
                </el-table>
              </div>
              <div v-else class="empty-result">
                <el-empty description="执行SQL后显示结果" />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
    
    <!-- 保存查询对话框 -->
    <el-dialog
      v-model="saveQueryDialogVisible"
      title="保存查询"
      width="500px"
    >
      <el-form :model="saveQueryForm" label-width="100px">
        <el-form-item label="查询名称" required>
          <el-input
            v-model="saveQueryForm.name"
            placeholder="请输入查询名称"
            maxlength="100"
          />
        </el-form-item>
        
        <el-form-item label="查询描述">
          <el-input
            v-model="saveQueryForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入查询描述"
            maxlength="500"
          />
        </el-form-item>
        
        <el-form-item label="所属项目">
          <el-select
            v-model="saveQueryForm.project_id"
            placeholder="请选择所属项目"
            style="width: 100%"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="是否收藏">
          <el-switch v-model="saveQueryForm.is_favorite" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="saveQueryDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveQuery" :loading="savingQuery">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 历史记录 -->
    <el-card shadow="hover" class="history-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>历史记录</span>
        </div>
      </template>
      
      <div class="history-content">
        <el-table :data="historyList" stripe style="width: 100%">
          <el-table-column prop="natural_language" label="自然语言查询" show-overflow-tooltip width="400" />
          <el-table-column prop="generated_sql" label="生成的SQL" show-overflow-tooltip width="400" />
          <el-table-column prop="status" label="状态">
            <template #default="scope">
              <el-tag
                :type="scope.row.status === 'SUCCESS' ? 'success' : (scope.row.status === 'FAILED' ? 'danger' : 'warning')"
                size="small"
              >
                {{ scope.row.status === 'SUCCESS' ? '成功' : (scope.row.status === 'FAILED' ? '失败' : '等待中') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="生成时间" width="180" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                @click="reuseQuery(scope.row)"
                :disabled="scope.row.status !== 'SUCCESS'"
              >
                复用
              </el-button>
              <el-button
                type="success"
                size="small"
                @click="showSql(scope.row)"
                :disabled="scope.row.status !== 'SUCCESS'"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

  </BasePage>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, VideoPlay, Download, Document, Timer, Star } from '@element-plus/icons-vue'
import {
  getVannaConfigs,
  generateSql,
  getSqlGenerations,
  executeSql,
  getDataFactoryProjects,
  createSavedQuery
} from '@/api/data-factory'

// 配置和输入
const configs = ref([])
const selectedConfig = ref('')
const naturalLanguage = ref('') // 确保初始值为空字符串，不是null或undefined
const activeTab = ref('sql')

// 生成结果
const generatedSql = ref('')
const currentSqlGenerationId = ref(null) // 保存当前生成的SQL记录ID
const loading = ref(false)
const errorMessage = ref('')

// 执行结果
const executionResult = ref(null)
const executionLoading = ref(false)
const executionError = ref('')

// 历史记录
const historyList = ref([])

// 保存查询相关
const saveQueryDialogVisible = ref(false)
const savingQuery = ref(false)
const projects = ref([])
const saveQueryForm = ref({
  name: '',
  description: '',
  project_id: '',
  is_favorite: false
})

// 加载配置列表
const loadConfigs = async () => {
  try {
    const res = await getVannaConfigs().catch(() => ({ data: { results: [] } }))
    configs.value = res.data.results || []
    
    // 如果没有配置，添加模拟配置
    if (configs.value.length === 0) {
      configs.value = [
        {
          id: 1,
          name: '默认Vanna配置',
          is_active: true
        }
      ]
      selectedConfig.value = configs.value[0].id
      ElMessage.info('使用模拟Vanna配置')
    } else {
      selectedConfig.value = configs.value[0].id
      ElMessage.success('配置加载成功')
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    // 使用模拟配置
    configs.value = [
      {
        id: 1,
        name: '默认Vanna配置',
        is_active: true
      }
    ]
    selectedConfig.value = configs.value[0].id
    ElMessage.info('加载配置失败，使用模拟配置')
  }
}

// 加载项目列表
const loadProjects = async () => {
  try {
    const res = await getDataFactoryProjects().catch(() => ({ data: { results: [] } }))
    projects.value = res.data.results || []
    
    // 如果没有项目，添加模拟项目
    if (projects.value.length === 0) {
      projects.value = [
        {
          id: 1,
          name: '默认项目'
        }
      ]
      // 自动选择第一个项目
      if (projects.value.length > 0) {
        saveQueryForm.value.project_id = projects.value[0].id
      }
    } else {
      // 自动选择第一个项目
      if (projects.value.length > 0) {
        saveQueryForm.value.project_id = projects.value[0].id
      }
    }
  } catch (error) {
    console.error('加载项目列表失败:', error)
    // 使用模拟项目
    projects.value = [
      {
        id: 1,
        name: '默认项目'
      }
    ]
    saveQueryForm.value.project_id = projects.value[0].id
  }
}

// 保存查询
const saveQuery = async () => {
  // 表单验证
  if (!saveQueryForm.value.name.trim()) {
    ElMessage.warning('请输入查询名称')
    return
  }
  
  if (!saveQueryForm.value.project_id) {
    ElMessage.warning('请选择所属项目')
    return
  }
  
  if (!generatedSql.value) {
    ElMessage.warning('没有可保存的SQL')
    return
  }
  
  // 确保自然语言查询有值
  let nlValue = naturalLanguage.value
  if (!nlValue || nlValue.trim() === '') {
    // 如果自然语言查询为空，尝试从生成SQL记录中获取
    if (historyList.value.length > 0) {
      // 从最近的历史记录中获取自然语言查询
      const latestHistory = historyList.value[0]
      nlValue = latestHistory.natural_language || '未提供自然语言查询'
    } else {
      nlValue = '未提供自然语言查询'
    }
  }
  
  savingQuery.value = true
  
  try {
    // 确保所有字段都有正确的类型
    const saveData = {
      name: saveQueryForm.value.name.trim(),
      description: saveQueryForm.value.description || '', // 确保是字符串
      project: parseInt(saveQueryForm.value.project_id), // 确保是数字类型
      natural_language: nlValue.trim(), // 确保是字符串且非空
      generated_sql: generatedSql.value.trim(), // 确保是字符串且非空
      is_favorite: !!saveQueryForm.value.is_favorite // 确保是布尔值
    }
    
    console.log('准备保存的查询数据:', saveData)
    
    // 使用原有的createSavedQuery函数
    const res = await createSavedQuery(saveData)
    
    console.log('API调用结果:', res)
    
    ElMessage.success('查询保存成功')
    
    // 关闭对话框
    saveQueryDialogVisible.value = false
    
    // 重置表单
    saveQueryForm.value = {
      name: '',
      description: '',
      project_id: projects.value.length > 0 ? projects.value[0].id : '',
      is_favorite: false
    }
    
  } catch (error) {
    console.error('保存查询失败:', error)
    if (error.response && error.response.data) {
      console.error('错误数据:', error.response.data)
      // 显示更友好的错误信息
      if (error.response.data.error) {
        const errorMsg = error.response.data.error
        if (typeof errorMsg === 'object') {
          // 处理字段验证错误
          let errorText = '保存失败：'
          for (const [field, messages] of Object.entries(errorMsg)) {
            errorText += `${field}：${messages[0].en || messages[0]}；`
          }
          ElMessage.error(errorText)
        } else {
          ElMessage.error('保存查询失败: ' + errorMsg)
        }
      } else {
        ElMessage.error('保存查询失败: ' + JSON.stringify(error.response.data))
      }
    } else {
      ElMessage.error('保存查询失败: ' + error.message)
    }
  } finally {
    savingQuery.value = false
  }
}

// 加载历史记录
const loadHistory = async () => {
  try {
    const res = await getSqlGenerations({ page_size: 10, ordering: '-created_at' }).catch(() => ({ data: { results: [] } }))
    historyList.value = res.data.results || []
    
    // 如果没有历史记录，添加模拟记录
    if (historyList.value.length === 0) {
      historyList.value = [
        {
          id: 1,
          natural_language: '查询最近7天的用户注册数',
          generated_sql: 'SELECT DATE(created_at) as register_date, COUNT(*) as user_count FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY DATE(created_at) ORDER BY register_date DESC',
          status: 'SUCCESS',
          config: 1,
          created_at: new Date().toISOString()
        },
        {
          id: 2,
          natural_language: '查询活跃用户的平均年龄',
          generated_sql: 'SELECT AVG(age) as avg_age FROM users WHERE last_login >= DATE_SUB(NOW(), INTERVAL 30 DAY)',
          status: 'SUCCESS',
          config: 1,
          created_at: new Date(Date.now() - 3600000).toISOString()
        },
        {
          id: 3,
          natural_language: '查询每个部门的员工数量',
          generated_sql: 'SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department ORDER BY employee_count DESC',
          status: 'SUCCESS',
          config: 1,
          created_at: new Date(Date.now() - 7200000).toISOString()
        }
      ]
      ElMessage.info('使用模拟历史记录')
    } else {
      ElMessage.success('历史记录加载成功')
    }
  } catch (error) {
    console.error('加载历史记录失败:', error)
    // 使用模拟历史记录
    historyList.value = [
      {
        id: 1,
        natural_language: '查询最近7天的用户注册数',
        generated_sql: 'SELECT DATE(created_at) as register_date, COUNT(*) as user_count FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY DATE(created_at) ORDER BY register_date DESC',
        status: 'SUCCESS',
        config: 1,
        created_at: new Date().toISOString()
      },
      {
        id: 2,
        natural_language: '查询活跃用户的平均年龄',
        generated_sql: 'SELECT AVG(age) as avg_age FROM users WHERE last_login >= DATE_SUB(NOW(), INTERVAL 30 DAY)',
        status: 'SUCCESS',
        config: 1,
        created_at: new Date(Date.now() - 3600000).toISOString()
      }
    ]
    ElMessage.info('加载历史记录失败，使用模拟数据')
  }
}

// 生成SQL
const generateSqlAction = async () => {
  if (!selectedConfig.value) {
    ElMessage.warning('请选择Vanna配置')
    return
  }
  
  if (!naturalLanguage.value.trim()) {
    ElMessage.warning('请输入自然语言查询')
    return
  }
  
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await generateSql({
      config_id: selectedConfig.value,
      natural_language: naturalLanguage.value
    })
    
    generatedSql.value = res.data.generated_sql || ''
    currentSqlGenerationId.value = res.data.id // 保存SQL生成记录ID
    
    if (res.data.status === 'FAILED') {
      errorMessage.value = res.data.error_message || '生成失败'
      generatedSql.value = ''
      currentSqlGenerationId.value = null
    } else {
      // 切换到SQL标签页
      activeTab.value = 'sql'
      // 更新历史记录
      loadHistory()
      ElMessage.success('SQL生成成功')
    }
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || '生成失败'
    generatedSql.value = ''
    currentSqlGenerationId.value = null
    console.error('生成SQL失败:', error)
  } finally {
    loading.value = false
  }
}

// 执行SQL
const executeSqlAction = async () => {
  if (!generatedSql.value) {
    ElMessage.warning('没有可执行的SQL')
    return
  }
  
  executionLoading.value = true
  executionError.value = ''
  executionResult.value = null
  try {
    let res
    // 如果有currentSqlGenerationId，使用已有的记录执行
    if (currentSqlGenerationId.value) {
      // 调用后端API执行SQL
      res = await executeSql(currentSqlGenerationId.value)
    } else {
      // 否则，先生成新的SQL记录，再执行
      // 这里需要调用generateSql API生成新记录
      const generateRes = await generateSql({
        config_id: selectedConfig.value,
        natural_language: naturalLanguage.value || '查询配置信息'
      })
      
      if (generateRes.data.status === 'SUCCESS') {
        currentSqlGenerationId.value = generateRes.data.id
        // 调用后端API执行SQL
        res = await executeSql(generateRes.data.id)
      } else {
        executionError.value = generateRes.data.error_message || '生成SQL失败'
        ElMessage.error('生成SQL失败')
        return
      }
    }
    
    // 使用后端返回的执行结果
    if (res.data) {
      if (res.data.execution_result) {
        // 转换执行结果格式：将二维数组转换为对象数组，以便el-table正确渲染
        const result = res.data.execution_result
        // 检查是否需要转换（如果是二维数组，则转换；如果已经是对象数组，则直接使用）
        if (result.rows && Array.isArray(result.rows) && result.rows.length > 0 && Array.isArray(result.rows[0])) {
          // 是二维数组，需要转换为对象数组
          const columns = result.columns
          const transformedRows = result.rows.map(row => {
            const obj = {}
            columns.forEach((col, index) => {
              obj[col] = row[index]
            })
            return obj
          })
          // 创建新的执行结果对象
          executionResult.value = {
            ...result,
            rows: transformedRows
          }
        } else {
          // 已经是对象数组，直接使用
          executionResult.value = result
        }
        // 切换到结果标签页
        activeTab.value = 'result'
        ElMessage.success('SQL执行成功')
      } else if (res.data.error_message) {
        executionError.value = res.data.error_message
        ElMessage.error('SQL执行失败')
      }
    } else {
      executionError.value = '执行结果格式错误'
      ElMessage.error('SQL执行失败')
    }
  } catch (error) {
    executionError.value = error.response?.data?.error || error.response?.data?.detail || '执行失败'
    console.error('执行SQL失败:', error)
    ElMessage.error('SQL执行失败')
  } finally {
    executionLoading.value = false
  }
}

// 复用历史查询
const reuseQuery = (row) => {
  naturalLanguage.value = row.natural_language
  // 检查row.config是否为对象，如果是，则取其id，否则直接使用
  selectedConfig.value = typeof row.config === 'object' && row.config !== null ? row.config.id : row.config
  generatedSql.value = row.generated_sql
  // 设置currentSqlGenerationId，以便后续执行SQL
  currentSqlGenerationId.value = row.id
  activeTab.value = 'sql'
  ElMessage.info('已复用历史查询')
}

// 查看SQL
const showSql = (row) => {
  generatedSql.value = row.generated_sql
  // 设置currentSqlGenerationId，以便后续执行SQL
  currentSqlGenerationId.value = row.id
  // 如果有执行结果，也一并显示
  if (row.execution_result) {
    executionResult.value = row.execution_result
  }
  activeTab.value = 'sql'
}

// 导出结果
const exportResult = () => {
  if (!executionResult.value) {
    ElMessage.warning('没有可导出的结果')
    return
  }
  
  // 简单的CSV导出
  const headers = executionResult.value.columns
  const rows = executionResult.value.rows
  
  // 根据rows的类型选择不同的处理方式
  let csvRows = []
  if (Array.isArray(rows) && rows.length > 0) {
    if (Array.isArray(rows[0])) {
      // 二维数组格式
      csvRows = rows.map(row => row.map(cell => `"${cell}"`).join(','))
    } else {
      // 对象数组格式
      csvRows = rows.map(row => headers.map(col => `"${row[col]}"`).join(','))
    }
  }
  
  // 创建CSV内容
  const headersLine = headers.join(',')
  const csvContent = [headersLine, ...csvRows].join('\n')
  
  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `sql_result_${new Date().getTime()}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  ElMessage.success('结果导出成功')
}

// 处理配置变更
const handleConfigChange = () => {
  // 配置变更时清空之前的生成结果
  generatedSql.value = ''
  errorMessage.value = ''
}

// 组件挂载时加载数据
onMounted(() => {
  loadConfigs()
  loadHistory()
  loadProjects()
})

// 监听保存查询对话框的显示状态
watch(saveQueryDialogVisible, (newVal) => {
  if (newVal) {
    // 打开对话框时刷新项目列表
    loadProjects()
  }
})
</script>

<style scoped>
/* 页面特定样式 */

.sql-generation-container {
  width: 100%;
  padding: 0;
}

.main-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}



.generation-content {
  margin-top: 20px;
}

.input-section {
  margin-bottom: 30px;
}

.result-section {
  margin-top: 30px;
}

.sql-content {
  background-color: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 20px;
  min-height: 300px;
}

.loading-sql {
  padding: 20px 0;
}

.generated-sql {
  background-color: #f6f8fa;
  border: 1px solid #e1e4e8;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
}

.generated-sql pre {
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #24292e;
}

.empty-sql {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 260px;
  color: #909399;
}

.execution-result {
  min-height: 300px;
}

.loading-result {
  padding: 20px 0;
}

.result-data {
  background-color: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 20px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e8e8e8;
}

.result-stats {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #666;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.empty-result {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 260px;
  color: #909399;
}

.history-card {
  margin-top: 20px;
}

.history-content {
  margin-top: 20px;
}

.error-message {
  margin-bottom: 20px;
}
</style>
