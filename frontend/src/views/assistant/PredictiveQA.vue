<template>
  <BasePage title="精准测试与风险预测">
    <div class="card-container main-content">
      <el-card class="top-panel" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="title">🧪 V3.2 精准测试与风险预测 (Predictive QA)</span>
            <el-tag type="info">基于 Git 变更分析</el-tag>
          </div>
        </template>

        <el-form :inline="true" class="control-form">
          <el-form-item label="对比基准 (Base)">
            <el-select v-model="compareForm.base" placeholder="请选择分支" style="width: 150px">
              <el-option label="main" value="main" />
              <el-option label="master" value="master" />
              <el-option label="develop" value="develop" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标提交 (Head)">
            <el-select v-model="compareForm.head" placeholder="请选择或输入 Commit ID" style="width: 200px">
              <el-option label="HEAD (当前状态)" value="HEAD" />
              <el-option label="Latest Commit" value="ad6df3b" />
              <el-option label="Pre-migration" value="d702f43" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="runAnalysis">
              {{ loading ? '解析代码拓扑中...' : '提交风险评估' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <div v-if="dataLoaded && analysisResult" class="result-layout">
        <!-- 风险统计看板 -->
        <div class="stats-grid">
          <el-card shadow="never">
            <el-statistic title="影响文件总数" :value="analysisResult.changed_count" />
          </el-card>
          <el-card shadow="never">
            <el-statistic title="高风险项" :value="highRiskCount" value-style="color: #cf1322" />
          </el-card>
          <el-card shadow="never">
            <el-statistic title="建议回归用例" :value="suggestedTestCount" value-style="color: #389e0d" />
          </el-card>
        </div>

        <!-- 详细列表 -->
        <el-card class="detail-panel" shadow="never">
          <template #header>
            <div class="card-header">
              <span>🔍 变更文件风险指纹 (Impact Fingerprints)</span>
              <el-tag v-if="analysisResult.impact_items.length > 200" type="warning">仅展示前 200 项</el-tag>
            </div>
          </template>
          <el-table 
            :data="analysisResult.impact_items.slice(0, 200)" 
            stripe 
            height="500"
            style="width: 100%">
            <el-table-column prop="file" label="变更文件" min-width="300" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column label="风险等级" width="120">
              <template #default="scope">
                <el-tag :type="getRiskType(scope.row.risk)">{{ scope.row.risk }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="建议回归集">
              <template #default="scope">
                <div class="test-tags">
                  <el-tag v-for="test in scope.row.suggested_tests" :key="test" size="small" effect="plain" style="margin-right: 5px; margin-bottom: 4px">
                    {{ test }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default>
                <el-button link type="primary">一键运行</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div class="action-footer">
            <el-button type="success" size="large">启动“最小集”自动化回归任务</el-button>
          </div>
        </el-card>
      </div>
      
      <div v-else class="empty-state">
        <el-empty description="输入 Commit ID 开始分析变更对系统的影响范围" />
      </div>
    </div>
  </BasePage>
</template>

<script setup>
import { ref, reactive, computed, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const loading = ref(false)
const analysisResult = shallowRef(null)
const dataLoaded = ref(false)

const compareForm = reactive({
  base: 'main',
  head: 'HEAD'
})

const highRiskCount = computed(() => {
  if (!analysisResult.value) return 0
  return analysisResult.value.impact_items.filter(i => ['High', 'CRITICAL'].includes(i.risk)).length
})

const suggestedTestCount = computed(() => {
  if (!analysisResult.value) return 0
  const tests = new Set()
  analysisResult.value.impact_items.forEach(i => i.suggested_tests.forEach(t => tests.add(t)))
  return tests.size
})

const runAnalysis = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/assistant/predictive-qa/analyze-impact/', {
      params: { commit: compareForm.head, base: compareForm.base }
    })
    if (response.data.status === 'SUCCESS') {
      analysisResult.value = response.data
      dataLoaded.value = true
      ElMessage.success('影响范围分析完成！')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('获取分析结果失败，请检查后端 Git 连接')
  } finally {
    loading.value = false
  }
}

const getRiskType = (risk) => {
  const map = {
    'CRITICAL': 'danger',
    'High': 'danger',
    'Medium': 'warning',
    'Low': 'success'
  }
  return map[risk] || 'info'
}
</script>

<style scoped>
.main-content {
  padding: 20px;
}

.top-panel {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 18px;
  font-weight: bold;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.detail-panel {
  margin-bottom: 20px;
}

.test-tags {
  display: flex;
  flex-wrap: wrap;
}

.action-footer {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.empty-state {
  margin-top: 100px;
}
</style>
