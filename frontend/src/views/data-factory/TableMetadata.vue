<template>
  <div class="table-metadata-container">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">表元数据管理</h2>
          <el-button type="primary" @click="handleRefreshMetadata" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
            {{ refreshing ? '刷新中...' : '刷新元数据' }}
          </el-button>
        </div>
      </template>
      
      <div class="content">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索表名或描述"
            clearable
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select
            v-model="databaseFilter"
            placeholder="筛选数据库"
            clearable
            class="filter-select"
          >
            <el-option label="全部" value="" />
            <el-option
              v-for="db in databases"
              :key="db"
              :label="db"
              :value="db"
            />
          </el-select>
        </div>
        
        <!-- 表列表 -->
        <el-table
          v-loading="loading"
          :data="filteredTables"
          style="width: 100%"
          border
          stripe
          :default-sort="{ prop: 'table_name', order: 'ascending' }"
        >
          <el-table-column prop="table_name" label="表名" min-width="180" />
          <el-table-column prop="description" label="表描述" min-width="250" show-overflow-tooltip />
          <el-table-column prop="database" label="数据库" width="150" />
          <el-table-column prop="schema" label="Schema" width="120" />
          <el-table-column prop="column_count" label="列数" width="100" align="center" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                @click="handleViewTableDetails(scope.row)"
              >
                查看详情
              </el-button>
              <el-button
                size="small"
                @click="handleViewColumns(scope.row)"
              >
                查看列
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
            :total="filteredTables.length"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
        
        <!-- 表详情对话框 -->
        <el-dialog
          v-model="showTableDetails"
          :title="selectedTable?.table_name || '表详情'"
          width="70%"
        >
          <div v-if="selectedTable" class="table-details">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="表名">{{ selectedTable.table_name }}</el-descriptions-item>
              <el-descriptions-item label="数据库">{{ selectedTable.database }}</el-descriptions-item>
              <el-descriptions-item label="Schema">{{ selectedTable.schema }}</el-descriptions-item>
              <el-descriptions-item label="列数">{{ selectedTable.column_count }}</el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ selectedTable.description }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ selectedTable.created_at }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ selectedTable.updated_at }}</el-descriptions-item>
            </el-descriptions>
            
            <h3 class="section-title">表列信息</h3>
            <el-table
              :data="selectedTable.columns"
              style="width: 100%"
              border
              size="small"
            >
              <el-table-column prop="name" label="列名" min-width="150" />
              <el-table-column prop="type" label="数据类型" width="150" />
              <el-table-column prop="nullable" label="可空" width="80" align="center">
                <template #default="scope">
                  <el-icon v-if="scope.row.nullable" color="#67c23a"><Check /></el-icon>
                  <el-icon v-else color="#f56c6c"><Close /></el-icon>
                </template>
              </el-table-column>
              <el-table-column prop="default_value" label="默认值" width="120" />
              <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            </el-table>
          </div>
        </el-dialog>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search, Check, Close } from '@element-plus/icons-vue'
import { getTableMetadata } from '@/api/data-factory'

// 状态管理
const loading = ref(false)
const refreshing = ref(false)
const searchKeyword = ref('')
const databaseFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const showTableDetails = ref(false)
const selectedTable = ref(null)

// 数据库列表
const databases = ref(['db1', 'db2', 'db3'])

// 表数据
const tables = ref([])

// 模拟表元数据
const mockTables = [
  {
    id: 1,
    table_name: 'users',
    description: '用户信息表',
    database: 'db1',
    schema: 'public',
    column_count: 8,
    created_at: '2023-11-01T10:00:00Z',
    updated_at: '2023-11-15T14:20:00Z',
    columns: [
      { name: 'id', type: 'int', nullable: false, default_value: null, description: '用户ID' },
      { name: 'username', type: 'varchar(50)', nullable: false, default_value: null, description: '用户名' },
      { name: 'email', type: 'varchar(100)', nullable: false, default_value: null, description: '邮箱' },
      { name: 'password_hash', type: 'varchar(255)', nullable: false, default_value: null, description: '密码哈希' },
      { name: 'first_name', type: 'varchar(50)', nullable: true, default_value: null, description: '名' },
      { name: 'last_name', type: 'varchar(50)', nullable: true, default_value: null, description: '姓' },
      { name: 'created_at', type: 'datetime', nullable: false, default_value: 'CURRENT_TIMESTAMP', description: '创建时间' },
      { name: 'updated_at', type: 'datetime', nullable: false, default_value: 'CURRENT_TIMESTAMP', description: '更新时间' }
    ]
  },
  {
    id: 2,
    table_name: 'orders',
    description: '订单表',
    database: 'db1',
    schema: 'public',
    column_count: 12,
    created_at: '2023-11-02T09:30:00Z',
    updated_at: '2023-11-14T16:45:00Z',
    columns: [
      { name: 'id', type: 'int', nullable: false, default_value: null, description: '订单ID' },
      { name: 'user_id', type: 'int', nullable: false, default_value: null, description: '用户ID' },
      { name: 'order_number', type: 'varchar(30)', nullable: false, default_value: null, description: '订单号' },
      { name: 'total_amount', type: 'decimal(10,2)', nullable: false, default_value: '0.00', description: '总金额' },
      { name: 'status', type: 'varchar(20)', nullable: false, default_value: 'PENDING', description: '订单状态' },
      { name: 'payment_method', type: 'varchar(20)', nullable: false, default_value: null, description: '支付方式' },
      { name: 'shipping_address', type: 'text', nullable: false, default_value: null, description: '收货地址' },
      { name: 'billing_address', type: 'text', nullable: false, default_value: null, description: ' billing_address' },
      { name: 'shipping_cost', type: 'decimal(10,2)', nullable: false, default_value: '0.00', description: '运费' },
      { name: 'tax_amount', type: 'decimal(10,2)', nullable: false, default_value: '0.00', description: '税额' },
      { name: 'created_at', type: 'datetime', nullable: false, default_value: 'CURRENT_TIMESTAMP', description: '创建时间' },
      { name: 'updated_at', type: 'datetime', nullable: false, default_value: 'CURRENT_TIMESTAMP', description: '更新时间' }
    ]
  },
  {
    id: 3,
    table_name: 'products',
    description: '商品表',
    database: 'db1',
    schema: 'public',
    column_count: 10,
    created_at: '2023-11-03T14:15:00Z',
    updated_at: '2023-11-13T15:30:00Z',
    columns: [
      { name: 'id', type: 'int', nullable: false, default_value: null, description: '商品ID' },
      { name: 'name', type: 'varchar(100)', nullable: false, default_value: null, description: '商品名称' },
      { name: 'description', type: 'text', nullable: true, default_value: null, description: '商品描述' },
      { name: 'price', type: 'decimal(10,2)', nullable: false, default_value: '0.00', description: '商品价格' },
      { name: 'stock_quantity', type: 'int', nullable: false, default_value: '0', description: '库存数量' },
      { name: 'category_id', type: 'int', nullable: false, default_value: null, description: '分类ID' },
      { name: 'brand_id', type: 'int', nullable: false, default_value: null, description: '品牌ID' },
      { name: 'is_active', type: 'boolean', nullable: false, default_value: 'true', description: '是否激活' },
      { name: 'created_at', type: 'datetime', nullable: false, default_value: 'CURRENT_TIMESTAMP', description: '创建时间' },
      { name: 'updated_at', type: 'datetime', nullable: false, default_value: 'CURRENT_TIMESTAMP', description: '更新时间' }
    ]
  },
  {
    id: 4,
    table_name: 'user_logins',
    description: '用户登录日志',
    database: 'db2',
    schema: 'public',
    column_count: 6,
    created_at: '2023-11-04T11:20:00Z',
    updated_at: '2023-11-12T17:15:00Z',
    columns: [
      { name: 'id', type: 'int', nullable: false, default_value: null, description: '日志ID' },
      { name: 'user_id', type: 'int', nullable: false, default_value: null, description: '用户ID' },
      { name: 'login_time', type: 'datetime', nullable: false, default_value: 'CURRENT_TIMESTAMP', description: '登录时间' },
      { name: 'ip_address', type: 'varchar(45)', nullable: false, default_value: null, description: 'IP地址' },
      { name: 'user_agent', type: 'text', nullable: true, default_value: null, description: '用户代理' },
      { name: 'success', type: 'boolean', nullable: false, default_value: 'true', description: '登录是否成功' }
    ]
  },
  {
    id: 5,
    table_name: 'ad_campaigns',
    description: '广告活动表',
    database: 'db3',
    schema: 'public',
    column_count: 9,
    created_at: '2023-11-05T16:45:00Z',
    updated_at: '2023-11-11T14:50:00Z',
    columns: [
      { name: 'id', type: 'int', nullable: false, default_value: null, description: '活动ID' },
      { name: 'name', type: 'varchar(100)', nullable: false, default_value: null, description: '活动名称' },
      { name: 'description', type: 'text', nullable: true, default_value: null, description: '活动描述' },
      { name: 'channel', type: 'varchar(50)', nullable: false, default_value: null, description: '广告渠道' },
      { name: 'start_date', type: 'date', nullable: false, default_value: null, description: '开始日期' },
      { name: 'end_date', type: 'date', nullable: true, default_value: null, description: '结束日期' },
      { name: 'budget', type: 'decimal(12,2)', nullable: false, default_value: '0.00', description: '预算' },
      { name: 'cost', type: 'decimal(12,2)', nullable: false, default_value: '0.00', description: '实际花费' },
      { name: 'revenue', type: 'decimal(12,2)', nullable: false, default_value: '0.00', description: '产生收入' }
    ]
  }
]

// 过滤后的表
const filteredTables = computed(() => {
  let result = [...tables.value]
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(table => 
      table.table_name.toLowerCase().includes(keyword) ||
      table.description.toLowerCase().includes(keyword)
    )
  }
  
  // 数据库过滤
  if (databaseFilter.value) {
    result = result.filter(table => table.database === databaseFilter.value)
  }
  
  return result
})

// 加载表数据
const loadTables = async () => {
  loading.value = true
  
  try {
    // 调用真实API
    const response = await getTableMetadata()
    tables.value = response.data.results || response.data
    loading.value = false
  } catch (error) {
    console.error('加载表数据失败:', error)
    ElMessage.error('加载表数据失败')
    loading.value = false
  }
}

// 刷新元数据
const handleRefreshMetadata = async () => {
  refreshing.value = true
  
  try {
    // 调用真实API
    await loadTables()
    ElMessage.success('元数据刷新成功')
    refreshing.value = false
  } catch (error) {
    console.error('刷新元数据失败:', error)
    ElMessage.error('刷新元数据失败')
    refreshing.value = false
  }
}

// 查看表详情
const handleViewTableDetails = (table) => {
  selectedTable.value = table
  showTableDetails.value = true
}

// 查看表列
const handleViewColumns = (table) => {
  handleViewTableDetails(table)
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
  loadTables()
})
</script>

<style scoped>
.table-metadata-container {
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
  width: 300px;
}

.filter-select {
  width: 180px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.table-details {
  padding: 10px 0;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 20px 0 10px 0;
}
</style>