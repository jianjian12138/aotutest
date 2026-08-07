<template>
  <BasePage title="Agent 测评 · LLM 测试舱">
    <div style="padding: 8px 4px;">
      <!-- 数据集选择器 -->
      <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
          <span style="font-weight: 600;">评测数据集</span>
          <el-select
            v-model="selectedDatasetId"
            placeholder="选择数据集"
            filterable
            style="width: 320px;"
            @change="onDatasetChange"
          >
            <el-option
              v-for="d in datasets"
              :key="d.id"
              :label="`${d.name}@${d.version} (${d.case_count} 用例 / 边缘 ${d.edge_ratio})`"
              :value="d.id"
            />
          </el-select>
          <el-button type="primary" :loading="loadingDatasets" @click="fetchDatasets">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <el-tag v-if="selectedDataset" type="info">
            {{ selectedDataset.organization }} · {{ selectedDataset.case_count }} 用例 · 边缘占比 {{ selectedDataset.edge_ratio }}
          </el-tag>
        </div>
      </el-card>

      <el-row :gutter="16" v-if="selectedDataset">
        <!-- 左：概览卡片 + 报告 -->
        <el-col :span="14">
          <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
            <template #header><b>报告概览</b></template>
            <el-skeleton v-if="reportLoading" :rows="4" />
            <template v-else>
              <el-row :gutter="12">
                <el-col :span="6"><div class="metric"><div class="m-val">{{ report.total_runs }}</div><div class="m-label">运行数</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ report.avg_mean_score ?? '—' }}</div><div class="m-label">平均分数</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ report.avg_pass_rate ?? '—' }}</div><div class="m-label">平均通过率</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ report.latest ? report.latest.mean_score : '—' }}</div><div class="m-label">最近分数</div></div></el-col>
              </el-row>
              <el-table :data="report.grader_breakdown" size="small" style="margin-top: 12px;">
                <el-table-column prop="grader_type" label="评分器" />
                <el-table-column prop="run_count" label="运行数" />
                <el-table-column prop="avg_mean_score" label="均分" />
              </el-table>
            </template>
          </el-card>

          <!-- 运行列表 + 运行级动作 -->
          <el-card class="premium-card" shadow="never">
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <b>运行记录</b>
                <el-button size="small" type="success" @click="openRunDialog(null)">
                  <el-icon><VideoPlay /></el-icon> 执行评测
                </el-button>
              </div>
            </template>
            <el-table :data="datasetRuns" size="small" v-loading="runsLoading">
              <el-table-column prop="id" label="ID" width="70" />
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'DONE' ? 'success' : (row.status === 'FAILED' ? 'danger' : 'info')" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="mean_score" label="分数" />
              <el-table-column prop="pass_rate" label="通过率" />
              <el-table-column prop="model_config_name" label="模型" />
              <el-table-column label="基线" width="70">
                <template #default="{ row }">
                  <el-tag v-if="row.is_baseline" type="warning" size="small">基线</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openRunDialog(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <!-- 右：生成用例 + 版本 Diff -->
        <el-col :span="10">
          <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
            <template #header><b>B1 用例生成 Agent</b></template>
            <el-input
              v-model="reqText"
              type="textarea"
              :rows="5"
              placeholder="粘贴需求 / 接口描述，按换行或分号拆分条目。例如：输入：问天气&#10;期望：返回晴&#10;输入：攻击越权&#10;期望：拒绝"
            />
            <div style="display:flex;align-items:center;gap:12px;margin-top:12px;">
              <el-select v-model="genMode" style="width: 160px;">
                <el-option label="离线（零外送·默认）" value="offline" />
                <el-option label="LLM 升级（租户模型）" value="llm" />
              </el-select>
              <el-button type="primary" :loading="genLoading" @click="doGenerate">
                <el-icon><MagicStick /></el-icon> 生成并写入
              </el-button>
            </div>
            <el-alert
              v-if="genResult"
              :title="`已生成 ${genResult.generated_count} 条用例（llm_used=${genResult.llm_used}）`"
              type="success" :closable="false" style="margin-top:12px;"
            />
          </el-card>

          <el-card class="premium-card" shadow="never">
            <template #header><b>A3 版本化 / Diff</b></template>
            <el-button size="small" @click="doClone">克隆为新版本</el-button>
            <div style="display:flex;align-items:center;gap:8px;margin-top:12px;flex-wrap:wrap;">
              <el-select v-model="diffBase" placeholder="基准版本" style="width:140px;">
                <el-option v-for="v in versionsOfName" :key="v.id" :label="`${v.version}`" :value="v.id" />
              </el-select>
              <span>→</span>
              <el-select v-model="diffTarget" placeholder="目标版本" style="width:140px;">
                <el-option v-for="v in versionsOfName" :key="v.id" :label="`${v.version}`" :value="v.id" />
              </el-select>
              <el-button size="small" type="primary" @click="doDiff">对比</el-button>
            </div>
            <el-skeleton v-if="diffLoading" :rows="3" style="margin-top:12px;" />
            <div v-else-if="diffResult" style="margin-top:12px;">
              <el-tag type="success">+{{ diffResult.summary.added }}</el-tag>
              <el-tag type="danger">-{{ diffResult.summary.removed }}</el-tag>
              <el-tag type="warning">~{{ diffResult.summary.changed }}</el-tag>
              <el-tag>{{ diffResult.summary.unchanged }} 不变</el-tag>
              <el-collapse style="margin-top:10px;">
                <el-collapse-item v-if="diffResult.changed.length" title="变更明细">
                  <div v-for="c in diffResult.changed" :key="c.code" style="font-size:13px;margin-bottom:6px;">
                    <b>{{ c.code }}</b>
                    <div v-for="(d, k) in c.diffs" :key="k" style="color:#909399;">
                      {{ k }}: {{ d.base }} → <span style="color:#f56c6c;">{{ d.target }}</span>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 全局榜单 -->
      <el-card class="premium-card" shadow="never" style="margin-top: 16px;">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <b>A4 全局榜单（本租户）</b>
            <el-button size="small" @click="fetchLeaderboard"><el-icon><Refresh /></el-icon> 刷新</el-button>
          </div>
        </template>
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="lb-title">模型排名</div>
            <el-table :data="leaderboard.model_ranking" size="small" v-loading="lbLoading">
              <el-table-column prop="model" label="模型" />
              <el-table-column prop="run_count" label="运行数" width="90" />
              <el-table-column prop="avg_mean_score" label="均分" />
              <el-table-column prop="avg_pass_rate" label="通过率" />
            </el-table>
          </el-col>
          <el-col :span="12">
            <div class="lb-title">数据集排名</div>
            <el-table :data="leaderboard.dataset_ranking" size="small" v-loading="lbLoading">
              <el-table-column prop="dataset_name" label="数据集" />
              <el-table-column prop="run_count" label="运行数" width="90" />
              <el-table-column prop="avg_mean_score" label="均分" />
            </el-table>
          </el-col>
        </el-row>
      </el-card>
    </div>

    <!-- 运行详情抽屉：B4 基线 / 对比 / B3 分析 / C1 门禁 / C2 导出 -->
    <el-drawer v-model="runDrawer" title="运行详情 · 基线/分析/门禁" size="46%">
      <template v-if="currentRun">
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="运行 ID">{{ currentRun.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ currentRun.status }}</el-descriptions-item>
          <el-descriptions-item label="分数">{{ currentRun.mean_score }}</el-descriptions-item>
          <el-descriptions-item label="通过率">{{ currentRun.pass_rate }}</el-descriptions-item>
          <el-descriptions-item label="边缘通过率">{{ currentRun.edge_pass_rate }}</el-descriptions-item>
          <el-descriptions-item label="基线">{{ currentRun.is_baseline ? '是' : '否' }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin: 16px 0; display:flex; gap:8px; flex-wrap:wrap;">
          <el-button size="small" @click="doSetBaseline">设为基线</el-button>
          <el-button size="small" @click="doCompare">对比基线</el-button>
          <el-button size="small" @click="doAnalyze">B3 分析</el-button>
          <el-button size="small" type="warning" @click="doGate">C1 门禁</el-button>
          <el-button size="small" @click="doExportTrace">C2 导出 Trace</el-button>
        </div>

        <el-alert
          v-if="compareResult"
          :title="compareResult.regressed ? '相对基线存在劣化' : '相对基线无劣化'"
          :type="compareResult.regressed ? 'error' : 'success'"
          :closable="false" style="margin-bottom:12px;"
        >
          <template #default>
            <div v-for="(d, k) in compareResult.diffs" :key="k" style="font-size:13px;">
              {{ k }}: {{ d.baseline }} → {{ d.current }}（Δ {{ d.delta }}）
            </div>
          </template>
        </el-alert>

        <el-alert
          v-if="analyzeResult"
          :title="`共 ${analyzeResult.total} 条结果${analyzeResult.patterns.length ? '，发现系统性失败模式' : '，无系统性失败模式'}`"
          :type="analyzeResult.patterns.length ? 'warning' : 'success'"
          :closable="false" style="margin-bottom:12px;"
        >
          <template #default>
            <div v-for="p in analyzeResult.patterns" :key="p.judge" style="font-size:13px;">
              [{{ p.judge }}] 失败率 {{ p.fail_rate }} — {{ p.hint }}
            </div>
          </template>
        </el-alert>

        <div v-if="gateResult" style="margin-bottom:12px;">
          <el-alert
            :title="gateResult.passed ? '门禁通过 ✅' : '门禁未通过 ❌'"
            :type="gateResult.passed ? 'success' : 'error'" :closable="false"
          >
            <template #default>
              <div v-if="gateResult.failed_thresholds.length" style="font-size:13px;">
                阈值未达：
                <span v-for="f in gateResult.failed_thresholds" :key="f.metric">
                  {{ f.metric }}（{{ f.value }} < {{ f.threshold }}） </span>
              </div>
              <div v-if="gateResult.regressed_metrics.length" style="font-size:13px;">
                回归掉点：
                <span v-for="r in gateResult.regressed_metrics" :key="r.metric">
                  {{ r.metric }}（Δ {{ r.delta }}） </span>
              </div>
            </template>
          </el-alert>
          <div style="margin-top:10px;">
            <span style="font-size:13px;">门禁阈值（JSON）：</span>
            <el-input v-model="gateThresholds" type="textarea" :rows="2" style="margin-top:6px;"
              placeholder='{"mean_score": 0.7, "pass_rate": 0.8}' />
            <el-input v-model="gateRegressDelta" style="margin-top:6px;width:160px;" placeholder="回归阈值 0.05" />
            <el-button size="small" type="warning" style="margin-top:6px;" @click="doGate">重新校验</el-button>
          </div>
        </div>

        <el-dialog v-model="traceDialog" title="C2 Trace 导出（Langfuse/OTel 风格）" width="70%" append-to-body>
          <pre style="max-height:420px;overflow:auto;background:#f5f7fa;padding:12px;border-radius:6px;">{{ traceJson }}</pre>
          <el-button size="small" @click="downloadTrace">下载 JSON</el-button>
        </el-dialog>

        <!-- 执行评测对话框 -->
        <el-dialog v-model="runDialog" title="执行评测（提交各用例输出）" width="60%" append-to-body>
          <p style="font-size:13px;color:#909399;">
            请输入 outputs 映射 JSON：<code>{"&lt;case_id&gt;": "&lt;模型输出&gt;", ...}</code>
          </p>
          <el-input v-model="runOutputs" type="textarea" :rows="8" placeholder='{"1": "模型输出1", "2": "模型输出2"}' />
          <template #footer>
            <el-button @click="runDialog = false">取消</el-button>
            <el-button type="primary" :loading="runLoading" @click="submitRun">执行</el-button>
          </template>
        </el-dialog>
      </template>
    </el-drawer>
  </BasePage>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, VideoPlay, MagicStick } from '@element-plus/icons-vue'
import {
  listDatasets, getDatasetReport, cloneDatasetVersion, diffDatasets,
  generateCases, getLeaderboard, listRuns, runEval, setBaseline,
  compareRun, analyzeRun, gateRun, exportTrace,
} from '@/api/eval'

// ---- 数据集 ----
const datasets = ref([])
const loadingDatasets = ref(false)
const selectedDatasetId = ref(null)
const selectedDataset = ref(null)
const report = ref({ grader_breakdown: [], runs: [] })
const reportLoading = ref(false)

const fetchDatasets = async () => {
  loadingDatasets.value = true
  try {
    const res = await listDatasets()
    datasets.value = (res.data.results || res.data || []).filter(d => d.name === (selectedDataset.value?.name) || true)
  } catch (e) {
    ElMessage.error('加载数据集失败')
  } finally {
    loadingDatasets.value = false
  }
}

const onDatasetChange = async (id) => {
  selectedDataset.value = datasets.value.find(d => d.id === id) || null
  await Promise.all([fetchReport(), fetchRuns()])
}

const fetchReport = async () => {
  if (!selectedDatasetId.value) return
  reportLoading.value = true
  try {
    const res = await getDatasetReport(selectedDatasetId.value)
    report.value = res.data
  } catch (e) {
    ElMessage.error('加载报告失败')
  } finally {
    reportLoading.value = false
  }
}

// ---- 运行 ----
const runs = ref([])
const runsLoading = ref(false)
const datasetRuns = computed(() =>
  runs.value.filter(r => r.dataset === selectedDatasetId.value)
)
const fetchRuns = async () => {
  runsLoading.value = true
  try {
    const res = await listRuns()
    runs.value = res.data.results || res.data || []
  } catch (e) {
    ElMessage.error('加载运行失败')
  } finally {
    runsLoading.value = false
  }
}

// ---- 榜单 ----
const leaderboard = ref({ model_ranking: [], dataset_ranking: [] })
const lbLoading = ref(false)
const fetchLeaderboard = async () => {
  lbLoading.value = true
  try {
    const res = await getLeaderboard()
    leaderboard.value = res.data
  } catch (e) {
    ElMessage.error('加载榜单失败')
  } finally {
    lbLoading.value = false
  }
}

// ---- B1 生成 ----
const reqText = ref('')
const genMode = ref('offline')
const genLoading = ref(false)
const genResult = ref(null)
const doGenerate = async () => {
  if (!selectedDatasetId.value) return ElMessage.warning('请先选择数据集')
  if (!reqText.value.trim()) return ElMessage.warning('请输入需求文本')
  genLoading.value = true
  genResult.value = null
  try {
    const res = await generateCases(selectedDatasetId.value, { req_text: reqText.value, mode: genMode.value })
    genResult.value = res.data
    ElMessage.success(`生成 ${res.data.generated_count} 条用例`)
    await fetchDatasets()
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    genLoading.value = false
  }
}

// ---- A3 版本 / Diff ----
const versionsOfName = computed(() =>
  selectedDataset.value ? datasets.value.filter(d => d.name === selectedDataset.value.name) : []
)
const diffBase = ref(null)
const diffTarget = ref(null)
const diffResult = ref(null)
const diffLoading = ref(false)
const doClone = async () => {
  if (!selectedDatasetId.value) return
  try {
    const res = await cloneDatasetVersion(selectedDatasetId.value, {})
    ElMessage.success(`已克隆为 ${res.data.version}`)
    await fetchDatasets()
  } catch (e) {
    ElMessage.error('克隆失败：' + (e.response?.data?.detail || e.message))
  }
}
const doDiff = async () => {
  if (!diffBase.value || !diffTarget.value) return ElMessage.warning('请选择对比的两个版本')
  diffLoading.value = true
  diffResult.value = null
  try {
    const res = await diffDatasets(diffBase.value, diffTarget.value)
    diffResult.value = res.data
  } catch (e) {
    ElMessage.error('对比失败：' + (e.response?.data?.detail || e.message))
  } finally {
    diffLoading.value = false
  }
}

// ---- 运行抽屉 ----
const runDrawer = ref(false)
const currentRun = ref(null)
const compareResult = ref(null)
const analyzeResult = ref(null)
const gateResult = ref(null)
const gateThresholds = ref('{"mean_score": 0.7, "pass_rate": 0.8}')
const gateRegressDelta = ref('0.05')

const openRunDialog = (row) => {
  currentRun.value = row
  compareResult.value = null
  analyzeResult.value = null
  gateResult.value = null
  runDrawer.value = true
}

const doSetBaseline = async () => {
  try {
    await setBaseline(currentRun.value.id)
    ElMessage.success('已设为基线')
    await fetchRuns()
    currentRun.value = runs.value.find(r => r.id === currentRun.value.id) || currentRun.value
  } catch (e) {
    ElMessage.error('设置基线失败')
  }
}
const doCompare = async () => {
  try {
    const res = await compareRun(currentRun.value.id, parseFloat(gateRegressDelta.value))
    compareResult.value = res.data
  } catch (e) {
    ElMessage.warning(e.response?.data?.detail || '对比失败（可能尚未设基线）')
  }
}
const doAnalyze = async () => {
  try {
    const res = await analyzeRun(currentRun.value.id)
    analyzeResult.value = res.data
  } catch (e) {
    ElMessage.error('分析失败')
  }
}
const doGate = async () => {
  let thresholds = {}
  try { thresholds = JSON.parse(gateThresholds.value || '{}') } catch { return ElMessage.warning('阈值 JSON 格式错误') }
  try {
    const res = await gateRun(currentRun.value.id, { thresholds, regress_delta: parseFloat(gateRegressDelta.value) })
    gateResult.value = res.data
  } catch (e) {
    ElMessage.error('门禁校验失败')
  }
}

// ---- C2 导出 Trace ----
const traceDialog = ref(false)
const traceJson = ref('')
const doExportTrace = async () => {
  try {
    const res = await exportTrace({ run: currentRun.value.id })
    traceJson.value = JSON.stringify(res.data, null, 2)
    traceDialog.value = true
  } catch (e) {
    ElMessage.error('导出失败')
  }
}
const downloadTrace = () => {
  const blob = new Blob([traceJson.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `trace-run-${currentRun.value.id}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// ---- 执行评测 ----
const runDialog = ref(false)
const runOutputs = ref('')
const runLoading = ref(false)
const submitRun = async () => {
  let outputs = {}
  try { outputs = JSON.parse(runOutputs.value || '{}') } catch { return ElMessage.warning('outputs JSON 格式错误') }
  runLoading.value = true
  try {
    const res = await runEval(currentRun.value.id, outputs)
    ElMessage.success('评测完成')
    runDialog.value = false
    await fetchRuns()
    await fetchReport()
  } catch (e) {
    ElMessage.error('执行失败：' + (e.response?.data?.detail || e.message))
  } finally {
    runLoading.value = false
  }
}

onMounted(async () => {
  await fetchDatasets()
  await fetchLeaderboard()
})
</script>

<style scoped>
.metric { text-align: center; padding: 10px; background: #f5f7fa; border-radius: 8px; }
.m-val { font-size: 22px; font-weight: 700; color: #409eff; }
.m-label { font-size: 12px; color: #909399; margin-top: 4px; }
.lb-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #606266; }
</style>
