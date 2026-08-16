import api from '@/utils/api'

// 评测舱（agent 测评 + LLM 测试）API —— 对应后端 apps.eval_pod
// 全部接口前缀 /api/eval/（api 实例 baseURL 已为 /api）
const base = '/eval'

export function listDatasets(params) {
  return api.get(`${base}/datasets/`, { params })
}

export function getDatasetReport(id) {
  return api.get(`${base}/datasets/${id}/report/`)
}

export function cloneDatasetVersion(id, payload) {
  return api.post(`${base}/datasets/${id}/clone_version/`, payload)
}

export function diffDatasets(baseId, targetId) {
  return api.get(`${base}/datasets/diff/`, { params: { base: baseId, target: targetId } })
}

export function generateCases(id, payload) {
  return api.post(`${base}/datasets/${id}/generate_cases/`, payload)
}

export function getLeaderboard(params) {
  return api.get(`${base}/runs/leaderboard/`, { params })
}

// E3/E4：单运行 Elo 排名 + 报告富化（校准/热力图）
export function getRunElo(runId) {
  return api.get(`${base}/runs/${runId}/elo/`)
}

export function getRunReport(runId) {
  return api.get(`${base}/runs/${runId}/report/`)
}

// P3-17 分层报告产物：L0 总览 + L1 分类（角色/边缘/评分器）+ L2 失败 TopN
export function getRunLayeredReport(runId) {
  return api.get(`${base}/runs/${runId}/report_layered/`)
}

export function getDatasetLayeredReport(datasetId) {
  return api.get(`${base}/datasets/${datasetId}/report_layered/`)
}

// E7：从标准 Benchmark 模板新建数据集
export function createFromTemplate(payload) {
  return api.post(`${base}/datasets/from_template/`, payload)
}

export function listRuns(params) {
  return api.get(`${base}/runs/`, { params })
}

export function runEval(runId, outputs, extra = {}) {
  return api.post(`${base}/runs/${runId}/run/`, { outputs, ...extra })
}

// P3-6 E2E Harness：经 MockHarness / RealHarness 端到端驱动被测 agent 并评测
export function runHarness(runId, payload) {
  return api.post(`${base}/runs/${runId}/run_harness/`, payload)
}

export function setBaseline(runId) {
  return api.post(`${base}/runs/${runId}/set_baseline/`)
}

export function compareRun(runId, regressDelta) {
  return api.get(`${base}/runs/${runId}/compare/`, { params: { regress_delta: regressDelta } })
}

export function analyzeRun(runId) {
  return api.get(`${base}/runs/${runId}/analyze/`)
}

export function gateRun(runId, payload) {
  return api.post(`${base}/runs/${runId}/gate/`, payload)
}

export function exportTrace(params) {
  return api.get(`${base}/traces/export/`, { params })
}

// P3-15 失败 case Trace 回放
export function getRunCaseTraces(runId) {
  return api.get(`${base}/runs/${runId}/case_traces/`)
}

export function getTracePlayback(params) {
  // params: { run, case }
  return api.get(`${base}/traces/playback/`, { params })
}

export function getTraceReplay(traceId) {
  return api.get(`${base}/traces/${traceId}/replay/`)
}

// P3-8 OTel 回流：列出某数据集下用例 + 导入 OTLP/JSON trace
export function listCases(params) {
  // params: { dataset } 过滤
  return api.get(`${base}/cases/`, { params })
}

export function ingestOtelTrace(payload) {
  // payload: { run, case, payload(OTLP/JSON | {spans:[...]} | 裸列表) }
  return api.post(`${base}/traces/ingest/`, payload)
}

// P3-14 Copilot 对话入口 + eval-plan-designer
export function designPlan(payload) {
  return api.post(`${base}/plans/design/`, payload)
}

export function confirmPlan(planId, payload = {}) {
  return api.post(`${base}/plans/${planId}/confirm/`, payload)
}

// P3-13 知识中枢 RAG
export function listKnowledge(params) {
  return api.get(`${base}/knowledge/`, { params })
}

export function createKnowledge(payload) {
  return api.post(`${base}/knowledge/`, payload)
}

export function deleteKnowledge(id) {
  return api.delete(`${base}/knowledge/${id}/`)
}

export function searchKnowledge(payload) {
  return api.post(`${base}/knowledge/search/`, payload)
}

// P3-16 定时评测（平台内部调度模型）+ IM 通知（飞书/企微/钉钉）
export function listGraders(params) {
  return api.get(`${base}/graders/`, { params })
}

export function listSchedules(params) {
  return api.get(`${base}/schedules/`, { params })
}

export function createSchedule(payload) {
  return api.post(`${base}/schedules/`, payload)
}

export function updateSchedule(id, payload) {
  return api.patch(`${base}/schedules/${id}/`, payload)
}

export function deleteSchedule(id) {
  return api.delete(`${base}/schedules/${id}/`)
}

export function fireSchedule(id) {
  return api.post(`${base}/schedules/${id}/fire_now/`)
}

export function testScheduleNotify(payload) {
  return api.post(`${base}/schedules/notify_test/`, payload)
}

// 被评测的 agent / 模型配置（可选，自动产出 outputs）
export function listAgentModels(params) {
  return api.get('/requirement-analysis/ai-models/', { params })
}

// P3-4 评测技能版本化
export function listSkillVersions(params) {
  return api.get(`${base}/skill-versions/`, { params })
}

export function publishSkillVersion(payload) {
  return api.post(`${base}/skill-versions/publish/`, payload)
}

export function setActiveSkillVersion(id) {
  return api.post(`${base}/skill-versions/${id}/set_active/`)
}

export function diffSkillVersion(id, other) {
  return api.get(`${base}/skill-versions/${id}/diff/`, { params: { other } })
}

export function currentSkillVersion(params) {
  return api.get(`${base}/skill-versions/current/`, { params })
}

// P3-5 冷启动标准：状态查询 + 默认评分器模板一键种子
export function getColdStartStatus() {
  return api.get(`${base}/cold-start/status/`)
}

export function applyColdStart() {
  return api.post(`${base}/cold-start/apply/`)
}

// P3-9 边缘用例规则：CRUD + 默认规则播种 + 对数据集生成边缘用例
export function listEdgeRules(params) {
  return api.get(`${base}/edge-rules/`, { params })
}

export function createEdgeRule(payload) {
  return api.post(`${base}/edge-rules/`, payload)
}

export function seedEdgeRules() {
  return api.post(`${base}/edge-rules/seed_defaults/`)
}

export function applyEdgeRules(payload) {
  return api.post(`${base}/edge-rules/apply/`, payload)
}

// P3-11 评判模型强度自校准：记录列表 + 一键评估
export function listJudgeStrengths(params) {
  return api.get(`${base}/judge-strengths/`, { params })
}

export function assessJudgeStrength() {
  return api.post(`${base}/judge-strengths/assess/`)
}
