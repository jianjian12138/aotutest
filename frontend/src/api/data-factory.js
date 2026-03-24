import request from '@/utils/api'

// Vanna AI配置相关API
export function getVannaConfigs(params) {
  return request({
    url: '/data-factory/vanna-configs/',
    method: 'get',
    params
  })
}

export function createVannaConfig(data) {
  return request({
    url: '/data-factory/vanna-configs/',
    method: 'post',
    data
  })
}

export function getVannaConfig(id) {
  return request({
    url: `/data-factory/vanna-configs/${id}/`,
    method: 'get'
  })
}

export function updateVannaConfig(id, data) {
  return request({
    url: `/data-factory/vanna-configs/${id}/`,
    method: 'patch',
    data
  })
}

export function deleteVannaConfig(id) {
  return request({
    url: `/data-factory/vanna-configs/${id}/`,
    method: 'delete'
  })
}

export function testVannaConnection(id) {
  return request({
    url: `/data-factory/vanna-configs/${id}/test_connection/`,
    method: 'post'
  })
}

// SQL生成相关API
export function generateSql(data) {
  return request({
    url: '/data-factory/sql-generations/generate/',
    method: 'post',
    data
  })
}

export function getSqlGenerations(params) {
  return request({
    url: '/data-factory/sql-generations/',
    method: 'get',
    params
  })
}

export function executeSql(id) {
  return request({
    url: `/data-factory/sql-generations/${id}/execute/`,
    method: 'post'
  })
}

// 数据工厂项目相关API
export function getDataFactoryProjects(params) {
  return request({
    url: '/data-factory/projects/',
    method: 'get',
    params
  })
}

export function createDataFactoryProject(data) {
  return request({
    url: '/data-factory/projects/',
    method: 'post',
    data
  })
}

export function getDataFactoryProject(id) {
  return request({
    url: `/data-factory/projects/${id}/`,
    method: 'get'
  })
}

export function updateDataFactoryProject(id, data) {
  return request({
    url: `/data-factory/projects/${id}/`,
    method: 'put',
    data
  })
}

export function deleteDataFactoryProject(id) {
  return request({
    url: `/data-factory/projects/${id}/`,
    method: 'delete'
  })
}

// 保存的查询相关API
export function getSavedQueries(params) {
  return request({
    url: '/data-factory/saved-queries/',
    method: 'get',
    params
  })
}

export function createSavedQuery(data) {
  return request({
    url: '/data-factory/saved-queries/',
    method: 'post',
    data
  })
}

export function toggleSavedQueryFavorite(id) {
  return request({
    url: `/data-factory/saved-queries/${id}/toggle_favorite/`,
    method: 'post'
  })
}

export function deleteSavedQuery(id) {
  return request({
    url: `/data-factory/saved-queries/${id}/`,
    method: 'delete'
  })
}

// 表元数据相关API
export function getTableMetadata(params) {
  return request({
    url: '/data-factory/table-metadata/',
    method: 'get',
    params
  })
}

export function refreshTableMetadata(id) {
  return request({
    url: `/data-factory/table-metadata/${id}/refresh/`,
    method: 'post'
  })
}

export function batchRefreshTableMetadata(data) {
  return request({
    url: '/data-factory/table-metadata/batch_refresh/',
    method: 'post',
    data
  })
}

// 查询历史相关API
export function getQueryHistory(params) {
  return request({
    url: '/data-factory/query-histories/',
    method: 'get',
    params
  })
}

// 仪表板相关API
export function getDashboardSummary() {
  return request({
    url: '/data-factory/dashboard/summary/',
    method: 'get'
  })
}

export function inferSchemaFromTable(tableId) {
  return request({
    url: '/data-factory/data-generator/infer_from_table/',
    method: 'post',
    data: { table_id: tableId }
  })
}