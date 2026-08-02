<template>
  <div class="report-detail" v-loading="loading">
    <div class="page-header">
      <el-button @click="goBack" :icon="ArrowLeft">返回</el-button>
      <div class="header-content">
        <h2>{{ report.name }}</h2>
        <el-tag :type="getTestTypeTag(report.test_type)" size="large">
          {{ getTestTypeText(report.test_type) }}
        </el-tag>
        <el-tag :type="getStatusType(report.status)">
          {{ getStatusText(report.status) }}
        </el-tag>
      </div>
      <div class="header-actions">
        <el-button type="warning" :icon="Warning" @click="openFileDefect">
          提缺陷
        </el-button>
        <el-button v-if="report.allure_url" type="success" @click="openAllureReport">
          <el-icon><Monitor /></el-icon>
          查看 Allure 报告
        </el-button>
        <el-dropdown @command="(cmd) => handleExport(cmd)">
          <el-button type="primary">
            <el-icon><Download /></el-icon>
            导出报告<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="html">HTML</el-dropdown-item>
              <el-dropdown-item command="pdf">PDF</el-dropdown-item>
              <el-dropdown-item command="excel">Excel</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="summary-card">
          <template #header>
            <span>报告摘要</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="报告名称">{{ report.name }}</el-descriptions-item>
            <el-descriptions-item label="测试类型">
              {{ getTestTypeText(report.test_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="所属项目">{{ report.project_name }}</el-descriptions-item>
            <el-descriptions-item label="报告类型">
              {{ getReportTypeText(report.report_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="总用例数">
              {{ report.total_cases || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="通过用例数">
              <span class="text-success">{{ report.total_cases - report.failed_cases - report.skipped_cases || 0 }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="失败用例数">
              <span class="text-danger">{{ report.failed_cases || 0 }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="跳过用例数">
              <span class="text-info">{{ report.skipped_cases || 0 }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="通过率">
              <el-progress
                :percentage="report.pass_rate || 0"
                :color="getPassRateColor(report.pass_rate)"
                :stroke-width="16"
              />
            </el-descriptions-item>
            <el-descriptions-item label="耗时">
              {{ report.duration?.toFixed(2) }} 秒
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(report.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="执行人">
              {{ report.executor_name || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="detail-card">
          <template #header>
            <span>测试详情</span>
          </template>
          <div v-if="report.test_details && report.test_details.length">
            <!-- V2.0 P1 虚拟列表重构：万级测试记录防腐层渲染 -->
            <DynamicScroller
              :items="report.test_details.map((item, idx) => ({ ...item, id: idx }))"
              :min-item-size="48"
              class="scroller"
              style="height: 600px; overflow-y: auto; border: 1px solid #ebeef5; border-radius: 4px;"
            >
              <template #default="{ item, index, active }">
                <DynamicScrollerItem
                  :item="item"
                  :active="active"
                  :size-dependencies="[expandedItemId === item.id]"
                  :data-index="index"
                >
                  <div class="virtual-collapse-item" :class="{ expanded: expandedItemId === item.id }">
                    <div class="vc-header" @click="toggleExpand(item.id)">
                      <el-tag :type="getStatusType(item.status)" size="small" style="margin-right:8px">
                        {{ getStatusText(item.status) }}
                      </el-tag>
                      <span class="vc-name" style="flex:1">{{ item.name }}</span>
                      <span style="color:#909399; font-size:13px; margin-right:12px">{{ item.duration?.toFixed(2) }}s</span>
                    </div>
                    
                    <div class="vc-body" v-show="expandedItemId === item.id">
                      <el-descriptions :column="1" border size="small">
                        <el-descriptions-item label="用例名称">
                          {{ item.name }}
                        </el-descriptions-item>
                        <el-descriptions-item label="状态">
                          <el-tag :type="getStatusType(item.status)" size="small">
                            {{ getStatusText(item.status) }}
                          </el-tag>
                        </el-descriptions-item>
                        <el-descriptions-item label="耗时">
                          {{ item.duration?.toFixed(2) }} 秒
                        </el-descriptions-item>
                        <el-descriptions-item label="错误信息" v-if="item.error_message">
                          <pre class="error-message">{{ item.error_message }}</pre>
                        </el-descriptions-item>
                        <el-descriptions-item label="执行结果" v-if="item.result">
                          <pre>{{ JSON.stringify(item.result, null, 2) }}</pre>
                        </el-descriptions-item>
                      </el-descriptions>
                    </div>
                  </div>
                </DynamicScrollerItem>
              </template>
            </DynamicScroller>
          </div>
          <el-empty v-else description="暂无测试详情" />
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span>测试结果统计</span>
          </template>
          <div ref="chartRef" style="height: 300px"></div>
        </el-card>

        <el-card class="info-card">
          <template #header>
            <span>其他信息</span>
          </template>
          <el-form label-width="100px">
            <el-form-item label="执行环境">
              {{ report.environment_name || '-' }}
            </el-form-item>
            <el-form-item label="执行版本">
              {{ report.version || '-' }}
            </el-form-item>
            <el-form-item label="浏览器" v-if="report.test_type === 'UI'">
              {{ report.browser || '-' }}
            </el-form-item>
            <el-form-item label="并发数" v-if="report.test_type === 'PERFORMANCE'">
              {{ report.concurrency || '-' }}
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- AI 智能分析卡片 -->
    <el-card class="ai-analysis-card">
      <template #header>
        <div class="ai-card-header">
          <span class="ai-card-title">
            <el-icon class="ai-icon"><MagicStick /></el-icon>
            AI 智能分析
          </span>
          <el-tag v-if="aiAnalyzedAt" type="success" size="small">
            已分析 · {{ formatDate(aiAnalyzedAt) }}
          </el-tag>
        </div>
      </template>

      <!-- 模型选择 + 操作区 -->
      <div class="ai-action-bar">
        <el-select
          v-model="selectedModelId"
          placeholder="请选择 AI 模型"
          style="width: 220px"
          :loading="modelsLoading"
          clearable
        >
          <el-option
            v-for="m in aiModels"
            :key="m.id"
            :label="`${m.name}（${m.model_name}）`"
            :value="m.id"
          />
        </el-select>

        <el-button
          type="primary"
          :loading="analyzing"
          :icon="MagicStick"
          @click="handleAnalyze"
          style="margin-left: 12px"
        >
          {{ aiAnalyzedAt ? '重新分析' : '开始 AI 分析' }}
        </el-button>

        <span v-if="aiModels.length === 0 && !modelsLoading" class="no-model-tip">
          <el-icon><Warning /></el-icon>
          暂无可用模型，请先在
          <el-link type="primary" @click="$router.push('/configuration/ai-model')">
            配置中心 → AI模型配置
          </el-link>
          中添加模型
        </span>
      </div>

      <!-- 已有分析结果 -->
      <div v-if="aiAnalysisResult || aiSuggestions" class="ai-result-area">
        <el-divider />
        <div v-if="aiAnalysisResult" class="ai-result-section">
          <div class="ai-section-label">
            <el-icon><Document /></el-icon>
            分析总结
          </div>
          <div class="ai-result-content">{{ aiAnalysisResult }}</div>
        </div>

        <div v-if="aiSuggestions" class="ai-result-section" style="margin-top: 16px">
          <div class="ai-section-label suggestions">
            <el-icon><Promotion /></el-icon>
            修复建议
          </div>
          <div class="ai-result-content suggestions-content">{{ aiSuggestions }}</div>
        </div>
      </div>

      <!-- 未分析空状态 -->
      <el-empty
        v-else-if="!analyzing"
        description="暂未进行 AI 分析，请选择模型后点击「开始 AI 分析」"
        :image-size="80"
        style="padding: 20px 0"
      />

      <!-- 分析中占位 -->
      <div v-if="analyzing" class="analyzing-placeholder">
        <el-skeleton :rows="4" animated />
      </div>
    </el-card>

    <!-- 从报告提交缺陷 -->
    <el-dialog
      title="从报告提交缺陷"
      v-model="defectDialogVisible"
      width="640px">
      <el-form :model="defectForm" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="defectForm.title" placeholder="缺陷标题" />
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="defectForm.severity" style="width:100%">
            <el-option v-for="s in defectSeverityOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="defectForm.priority" style="width:100%">
            <el-option v-for="p in defectPriorityOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="环境">
          <el-input v-model="defectForm.environment" :placeholder="report.environment_name || '如 staging / prod'" />
        </el-form-item>
        <el-form-item label="复现步骤">
          <el-input v-model="defectForm.steps" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="defectForm.description" type="textarea" :rows="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="defectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingDefect" @click="submitDefect">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api, { authFetch } from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Download, MagicStick, Document, Promotion, Warning, Monitor } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getReportDetail,
  exportReport,
  getAIModelList,
  analyzeReport
} from '@/api/unified/report'

const router = useRouter()
const route = useRoute()

const reportId = route.params.id
const loading = ref(false)
const report = ref({})
const chartRef = ref(null)
let chartInstance = null

// V2 虚拟滚动折叠状态控制
const expandedItemId = ref(null)

const toggleExpand = (id) => {
  expandedItemId.value = expandedItemId.value === id ? null : id
}

// AI 分析相关
const aiModels = ref([])
const modelsLoading = ref(false)
const selectedModelId = ref(null)
const analyzing = ref(false)
const aiAnalysisResult = ref('')
const aiSuggestions = ref('')
const aiAnalyzedAt = ref(null)

// 提交缺陷相关
const defectDialogVisible = ref(false)
const submittingDefect = ref(false)
const defectForm = ref({
  title: '', severity: 'major', priority: 'P2',
  environment: '', steps: '', description: ''
})
const defectSeverityOptions = [
  { value: 'critical', label: '致命' }, { value: 'major', label: '严重' },
  { value: 'minor', label: '一般' }, { value: 'trivial', label: '轻微' },
]
const defectPriorityOptions = [
  { value: 'P0', label: 'P0-最高' }, { value: 'P1', label: 'P1-高' },
  { value: 'P2', label: 'P2-中' }, { value: 'P3', label: 'P3-低' },
]

const openFileDefect = () => {
  const details = report.value.test_details || []
  const failed = details.filter(d => d.status === 'FAILED' || d.status === 'failed')
  let desc = ''
  if (failed.length) {
    const lines = failed.slice(0, 20).map((d, i) => {
      const err = d.error_message ? `\n    错误：${d.error_message}` : ''
      return `${i + 1}. ${d.name || '-'}${err}`
    }).join('\n')
    desc = `报告「${report.value.name}」失败用例（共 ${failed.length} 条）：\n${lines}`
  } else {
    desc = `报告「${report.value.name}」测试结果汇总：通过率 ${report.value.pass_rate || 0}%，失败 ${report.value.failed_cases || 0} 条。`
  }
  defectForm.value = {
    title: `报告「${report.value.name}」缺陷跟踪`,
    severity: 'major',
    priority: 'P2',
    environment: report.value.environment_name || '',
    steps: '',
    description: desc,
  }
  defectDialogVisible.value = true
}

const submitDefect = async () => {
  if (!defectForm.value.title) {
    ElMessage.warning('请填写标题')
    return
  }
  submittingDefect.value = true
  try {
    await api.post('/defects/defects/', defectForm.value)
    ElMessage.success('缺陷已提交')
    defectDialogVisible.value = false
  } catch (error) {
    const msg = error?.response?.data?.message || error?.response?.data?.detail || error?.message || '提交失败'
    ElMessage.error('提交失败：' + msg)
  } finally {
    submittingDefect.value = false
  }
}

// 获取 AI 模型列表
const fetchAIModels = async () => {
  modelsLoading.value = true
  try {
    const res = await getAIModelList()
    const list = res?.data?.results ?? res?.data ?? res?.results ?? (Array.isArray(res) ? res : [])
    aiModels.value = list
    if (list.length > 0) {
      selectedModelId.value = list[0].id
    }
  } catch (e) {
    console.error('获取 AI 模型列表失败', e)
  } finally {
    modelsLoading.value = false
  }
}

// 触发 AI 分析
const handleAnalyze = async () => {
  if (!selectedModelId.value && aiModels.value.length > 0) {
    ElMessage.warning('请先选择 AI 模型')
    return
  }

  // 已有结果时确认重新分析
  if (aiAnalyzedAt.value) {
    try {
      await ElMessageBox.confirm('已存在分析结果，是否重新分析？重新分析将覆盖原有结果。', '确认重新分析', {
        confirmButtonText: '重新分析',
        cancelButtonText: '取消',
        type: 'warning'
      })
    } catch {
      return
    }
  }

  analyzing.value = true
  try {
    const res = await analyzeReport(reportId, {
      model_config_id: selectedModelId.value || undefined
    })
    const data = res?.data ?? res
    aiAnalysisResult.value = data.ai_analysis_result || ''
    aiSuggestions.value = data.ai_suggestions || ''
    aiAnalyzedAt.value = data.ai_analyzed_at || new Date().toISOString()
    const modelUsed = data.model_used || '未知模型'
    ElMessage.success(`AI 分析完成（${modelUsed}）`)
  } catch (error) {
    const msg = error?.response?.data?.message || error?.message || 'AI 分析失败，请稍后重试'
    ElMessage.error(msg)
    console.error(error)
  } finally {
    analyzing.value = false
  }
}

// 方法
const fetchReportDetail = async () => {
  loading.value = true
  try {
    const res = await getReportDetail(reportId)
    const data = res.data || res
    report.value = data

    // 回填 AI 分析字段
    aiAnalysisResult.value = data.ai_analysis_result || ''
    aiSuggestions.value = data.ai_suggestions || ''
    aiAnalyzedAt.value = data.ai_analyzed_at || null

    // 渲染图表
    nextTick(() => {
      renderChart()
    })
  } catch (error) {
    ElMessage.error('获取报告详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/unified/reports')
}

const openAllureReport = () => {
  if (report.value.allure_url) {
    // 处理相对路径
    let url = report.value.allure_url
    if (!url.startsWith('http')) {
      // 假设 /api 是后端基础路径，/media 是静态文件路径
      // 在本地开发环境中可能需要拼接正确的后端地址
      url = `${window.location.origin}${url}`
    }
    window.open(url, '_blank')
  }
}

const handleExport = async (format) => {
  try {
    const userStore = useUserStore()
    const token = userStore.accessToken
    
    // 使用原生的 fetch api 完全绕过 axios 拦截器和任何可能将其序列化的 mock 框架
    const response = await authFetch(`/api/reports/reports/${reportId}/fetch_report_file/?file_format=${format}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      throw new Error(`Export failed with status: ${response.status}`)
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // 设置正确的文件扩展名
    const extMap = {
      excel: 'xlsx',
      html: 'html',
      pdf: 'pdf'
    }
    const ext = extMap[format] || format
    link.download = `${report.value.name}.${ext}`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    window.URL.revokeObjectURL(url)

    ElMessage.success('报告导出成功')
  } catch (error) {
    ElMessage.error('报告导出失败')
    console.error(error)
  }
}

const renderChart = () => {
  if (!chartRef.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  const passed = report.value.total_cases - report.value.failed_cases - report.value.skipped_cases
  const failed = report.value.failed_cases
  const skipped = report.value.skipped_cases

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '测试结果',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: passed, name: '通过', itemStyle: { color: '#67c23a' } },
          { value: failed, name: '失败', itemStyle: { color: '#f56c6c' } },
          { value: skipped, name: '跳过', itemStyle: { color: '#909399' } }
        ]
      }
    ]
  }

  chartInstance.setOption(option)
}

// 辅助方法
const getTestTypeTag = (type) => {
  const tags = {
    API: 'primary',
    UI: 'success',
    PERFORMANCE: 'warning',
    GENERAL: 'info'
  }
  return tags[type] || 'info'
}

const getTestTypeText = (type) => {
  const texts = {
    API: 'API测试',
    UI: 'UI自动化',
    PERFORMANCE: '性能测试',
    GENERAL: '通用测试'
  }
  return texts[type] || type
}

const getReportTypeText = (type) => {
  const texts = {
    TEST_SUITE: '测试套件',
    SCHEDULED_TASK: '定时任务',
    API_REQUEST: 'API请求'
  }
  return texts[type] || type
}

const getStatusType = (status) => {
  const types = {
    PASSED: 'success',
    FAILED: 'danger',
    SKIPPED: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    PASSED: '通过',
    FAILED: '失败',
    SKIPPED: '跳过'
  }
  return texts[status] || status
}

const getPassRateColor = (rate) => {
  if (rate >= 80) return '#67c23a'
  if (rate >= 60) return '#e6a23c'
  return '#f56c6c'
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  fetchReportDetail()
  fetchAIModels()
})
</script>

<style scoped>
.report-detail {
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-content h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.summary-card,
.detail-card,
.chart-card,
.info-card {
  margin-bottom: 20px;
}

.text-success {
  color: #67c23a;
  font-weight: 600;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}

.text-info {
  color: #909399;
}

.test-case-title {
  display: flex;
  align-items: center;
}

.test-case-detail {
  padding: 12px 0;
}

.error-message {
  margin: 0;
  padding: 12px;
  background: #fef0f0;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 12px;
  overflow-x: auto;
}

pre {
  margin: 0;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
}

/* AI 分析卡片 */
.ai-analysis-card {
  margin-top: 4px;
}

.ai-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ai-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #409eff;
}

.ai-icon {
  font-size: 18px;
  color: #409eff;
}

.ai-action-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.no-model-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #e6a23c;
  font-size: 13px;
  margin-left: 8px;
}

.ai-result-area {
  margin-top: 4px;
}

.ai-result-section {
  background: #f8f9ff;
  border-radius: 8px;
  padding: 16px;
  border-left: 4px solid #409eff;
}

.ai-result-section.suggestions-content-wrapper {
  border-left-color: #67c23a;
}

.ai-section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 10px;
  font-size: 14px;
}

.ai-section-label.suggestions {
  color: #67c23a;
}

.ai-result-content {
  color: #303133;
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.suggestions-content {
  border-left-color: #67c23a;
}

.analyzing-placeholder {
  margin-top: 16px;
  padding: 8px 0;
}

/* V2 Virtual Scroller Styles */
.virtual-collapse-item {
  border-bottom: 1px solid #ebeef5;
  transition: all 0.3s;
}

.virtual-collapse-item:last-child {
  border-bottom: none;
}

.vc-header {
  display: flex;
  align-items: center;
  padding: 0 15px;
  height: 48px;
  cursor: pointer;
  background-color: #fff;
}

.vc-header:hover {
  background-color: #f5f7fa;
}

.vc-name {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vc-body {
  padding: 15px;
  background-color: #fcfcfd;
  border-top: 1px dashed #ebeef5;
}

</style>
