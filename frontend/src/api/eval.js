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

export function getLeaderboard() {
  return api.get(`${base}/runs/leaderboard/`)
}

export function listRuns(params) {
  return api.get(`${base}/runs/`, { params })
}

export function runEval(runId, outputs) {
  return api.post(`${base}/runs/${runId}/run/`, { outputs })
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
