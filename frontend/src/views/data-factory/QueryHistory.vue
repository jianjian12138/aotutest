<template>
  <div class="query-history-container">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">查询历史记录</h2>
          <el-button type="primary" @click="handleClearHistory">
            <el-icon><Delete /></el-icon>
            清空历史
          </el-button>
        </div>
      </template>
      
      <div class="content">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索自然语言或SQL语句"
            clearable
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select
            v-model="statusFilter"
            placeholder="筛选执行状态"
            clearable
            class="filter-select"
          >
            <el-option label="全部" value="" />
            <el-option label="成功" value="SUCCESS" />
            <el-option label="失败" value="FAILED" />
            <el-option label="运行中" value="RUNNING" />
          </el-select>
        </div>
        
        <!-- 历史记录列表 -->
        <el-table
          v-loading="loading"
          :data="filteredHistory"
          style="width: 100%"
          border
          stripe
          :default-sort="{ prop: 'created_at', order: 'descending' }"
        >
          <el-table-column label="自然语言" min-width="250" show-overflow-tooltip>
            <template #default="scope">
              {{ scope.row.sql_generation?.natural_language || '' }}
            </template>
          </el-table-column>
          <el-table-column label="SQL语句" min-width="250">
            <template #default="scope">
              <el-tooltip placement="top" :content="scope.row.sql_generation?.generated_sql || ''">
                <span class="sql-preview">{{ (scope.row.sql_generation?.generated_sql || '').substring(0, 50) }}{{ (scope.row.sql_generation?.generated_sql || '').length > 50 ? '...' : '' }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="执行状态" width="120">
            <template #default="scope">
              <el-tag
                :type="scope.row.sql_generation?.execution_status === 'SUCCESS' ? 'success' : (scope.row.sql_generation?.execution_status === 'FAILED' ? 'danger' : 'primary')"
              >
                {{ scope.row.sql_generation?.execution_status === 'SUCCESS' ? '成功' : (scope.row.sql_generation?.execution_status === 'FAILED' ? '失败' : '运行中') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="execution_time" label="执行时间(ms)" width="120" align="center">
            <template #default="scope">
              <span :class="scope.row.execution_time > 1000 ? 'slow-execution' : ''">{{ scope.row.execution_time ? Math.round(scope.row.execution_time * 1000) : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="row_count" label="结果行数" width="100" align="center" />
          <el-table-column prop="created_by.username" label="执行用户" width="120" />
          <el-table-column prop="created_at" label="执行时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                @click="handleViewResult(scope.row)"
              >
                查看结果
              </el-button>
              <el-button
                size="small"
                @click="handleReuseQuery(scope.row)"
              >
                复用查询
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="handleDeleteRecord(scope.row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="filteredHistory.length"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Delete } from '@element-plus/icons-vue'
import router from '@/router'
import { getQueryHistory } from '@/api/data-factory'

// 状态管理
const loading = ref(false)
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// 历史记录数据
const history = ref([])

// 模拟查询历史数据
const mockHistory = [
  {
    id: 1,
    natural_language: '查询最近7天的销售额',
    sql: 'SELECT DATE(order_date) as date, SUM(amount) as total_sales FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY DATE(order_date) ORDER BY date DESC',
    status: 'SUCCESS',
    execution_time: 256,
    result_count: 7,
    created_by: { username: 'admin' },
    created_at: '2023-11-15T14:30:00Z',
    updated_at: '2023-11-15T14:30:00Z'
  },
  {
    id: 2,
    natural_language: '查询活跃用户数量',
    sql: 'SELECT COUNT(DISTINCT user_id) as active_users FROM user_logins WHERE login_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)',
    status: 'SUCCESS',
    execution_time: 128,
    result_count: 1,
    created_by: { username: 'test' },
    created_at: '2023-11-15T13:45:00Z',
    updated_at: '2023-11-15T13:45:00Z'
  },
  {
    id: 3,
    natural_language: '查询订单状态分布',
    sql: 'SELECT status, COUNT(*) as count FROM orders GROUP BY status ORDER BY count DESC',
    status: 'SUCCESS',
    execution_time: 342,
    result_count: 5,
    created_by: { username: 'admin' },
    created_at: '2023-11-15T12:20:00Z',
    updated_at: '2023-11-15T12:20:00Z'
  },
  {
    id: 4,
    natural_language: '查询库存不足的商品',
    sql: 'SELECT name, sku, stock_quantity FROM products WHERE stock_quantity < 10 ORDER BY stock_quantity ASC',
    status: 'SUCCESS',
    execution_time: 456,
    result_count: 3,
    created_by: { username: 'user1' },
    created_at: '2023-11-15T11:15:00Z',
    updated_at: '2023-11-15T11:15:00Z'
  },
  {
    id: 5,
    natural_language: '查询广告投放效果',
    sql: 'SELECT channel, SUM(cost) as cost, SUM(revenue) as revenue, (SUM(revenue)/SUM(cost)) as roi FROM ad_campaigns GROUP BY channel ORDER BY roi DESC',
    status: 'SUCCESS',
    execution_time: 678,
    result_count: 4,
    created_by: { username: 'user2' },
    created_at: '2023-11-15T10:30:00Z',
    updated_at: '2023-11-15T10:30:00Z'
  },
  {
    id: 6,
    natural_language: '查询无效的SQL语句',
    sql: 'SELECT * FROM non_existent_table',
    status: 'FAILED',
    execution_time: 120,
    result_count: 0,
    error_message: 'Table not found: non_existent_table',
    created_by: { username: 'test' },
    created_at: '2023-11-15T09:45:00Z',
    updated_at: '2023-11-15T09:45:00Z'
  }
]

// 过滤后的历史记录
const filteredHistory = computed(() => {
  let result = [...history.value]
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(record => {
      const naturalLanguage = record.sql_generation?.natural_language?.toLowerCase() || ''
      const sql = record.sql_generation?.generated_sql?.toLowerCase() || ''
      return naturalLanguage.includes(keyword) || sql.includes(keyword)
    })
  }
  
  // 状态过滤
  if (statusFilter.value) {
    result = result.filter(record => record.sql_generation?.execution_status === statusFilter.value)
  }
  
  return result
})

// 加载历史记录
const loadHistory = async () => {
  loading.value = true
  
  try {
    // 调用真实API
    const response = await getQueryHistory()
    history.value = response.data.results || response.data
    loading.value = false
  } catch (error) {
    console.error('加载历史记录失败:', error)
    ElMessage.error('加载历史记录失败')
    loading.value = false
  }
}

// 查看结果
const handleViewResult = (record) => {
  ElMessage.success(`查看结果: ${record.natural_language}`)
  // 这里可以跳转到结果查看页面
  // router.push(`/data-factory/query-history/${record.id}/result`)
}

// 复用查询
const handleReuseQuery = (record) => {
  ElMessage.success(`复用查询: ${record.natural_language}`)
  // 这里可以跳转到SQL生成页面并填充内容
  // router.push({
  //   path: '/data-factory/sql-generation',
  //   query: { naturalLanguage: record.natural_language }
  // })
}

// 删除记录
const handleDeleteRecord = (record) => {
  ElMessageBox.confirm('确定要删除这条历史记录吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = history.value.indexOf(record)
    if (index > -1) {
      history.value.splice(index, 1)
      ElMessage.success('记录已删除')
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

// 清空历史
const handleClearHistory = () => {
  ElMessageBox.confirm('确定要清空所有历史记录吗？此操作不可恢复。', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'danger'
  }).then(() => {
    history.value = []
    ElMessage.success('历史记录已清空')
  }).catch(() => {
    ElMessage.info('已取消清空操作')
  })
}

// 分页事件处理
const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
}

const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
}

// 组件挂载时加载数据
onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
/* 页面特定样式 */
.page-container {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}
.query-history-container {
  width: 100%;
}

.page-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.content {
  padding: 20px 0;
}

.search-filter {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  align-items: center;
}

.search-input {
  width: 350px;
}

.filter-select {
  width: 180px;
}

.sql-preview {
  color: #1890ff;
  cursor: pointer;
}

.slow-execution {
  color: #ff4d4f;
  font-weight: bold;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>