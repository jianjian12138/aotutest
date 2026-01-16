<template>
  <div class="wharttest-dashboard">
    <h1>WHartTest 数据看板</h1>
    <div class="dashboard-cards">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8">
          <el-card shadow="hover" class="dashboard-card">
            <template #header>
              <div class="card-header">
                <span>项目总数</span>
              </div>
            </template>
            <div class="card-content">
              <div class="card-value">{{ projectCount }}</div>
              <div class="card-desc">已创建的项目数量</div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <el-card shadow="hover" class="dashboard-card">
            <template #header>
              <div class="card-header">
                <span>执行任务</span>
              </div>
            </template>
            <div class="card-content">
              <div class="card-value">{{ executionCount }}</div>
              <div class="card-desc">当前执行中的任务</div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <el-card shadow="hover" class="dashboard-card">
            <template #header>
              <div class="card-header">
                <span>成功执行率</span>
              </div>
            </template>
            <div class="card-content">
              <div class="card-value">{{ successRate }}%</div>
              <div class="card-desc">最近30天的执行成功率</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    <div class="dashboard-charts">
      <el-row :gutter="20">
        <el-col :xs="24" :md="12">
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <span>项目执行趋势</span>
              </div>
            </template>
            <div class="chart-placeholder">图表区域</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <span>项目状态分布</span>
              </div>
            </template>
            <div class="chart-placeholder">图表区域</div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

// 数据
const projectCount = ref(0)
const executionCount = ref(0)
const successRate = ref(0)

// 获取仪表盘数据
const fetchDashboardData = async () => {
  try {
    const response = await api.get('/dashboard/')
    const data = response.data
    projectCount.value = data.project_count || 0
    executionCount.value = data.execution_count || 0
    successRate.value = data.success_rate || 0
  } catch (error) {
    console.error('获取仪表盘数据失败:', error)
    ElMessage.error('获取仪表盘数据失败')
  }
}

onMounted(() => {
  fetchDashboardData()
})
</script>

<style scoped lang="scss">
.wharttest-dashboard {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

h1 {
  color: #2c3e50;
  margin-bottom: 20px;
  font-size: 24px;
  font-weight: 600;
}

.dashboard-cards {
  margin-bottom: 20px;
}

.dashboard-card {
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .card-content {
    padding: 20px 0;
    text-align: center;
  }
  
  .card-value {
    font-size: 36px;
    font-weight: 700;
    color: #409eff;
    margin-bottom: 10px;
  }
  
  .card-desc {
    font-size: 14px;
    color: #909399;
  }
}

.dashboard-charts {
  margin-top: 20px;
}

.chart-card {
  height: 300px;
  
  .chart-placeholder {
    width: 100%;
    height: 250px;
    background-color: #f0f2f5;
    border-radius: 4px;
    display: flex;
    justify-content: center;
    align-items: center;
    color: #909399;
    font-size: 16px;
  }
}
</style>