<template>
  <BasePage title="数据看板">
    <!-- 数据概览 -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-red">
                <el-icon><Lock /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ scanCount }}</div>
                <div class="stat-label">安全扫描</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-orange">
                <el-icon><Warning /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ vulnerabilityCount }}</div>
                <div class="stat-label">发现漏洞</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-green">
                <el-icon><SuccessFilled /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ secureCount }}</div>
                <div class="stat-label">安全项目</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 快速扫描和最近扫描记录 -->
    <el-row :gutter="20" class="content-section">
      <!-- 快速扫描区域 -->
      <el-col :span="12">
      <el-card class="quick-scan" title="快速扫描" shadow="hover">
        <div class="scan-content">
          <el-form-item label="扫描目标">
            <el-input
              v-model="scanTarget"
              placeholder="请输入要扫描的URL或IP地址"
              style="width: 100%"
            />
          </el-form-item>
          
          <el-form-item label="扫描类型">
            <el-select
              v-model="scanType"
              placeholder="选择扫描类型"
              style="width: 100%"
            >
              <el-option label="基础扫描" value="basic" />
              <el-option label="深度扫描" value="deep" />
              <el-option label="全面扫描" value="full" />
            </el-select>
          </el-form-item>
          
          <div class="scan-actions">
            <el-button
              type="primary"
              size="large"
              @click="startQuickScan"
              :disabled="!scanTarget.trim() || scanning"
            >
              <el-icon v-if="scanning"><Loading /></el-icon>
              <el-icon v-else><Search /></el-icon>
              {{ scanning ? '扫描中...' : '开始扫描' }}
            </el-button>
          </div>
        </div>
      </el-card>
      </el-col>
      
      <!-- 最近扫描记录 -->
      <el-col :span="12">
        <el-card class="recent-scans" title="最近扫描" shadow="hover">
          <div v-if="loadingScans" class="loading-container">
            <el-empty description="加载中..." />
          </div>
          <div v-else-if="recentScans.length === 0" class="scans-list">
            <el-empty description="暂无扫描记录" />
          </div>
          <div v-else class="scans-list">
            <div v-for="scan in recentScans" :key="scan.id" class="scan-item">
              <div class="scan-header">
                <div class="scan-title">{{ scan.target }}</div>
                <el-tag
                  :type="scan.status === 'COMPLETED' ? 'success' : (scan.status === 'FAILED' ? 'danger' : (scan.status === 'RUNNING' ? 'primary' : 'warning'))"
                  size="small"
                >
                  {{ scan.status === 'COMPLETED' ? '已完成' : (scan.status === 'FAILED' ? '失败' : (scan.status === 'RUNNING' ? '运行中' : (scan.status === 'PENDING' ? '等待中' : '已停止'))) }}
                </el-tag>
              </div>
              <div class="scan-meta">
                <span class="scan-time">{{ formatTime(scan.start_time) }}</span>
                <span class="scan-type">{{ scan.type === 'basic' ? '基础扫描' : (scan.type === 'deep' ? '深度扫描' : '全面扫描') }}</span>
                <span class="scan-vulnerabilities" :class="scan.vulnerabilities > 0 ? 'vulnerable' : 'secure'">
                  {{ scan.vulnerabilities > 0 ? `${scan.vulnerabilities}个漏洞` : '无漏洞' }}
                </span>
              </div>
              <div class="scan-actions">
                <el-button
                  type="primary"
                  size="small"
                  @click="viewScan(scan)"
                >
                  查看报告
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 漏洞统计 -->
    <div class="vulnerability-section">
      <el-card shadow="hover" title="漏洞统计" class="vulnerability-card">
        <div class="vulnerability-content">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="chart-container">
                <h3 class="chart-title">漏洞类型分布</h3>
                <el-progress :percentage="45" :stroke-width="24" status="warning" format="高危" />
                <div class="progress-stats">
                  <div class="progress-item">
                    <span class="progress-label">高危漏洞</span>
                    <span class="progress-value">45%</span>
                  </div>
                  <div class="progress-item">
                    <span class="progress-label">中危漏洞</span>
                    <span class="progress-value">30%</span>
                  </div>
                  <div class="progress-item">
                    <span class="progress-label">低危漏洞</span>
                    <span class="progress-value">25%</span>
                  </div>
                </div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="chart-container">
                <h3 class="chart-title">扫描结果趋势</h3>
                <div class="trend-chart">
                  <div class="trend-bar">
                    <div class="bar-container">
                      <div class="bar" style="height: 60%; background-color: #f56c6c;"></div>
                    </div>
                    <div class="bar-label">11/01</div>
                  </div>
                  <div class="trend-bar">
                    <div class="bar-container">
                      <div class="bar" style="height: 75%; background-color: #e6a23c;"></div>
                    </div>
                    <div class="bar-label">11/02</div>
                  </div>
                  <div class="trend-bar">
                    <div class="bar-container">
                      <div class="bar" style="height: 50%; background-color: #f56c6c;"></div>
                    </div>
                    <div class="bar-label">11/03</div>
                  </div>
                  <div class="trend-bar">
                    <div class="bar-container">
                      <div class="bar" style="height: 30%; background-color: #67c23a;"></div>
                    </div>
                    <div class="bar-label">11/04</div>
                  </div>
                  <div class="trend-bar">
                    <div class="bar-container">
                      <div class="bar" style="height: 45%; background-color: #e6a23c;"></div>
                    </div>
                    <div class="bar-label">11/05</div>
                  </div>
                  <div class="trend-bar">
                    <div class="bar-container">
                      <div class="bar" style="height: 20%; background-color: #67c23a;"></div>
                    </div>
                    <div class="bar-label">11/06</div>
                  </div>
                  <div class="trend-bar">
                    <div class="bar-container">
                      <div class="bar" style="height: 35%; background-color: #67c23a;"></div>
                    </div>
                    <div class="bar-label">11/07</div>
                  </div>
                </div>
              </div>
            </el-col>
          </el-row>
          
          <div class="vulnerability-table">
            <h3 class="chart-title">最近发现的漏洞</h3>
            <el-table
              :data="recentVulnerabilities"
              style="width: 100%"
              size="small"
              border
              stripe
            >
              <el-table-column prop="name" label="漏洞名称" min-width="200" />
              <el-table-column prop="severity" label="严重程度" width="120">
                <template #default="scope">
                  <el-tag
                    :type="scope.row.severity === 'HIGH' ? 'danger' : (scope.row.severity === 'MEDIUM' ? 'warning' : 'info')"
                  >
                    {{ scope.row.severity === 'HIGH' ? '高危' : (scope.row.severity === 'MEDIUM' ? '中危' : '低危') }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="target" label="受影响目标" min-width="180" />
              <el-table-column prop="scan_name" label="发现来源" width="150" />
              <el-table-column prop="discovered_at" label="发现时间" width="180" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="scope">
                  <el-button
                    type="primary"
                    size="small"
                    @click="viewVulnerability(scope.row)"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-card>
    </div>
  </BasePage>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, Warning, SuccessFilled, Loading, Search } from '@element-plus/icons-vue'
import router from '@/router'

// 统计数据
const scanCount = ref(0)
const vulnerabilityCount = ref(0)
const secureCount = ref(0)

// 快速扫描
const scanTarget = ref('')
const scanType = ref('basic')
const scanning = ref(false)

// 扫描记录
const loadingScans = ref(false)
const recentScans = ref([])

// 加载扫描记录
const loadRecentScans = async () => {
  loadingScans.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    // 模拟数据
    recentScans.value = [
      {
        id: 1,
        target: 'https://example.com',
        type: 'basic',
        status: 'COMPLETED',
        vulnerabilities: 2,
        start_time: new Date().toISOString()
      },
      {
        id: 2,
        target: 'https://test.com',
        type: 'deep',
        status: 'COMPLETED',
        vulnerabilities: 0,
        start_time: new Date(Date.now() - 3600000).toISOString()
      }
    ]
    scanCount.value = recentScans.value.length
    vulnerabilityCount.value = recentScans.value.reduce((sum, scan) => sum + scan.vulnerabilities, 0)
    secureCount.value = recentScans.value.filter(scan => scan.vulnerabilities === 0).length
  } catch (error) {
    console.error('加载扫描记录失败:', error)
    ElMessage.error('加载扫描记录失败')
  } finally {
    loadingScans.value = false
  }
}

// 开始快速扫描
const startQuickScan = async () => {
  if (!scanTarget.value.trim()) {
    ElMessage.warning('请输入扫描目标')
    return
  }
  
  scanning.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟成功响应
    const newScan = {
      id: Date.now(),
      target: scanTarget.value,
      type: scanType.value,
      status: 'COMPLETED',
      vulnerabilities: Math.floor(Math.random() * 3),
      start_time: new Date().toISOString()
    }
    
    recentScans.value.unshift(newScan)
    scanCount.value++
    vulnerabilityCount.value += newScan.vulnerabilities
    if (newScan.vulnerabilities === 0) {
      secureCount.value++
    }
    
    scanTarget.value = ''
    scanType.value = 'basic'
    
    ElMessage.success('扫描完成')
  } catch (error) {
    console.error('扫描失败:', error)
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

// 查看扫描报告
const viewScan = (scan) => {
  ElMessage.success(`查看扫描报告: ${scan.target}`)
  // 这里可以跳转到扫描报告页面
  // router.push(`/strix-security/reports/${scan.id}`)
}

// 最近发现的漏洞
const recentVulnerabilities = ref([
  {
    id: 1,
    name: 'SQL注入漏洞',
    severity: 'HIGH',
    target: 'https://example.com/api/users',
    scan_name: '全面扫描',
    discovered_at: '2023-11-07T14:30:00Z'
  },
  {
    id: 2,
    name: '跨站脚本攻击',
    severity: 'MEDIUM',
    target: 'https://example.com/login',
    scan_name: '深度扫描',
    discovered_at: '2023-11-07T12:15:00Z'
  },
  {
    id: 3,
    name: '不安全的直接对象引用',
    severity: 'HIGH',
    target: 'https://example.com/api/orders/123',
    scan_name: '基础扫描',
    discovered_at: '2023-11-06T16:45:00Z'
  },
  {
    id: 4,
    name: '缺少安全头',
    severity: 'LOW',
    target: 'https://example.com',
    scan_name: '全面扫描',
    discovered_at: '2023-11-06T10:30:00Z'
  },
  {
    id: 5,
    name: '密码策略薄弱',
    severity: 'MEDIUM',
    target: 'https://example.com/register',
    scan_name: '深度扫描',
    discovered_at: '2023-11-05T15:20:00Z'
  }
])

// 查看漏洞详情
const viewVulnerability = (vuln) => {
  ElMessage.success(`查看漏洞: ${vuln.name}`)
  // 这里可以跳转到漏洞详情页面
  // router.push(`/strix-security/vulnerabilities/${vuln.id}`)
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  
  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }
  // 小于1小时
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  }
  // 小于1天
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  }
  // 小于7天
  if (diff < 604800000) {
    return `${Math.floor(diff / 86400000)}天前`
  }
  // 超过7天显示具体日期
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 组件挂载时加载数据
onMounted(() => {
  loadRecentScans()
})
</script>

<style scoped>
.dashboard-container {
  width: 100%;
  padding: 0 ;
}

.stats-section {
  margin-bottom: 40px;
}

.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  color: white;
  font-size: 24px;
}

.stat-icon.bg-red {
  background-color: #f56c6c;
}

.stat-icon.bg-orange {
  background-color: #e6a23c;
}

.stat-icon.bg-green {
  background-color: #67c23a;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #1a1a1a;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.content-section {
  margin-bottom: 40px;
}

.quick-scan {
  height: 100%;
}

.scan-content {
  margin-top: 20px;
}

.scan-actions {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.recent-scans {
  height: 100%;
}

.loading-container {
  padding: 40px 0;
}

.scans-list {
  max-height: 400px;
  overflow-y: auto;
}

.scan-item {
  padding: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.scan-item:last-child {
  border-bottom: none;
}

.scan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.scan-title {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.scan-meta {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #999;
  margin-bottom: 10px;
}

.scan-vulnerabilities {
  font-weight: 500;
}

.scan-vulnerabilities.vulnerable {
  color: #f56c6c;
}

.scan-vulnerabilities.secure {
  color: #67c23a;
}

.vulnerability-section {
  margin-bottom: 40px;
}

.vulnerability-card {
  height: 100%;
}

.vulnerability-content {
  padding: 20px 0;
}

.chart-container {
  margin-bottom: 30px;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #333;
}

.progress-stats {
  margin-top: 20px;
  display: flex;
  justify-content: space-around;
}

.progress-item {
  text-align: center;
}

.progress-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 5px;
}

.progress-value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}

.trend-chart {
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  height: 200px;
  padding: 20px 0;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.trend-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  margin: 0 5px;
}

.bar-container {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  height: 100%;
  width: 100%;
}

.bar {
  width: 40px;
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
}

.bar:hover {
  opacity: 0.8;
}

.bar-label {
  margin-top: 10px;
  font-size: 12px;
  color: #666;
}

.vulnerability-table {
  margin-top: 30px;
}
</style>