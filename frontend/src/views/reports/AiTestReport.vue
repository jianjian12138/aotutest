<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">AI测试报告</h1>
      <div class="header-actions">
        <el-button type="primary" @click="exportReport">
          <el-icon><Download /></el-icon>
          导出报告
        </el-button>
      </div>
    </div>

    <div class="card-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="left-filters">
        <el-select v-model="filters.project" placeholder="选择项目" clearable @change="handleFilterChange" style="width: 200px">
          <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
        </el-select>
        <el-select v-model="filters.days" placeholder="时间范围" @change="handleFilterChange" style="width: 150px">
          <el-option label="最近7天" :value="7"></el-option>
          <el-option label="最近14天" :value="14"></el-option>
          <el-option label="最近30天" :value="30"></el-option>
        </el-select>
      </div>
    </div>

    <!-- 概览卡片 -->
    <div class="dashboard-cards">
      <div class="card total-plans">
        <div class="card-icon">
          <el-icon><Collection /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.active_plans || 0 }}</div>
          <div class="card-label">活跃计划</div>
        </div>
        <div class="card-extra">
          <el-progress type="circle" :percentage="dashboardData.plan_progress || 0" :width="40" :stroke-width="4" :show-text="false" />
          <span class="progress-text">{{ dashboardData.plan_progress || 0 }}% 进度</span>
        </div>
      </div>
      <div class="card total-cases">
        <div class="card-icon">
          <el-icon><Document /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.total_cases || 0 }}</div>
          <div class="card-label">用例总数</div>
        </div>
      </div>
      <div class="card pass-rate">
        <div class="card-icon">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.pass_rate || 0 }}%</div>
          <div class="card-label">通过率</div>
        </div>
      </div>
      <div class="card defects">
        <div class="card-icon">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-value">{{ dashboardData.total_defects || 0 }}</div>
          <div class="card-label">发现缺陷</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-container">
      <!-- 第一行：执行状态与趋势 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>执行状态分布</h3>
          </div>
          <div class="chart-body" ref="statusChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>每日执行趋势</h3>
          </div>
          <div class="chart-body" ref="trendChartRef"></div>
        </div>
      </div>

      <!-- 第二行：缺陷分析 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>失败用例优先级分布 (缺陷分布)</h3>
          </div>
          <div class="chart-body" ref="defectChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>失败用例 TOP 10</h3>
          </div>
          <div class="chart-body table-body">
            <el-table :data="failedCasesTop" style="width: 100%" size="small">
              <el-table-column prop="testcase__title" label="用例标题" show-overflow-tooltip />
              <el-table-column prop="fail_count" label="失败次数" width="100" align="center">
                <template #default="scope">
                  <el-tag type="danger">{{ scope.row.fail_count }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <!-- 第三行：AI效能 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-header">
            <h3>AI生成效能分析</h3>
          </div>
          <div class="ai-metrics-container">
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.adoption_rate || 0 }}%</div>
              <div class="metric-label">生成采纳率</div>
              <el-progress :percentage="aiData.adoption_rate || 0" :show-text="false" status="success" />
            </div>
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.requirement_coverage || 0 }}%</div>
              <div class="metric-label">需求覆盖率</div>
              <el-progress :percentage="aiData.requirement_coverage || 0" :show-text="false" />
            </div>
            <div class="ai-metric-item">
              <div class="metric-value">{{ aiData.saved_hours || 0 }}h</div>
              <div class="metric-label">节省工时估算</div>
            </div>
          </div>
          <div class="chart-body-small" ref="aiEfficiencyChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <h3>团队工作量统计</h3>
          </div>
          <div class="chart-body" ref="workloadChartRef"></div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Collection, Document, CircleCheck, Warning, Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import api from '@/utils/api'

// 状态
const projects = ref([])
const filters = reactive({
  project: null,
  days: 7
})
const dashboardData = ref({})
const failedCasesTop = ref([])
const aiData = ref({})

// 图表实例
let statusChart = null
let trendChart = null
let defectChart = null
let aiEfficiencyChart = null
let workloadChart = null

// DOM引用
const statusChartRef = ref(null)
const trendChartRef = ref(null)
const defectChartRef = ref(null)
const aiEfficiencyChartRef = ref(null)
const workloadChartRef = ref(null)

// 获取基础数据
const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || []
  } catch (error) {
    console.error('获取项目失败', error)
  }
}

// 获取概览数据
const fetchDashboardData = async () => {
  try {
    const params = { project: filters.project }
    const response = await api.get('/reports/reports/dashboard/', { params })
    dashboardData.value = response.data
  } catch (error) {
    console.error('获取概览数据失败', error)
  }
}

// 初始化图表
const initCharts = () => {
  if (statusChartRef.value) statusChart = echarts.init(statusChartRef.value)
  if (trendChartRef.value) trendChart = echarts.init(trendChartRef.value)
  if (defectChartRef.value) defectChart = echarts.init(defectChartRef.value)
  if (aiEfficiencyChartRef.value) aiEfficiencyChart = echarts.init(aiEfficiencyChartRef.value)
  if (workloadChartRef.value) workloadChart = echarts.init(workloadChartRef.value)
  
  window.addEventListener('resize', handleResize)
}

const handleResize = () => {
  statusChart?.resize()
  trendChart?.resize()
  defectChart?.resize()
  aiEfficiencyChart?.resize()
  workloadChart?.resize()
}

// 加载图表数据
const loadChartsData = async () => {
  const params = { 
    project: filters.project,
    days: filters.days
  }

  // 1. 状态分布
  try {
    const res = await api.get('/reports/reports/status_distribution/', { params })
    const data = [
      { value: res.data.passed, name: '通过', itemStyle: { color: '#67C23A' } },
      { value: res.data.failed, name: '失败', itemStyle: { color: '#F56C6C' } },
      { value: res.data.blocked, name: '阻塞', itemStyle: { color: '#E6A23C' } },
      { value: res.data.retest, name: '重测', itemStyle: { color: '#409EFF' } },
      { value: res.data.untested, name: '未测', itemStyle: { color: '#909399' } }
    ]
    
    statusChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center' },
      series: [{
        name: '执行状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: data
      }]
    })
  } catch (e) { console.error(e) }

  // 2. 执行趋势
  try {
    const res = await api.get('/reports/reports/execution_trend/', { params })
    const dates = res.data.map(item => item.date)
    const counts = res.data.map(item => item.count)
    
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: dates },
      yAxis: { type: 'value' },
      series: [{
        name: '执行数量',
        type: 'line',
        stack: 'Total',
        smooth: true,
        areaStyle: { opacity: 0.3, color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#fff' }]) },
        itemStyle: { color: '#409EFF' },
        data: counts
      }]
    })
  } catch (e) { console.error(e) }

  // 3. 缺陷分布
  try {
    const res = await api.get('/reports/reports/defect_distribution/', { params })
    defectChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center' },
      series: [{
        name: '优先级分布',
        type: 'pie',
        radius: '60%',
        center: ['50%', '45%'],
        data: res.data,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    })
  } catch (e) { console.error(e) }

  // 4. 失败用例TOP榜
  try {
    const res = await api.get('/reports/reports/failed_cases_top/', { params })
    failedCasesTop.value = res.data
  } catch (e) { console.error(e) }

  // 5. AI效能
  try {
    const res = await api.get('/reports/reports/ai_efficiency/', { params })
    aiData.value = res.data
    const aiCounts = res.data.ai_vs_manual
    
    aiEfficiencyChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: ['用例来源'] },
      series: [
        { name: 'AI生成', type: 'bar', stack: 'total', label: { show: true }, itemStyle: { color: '#8e44ad' }, data: [aiCounts.ai] },
        { name: '人工创建', type: 'bar', stack: 'total', label: { show: true }, itemStyle: { color: '#3498db' }, data: [aiCounts.manual] }
      ]
    })
  } catch (e) { console.error(e) }

  // 6. 团队工作量
  try {
    const res = await api.get('/reports/reports/team_workload/', { params })
    const users = res.data.map(item => item.username)
    const execCounts = res.data.map(item => item.execution_count)
    const defectCounts = res.data.map(item => item.defect_count)
    
    workloadChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['执行用例', '发现缺陷'], bottom: '0%' },
      grid: { left: '3%', right: '4%', bottom: '10%', top: '5%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: users },
      series: [
        {
          name: '执行用例',
          type: 'bar',
          stack: 'total',
          label: { show: true },
          itemStyle: { color: '#409EFF' },
          data: execCounts
        },
        {
          name: '发现缺陷',
          type: 'bar',
          stack: 'total',
          label: { show: true },
          itemStyle: { color: '#F56C6C' },
          data: defectCounts
        }
      ]
    })
  } catch (e) { console.error(e) }
}

const handleFilterChange = () => {
  fetchDashboardData()
  loadChartsData()
}

const exportReport = async () => {
  try {
    const params = {
      project: filters.project,
      days: filters.days
    }
    
    // 调用后端导出API
    const response = await api.get('/reports/reports/export_report/', {
      params,
      responseType: 'blob' // 指定响应类型为二进制数据
    })
    
    // 处理文件下载
    const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    
    // 从响应头获取文件名，或者使用默认名称
    const contentDisposition = response.headers['content-disposition']
    let filename = '测试报告.xlsx'
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="(.+)"/)
      if (filenameMatch && filenameMatch[1]) {
        filename = decodeURIComponent(filenameMatch[1])
      }
    }
    
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('报告导出成功！')
  } catch (error) {
    console.error('导出报告失败:', error)
    ElMessage.error('报告导出失败，请稍后重试')
  }
}

onMounted(async () => {
  await fetchProjects()
  await nextTick()
  initCharts()
  handleFilterChange()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  statusChart?.dispose()
  trendChart?.dispose()
  defectChart?.dispose()
  aiEfficiencyChart?.dispose()
  workloadChart?.dispose()
})
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
.test-report {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.left-filters {
  display: flex;
  gap: 16px;
}

.dashboard-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
  position: relative;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.1);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  font-size: 24px;
}

.total-plans .card-icon { background: #e8f3ff; color: #409EFF; }
.total-cases .card-icon { background: #f0f9eb; color: #67C23A; }
.pass-rate .card-icon { background: #fdf6ec; color: #E6A23C; }
.defects .card-icon { background: #fef0f0; color: #F56C6C; }

.card-content {
  flex: 1;
}

.card-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.card-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.card-extra {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.chart-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}

.chart-header {
  margin-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 10px;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
  font-weight: 600;
}

.chart-body {
  height: 300px;
  width: 100%;
}

.chart-body-small {
  height: 150px;
  width: 100%;
}

.table-body {
  overflow-y: auto;
}

.ai-metrics-container {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
}

.ai-metric-item {
  text-align: center;
  width: 30%;
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}
</style>
