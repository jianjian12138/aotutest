<template>
  <BasePage title="多模态视觉回归">
    <div class="card-container main-content">
      <el-card class="top-panel" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="title">👁️ V3.3 多模态视觉回归 (Visual AI)</span>
            <el-tag type="success">AI 语义化 UI 审计</el-tag>
          </div>
        </template>

        <el-form :inline="true" class="control-form">
          <el-form-item label="选择基准图 (Baseline)">
            <el-select 
              v-model="baselinePath" 
              placeholder="请选择基准快照" 
              style="width: 250px" 
              @change="handleSelection"
            >
              <el-option 
                v-for="item in snapshotList" 
                :key="item.id || item.path" 
                :label="item.name" 
                :value="item.path" 
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-upload
              class="upload-demo"
              action="#"
              :auto-upload="false"
              :on-change="handleImgUpload"
              :show-file-list="false"
            >
              <el-button type="primary">选择当前截图 (Current)</el-button>
            </el-upload>
          </el-form-item>
          <el-form-item>
            <el-button type="warning" :loading="isWorking" :disabled="!readyToCompare" @click="startComparison">
              {{ isWorking ? 'AI 视觉分析中...' : '启动 AI 语义对比' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <div v-if="hasPreview" class="comparison-layout">
        <!-- 左右对比图 -->
        <div class="image-viewer">
          <el-card shadow="never">
            <template #header><span> 基准图 (Baseline) </span></template>
            <el-image :src="baselinePath" fit="contain" class="preview-img">
              <template #error><div class="image-slot">请选择基准图</div></template>
            </el-image>
          </el-card>
          
          <el-card shadow="never">
            <template #header><span> 当前图 (Current) </span></template>
            <el-image v-if="targetBase64" :src="'data:image/png;base64,' + targetBase64" fit="contain" class="preview-img" />
            <div v-else class="image-slot">请上传截图</div>
          </el-card>
        </div>

        <!-- AI 解读面板 -->
        <el-card v-if="comparisonReport" class="insight-panel" :class="riskLevelClass" shadow="never">
          <template #header>
            <div class="insight-header">
              <span>🧠 AI 视觉洞察</span>
              <el-tag :type="reportTagType">{{ comparisonReport.risk_level }} Risk</el-tag>
            </div>
          </template>
          <div class="insight-content">
            <p class="status">
              <strong>检测结论:</strong> 
              <span :class="comparisonReport.diff_found ? 'danger' : 'success'">
                {{ comparisonReport.diff_found ? '发现显著 UI 异常' : '未见明显视觉回归' }}
              </span>
            </p>
            <p class="explanation">{{ comparisonReport.explanation }}</p>
          </div>
          <div class="insight-actions">
            <el-button type="success" size="small">设为新基准</el-button>
            <el-button type="info" size="small">忽略此差异</el-button>
          </div>
        </el-card>
      </div>

      <el-empty v-else description="请先设置基准图并上传当前截图以开始视觉审计" style="margin-top: 100px" />
    </div>
  </BasePage>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// --- State ---
const snapshotList = ref([])
const baselinePath = ref('')
const targetBase64 = ref('')
const isWorking = ref(false)
const comparisonReport = ref(null)

// --- Computed ---
const readyToCompare = computed(() => !!(baselinePath.value && targetBase64.value))
const hasPreview = computed(() => !!(baselinePath.value || targetBase64.value))

const riskLevelClass = computed(() => {
  if (!comparisonReport.value) return ''
  const risk = (comparisonReport.value.risk_level || 'low').toLowerCase()
  return `risk-${risk}`
})

const reportTagType = computed(() => {
  const map = { 'High': 'danger', 'Medium': 'warning', 'Low': 'info' }
  return map[comparisonReport.value?.risk_level] || 'info'
})

// --- Methods ---
const handleSelection = (val) => {
  comparisonReport.value = null
}

const handleImgUpload = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    targetBase64.value = e.target.result.split(',')[1]
    comparisonReport.value = null
  }
  reader.readAsDataURL(file.raw)
}

const startComparison = async () => {
  if (!readyToCompare.value) return
  
  isWorking.value = true
  comparisonReport.value = null
  try {
    const res = await axios.post('/api/assistant/visual-regression/compare/', {
      base_image_path: baselinePath.value,
      current_image_base64: targetBase64.value
    })
    const realData = res.data.data || res.data
    const status = res.data.status || realData.status
    if (status === 'SUCCESS') {
      comparisonReport.value = realData.data || realData
      ElMessage.success('AI 视觉分析完成')
    }
  } catch (err) {
    console.error('Visual analysis API failure:', err)
    ElMessage.error('视觉分析失败，请检查后端状态')
  } finally {
    isWorking.value = false
  }
}

// --- Lifecycle ---
onMounted(async () => {
  try {
    const res = await axios.get('/api/assistant/visual-regression/baselines/')
    const body = res.data.data || res.data
    const items = body.items || body.data || (Array.isArray(body) ? body : [])
    const status = res.data.status || body.status
    if (status === 'SUCCESS' || Array.isArray(items)) {
      snapshotList.value = items
    }
  } catch (err) {
    console.error('[V3.3] Error loading baselines:', err)
  }
})
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
.comparison-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.image-viewer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.preview-img {
  width: 100%;
  height: 400px;
  background: #f5f7fa;
  border-radius: 4px;
}
.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
  color: #909399;
  background: #f5f7fa;
}
.insight-panel {
  border-left: 5px solid #909399;
}
.risk-high { border-left-color: #f56c6c; background: #fef0f0; }
.risk-medium { border-left-color: #e6a23c; background: #fdf6ec; }
.risk-low { border-left-color: #409eff; background: #f0f9eb; }

.insight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.insight-content .status {
  margin-bottom: 10px;
  font-size: 16px;
}
.danger { color: #f56c6c; font-weight: bold; }
.success { color: #67c23a; font-weight: bold; }
.explanation {
  line-height: 1.6;
  color: #606266;
  background: #fff;
  padding: 15px;
  border-radius: 4px;
  border: 1px dashed #dcdfe6;
}
.insight-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}
</style>
