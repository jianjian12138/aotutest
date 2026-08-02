import request from '@/utils/api'

export function getTestScripts(params) {
  return request({
    url: '/ui-automation/test-scripts/',
    method: 'get',
    params
  })
}

// 创建测试脚本

export function createTestScript(data) {
  return request({
    url: '/ui-automation/test-scripts/',
    method: 'post',
    data
  })
}

// 获取测试脚本详情

export function getTestScriptDetail(id) {
  return request({
    url: `/ui-automation/test-scripts/${id}/`,
    method: 'get'
  })
}

// 更新测试脚本

export function updateTestScript(id, data) {
  return request({
    url: `/ui-automation/test-scripts/${id}/`,
    method: 'patch',
    data
  })
}

// 删除测试脚本

export function deleteTestScript(id) {
  return request({
    url: `/ui-automation/test-scripts/${id}/`,
    method: 'delete'
  })
}

// 格式化测试脚本代码

export function formatTestScript(data) {
  return request({
    url: '/ui-automation/test-scripts/format_code/',
    method: 'post',
    data
  })
}

// 测试套件相关API

// 获取测试套件列表

export function getTestSuites(params) {
  return request({
    url: '/ui-automation/test-suites/',
    method: 'get',
    params
  })
}

// 创建测试套件

export function createTestSuite(data) {
  return request({
    url: '/ui-automation/test-suites/',
    method: 'post',
    data
  })
}

// 获取测试套件详情

export function getTestSuiteDetail(id) {
  return request({
    url: `/ui-automation/test-suites/${id}/`,
    method: 'get'
  })
}

// 更新测试套件

export function updateTestSuite(id, data) {
  return request({
    url: `/ui-automation/test-suites/${id}/`,
    method: 'patch',
    data
  })
}

// 删除测试套件

export function deleteTestSuite(id) {
  return request({
    url: `/ui-automation/test-suites/${id}/`,
    method: 'delete'
  })
}

// 获取测试套件中的测试用例

export function getTestSuiteTestCases(id) {
  return request({
    url: `/ui-automation/test-suites/${id}/test_cases/`,
    method: 'get'
  })
}

// 向测试套件添加测试用例

export function addTestCaseToTestSuite(id, data) {
  return request({
    url: `/ui-automation/test-suites/${id}/add_test_case/`,
    method: 'post',
    data
  })
}

// 从测试套件移除测试用例

export function removeTestCaseFromTestSuite(suiteId, testCaseId) {
  return request({
    url: `/ui-automation/test-suites/${suiteId}/remove_test_case/`,
    method: 'delete',
    data: { test_case_id: testCaseId }
  })
}

// 更新测试套件中测试用例的顺序

export function updateTestCaseOrder(suiteId, testCaseOrders) {
  return request({
    url: `/ui-automation/test-suites/${suiteId}/update_test_case_order/`,
    method: 'post',
    data: { test_case_orders: testCaseOrders }
  })
}

// 运行测试套件

export function runTestSuite(suiteId, data) {
  return request({
    url: `/ui-automation/test-suites/${suiteId}/run_suite/`,
    method: 'post',
    data,
    timeout: 600000  // 10分钟超时，因为套件可能包含多个测试用例
  })
}

// 测试执行相关API

// 获取测试执行列表

export function getScriptSteps(params) {
  return request({
    url: '/ui-automation/script-steps/',
    method: 'get',
    params
  })
}

export function createScriptStep(data) {
  return request({
    url: '/ui-automation/script-steps/',
    method: 'post',
    data
  })
}

export function batchCreateScriptSteps(data) {
  return request({
    url: '/ui-automation/script-steps/batch_create/',
    method: 'post',
    data
  })
}

export function updateScriptStep(id, data) {
  return request({
    url: `/ui-automation/script-steps/${id}/`,
    method: 'patch',
    data
  })
}

export function deleteScriptStep(id) {
  return request({
    url: `/ui-automation/script-steps/${id}/`,
    method: 'delete'
  })
}

// 脚本元素使用情况API

export function getTestCases(params) {
  return request({
    url: '/ui-automation/test-cases/',
    method: 'get',
    params
  })
}

// 创建测试用例

export function createTestCase(data) {
  return request({
    url: '/ui-automation/test-cases/',
    method: 'post',
    data
  })
}

// 获取测试用例详情

export function getTestCaseDetail(id) {
  return request({
    url: `/ui-automation/test-cases/${id}/`,
    method: 'get'
  })
}

// 更新测试用例

export function updateTestCase(id, data) {
  return request({
    url: `/ui-automation/test-cases/${id}/`,
    method: 'patch',
    data
  })
}

// 删除测试用例

export function deleteTestCase(id) {
  return request({
    url: `/ui-automation/test-cases/${id}/`,
    method: 'delete'
  })
}

// 运行测试用例

export function runTestCase(testCaseId, data) {
  return request({
    url: `/ui-automation/test-cases/${testCaseId}/run/`,
    method: 'post',
    data,
    timeout: 300000  // 5分钟超时，因为测试执行需要启动浏览器和执行多个步骤
  })
}

// 复制测试用例

export function copyTestCase(id) {
  return request({
    url: `/ui-automation/test-cases/${id}/copy_case/`,
    method: 'post'
  })
}

// 获取测试用例执行历史

export function getTestCaseExecutions(params) {
  return request({
    url: '/ui-automation/test-case-executions/',
    method: 'get',
    params
  })
}

// 删除测试用例执行记录

export function deleteTestCaseExecution(id) {
  return request({
    url: `/ui-automation/test-case-executions/${id}/`,
    method: 'delete'
  })
}

// 批量删除测试用例执行记录

export function batchDeleteTestCaseExecutions(ids) {
  return request({
    url: '/ui-automation/test-case-executions/batch-delete/',
    method: 'post',
    data: { ids }
  })
}

// 批量运行测试用例

export function batchRunTestCases(data) {
  return request({
    url: '/ui-automation/test-cases/batch-run/',
    method: 'post',
    data
  })
}

// 操作记录相关API

// 获取操作记录列表

export function getUiTestCaseModules(params) {
  return request({
    url: '/ui-automation/test-case-modules/tree/',
    method: 'get',
    params
  })
}

// 创建UI测试模块

export function createUiTestCaseModule(data) {
  return request({
    url: '/ui-automation/test-case-modules/',
    method: 'post',
    data
  })
}

// 更新UI测试模块

export function updateUiTestCaseModule(id, data) {
  return request({
    url: `/ui-automation/test-case-modules/${id}/`,
    method: 'patch',
    data
  })
}

// 删除UI测试模块

export function deleteUiTestCaseModule(id) {
  return request({
    url: `/ui-automation/test-case-modules/${id}/`,
    method: 'delete'
  })
}

// 批量更新UI测试模块排序

export function batchUpdateUiTestCaseModuleOrder(data) {
  return request({
    url: '/ui-automation/test-case-modules/batch_update_order/',
    method: 'post',
    data
  })
}
