import request from '@/utils/request'

/**
 * 获取测试报告列表
 */
export function getReportList(params) {
  return request({
    url: '/reports/reports/',
    method: 'get',
    params
  })
}

/**
 * 获取报告详情
 */
export function getReportDetail(id) {
  return request({
    url: `/reports/reports/${id}/`,
    method: 'get'
  })
}

/**
 * 导出报告
 */
export function exportReport(id, format) {
  return request({
    url: `/reports/reports/${id}/fetch_report_file/`,
    method: 'get',
    params: { file_format: format },
    responseType: 'blob'
  })
}

/**
 * 获取报告模板列表
 */
export function getReportTemplates(params) {
  return request({
    url: '/reports/report-templates/',
    method: 'get',
    params
  })
}

/**
 * 获取报告模板详情
 */
export function getReportTemplateDetail(id) {
  return request({
    url: `/reports/report-templates/${id}/`,
    method: 'get'
  })
}

/**
 * 创建报告模板
 */
export function createReportTemplate(data) {
  return request({
    url: '/reports/report-templates/',
    method: 'post',
    data
  })
}

/**
 * 更新报告模板
 */
export function updateReportTemplate(id, data) {
  return request({
    url: `/reports/report-templates/${id}/`,
    method: 'put',
    data
  })
}

/**
 * 部分更新报告模板
 */
export function partialUpdateReportTemplate(id, data) {
  return request({
    url: `/reports/report-templates/${id}/`,
    method: 'patch',
    data
  })
}

/**
 * 删除报告模板
 */
export function deleteReportTemplate(id) {
  return request({
    url: `/reports/report-templates/${id}/`,
    method: 'delete'
  })
}

/**
 * 获取 AI 模型配置列表（来自需求分析模块）
 */
export function getAIModelList(params) {
  return request({
    url: '/requirement-analysis/api/ai-models/',
    method: 'get',
    params: { is_active: true, ...params }
  })
}

/**
 * 使用指定 AI 模型对报告进行智能分析
 */
export function analyzeReport(id, data) {
  return request({
    url: `/reports/reports/${id}/analyze/`,
    method: 'post',
    data
  })
}
