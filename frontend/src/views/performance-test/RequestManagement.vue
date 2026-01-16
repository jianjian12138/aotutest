<template>
  <div class="request-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>请求管理</h2>
          <el-button type="primary" @click="handleCreateRequest">
            <el-icon><Plus /></el-icon>
            新建请求
          </el-button>
        </div>
      </template>
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入请求名称或URL"
              prefix-icon="Search"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="methodFilter"
              placeholder="请求方法"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option label="GET" value="GET" />
              <el-option label="POST" value="POST" />
              <el-option label="PUT" value="PUT" />
              <el-option label="DELETE" value="DELETE" />
              <el-option label="PATCH" value="PATCH" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="collectionFilter"
              placeholder="所属集合"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option
                v-for="collection in collections"
                :key="collection.id"
                :label="collection.name"
                :value="collection.id"
              />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
          </el-col>
        </el-row>
      </div>
      
      <!-- 请求列表 -->
      <el-table
        :data="requests"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="请求ID" width="100" />
        <el-table-column prop="name" label="请求名称" />
        <el-table-column prop="url" label="请求URL" show-overflow-tooltip />
        <el-table-column prop="method" label="方法" width="100">
          <template #default="scope">
            <el-tag
              :type="getMethodTagType(scope.row.method)"
              size="small"
            >
              {{ scope.row.method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="collection_name" label="所属集合" width="150" />
        <el-table-column prop="timeout" label="超时时间(ms)" width="120" />
        <el-table-column prop="created_by" label="创建人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewRequest(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="primary" @click="handleEditRequest(scope.row)">
              <el-icon><EditPen /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="danger" @click="handleDeleteRequest(scope.row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalRequests"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 新建请求对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建请求"
      width="800px"
    >
      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="请求名称" required>
              <el-input v-model="form.name" placeholder="请输入请求名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属集合" required>
              <el-select v-model="form.collection_id" placeholder="请选择所属集合">
                <el-option
                  v-for="collection in collections"
                  :key="collection.id"
                  :label="collection.name"
                  :value="collection.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="请求方法" required>
              <el-select v-model="form.method" placeholder="请选择请求方法">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="DELETE" value="DELETE" />
                <el-option label="PATCH" value="PATCH" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="请求URL" required>
              <el-input v-model="form.url" placeholder="请输入请求URL" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="超时时间(ms)">
          <el-input-number v-model="form.timeout" :min="1000" :max="30000" :step="1000" />
        </el-form-item>
        <el-form-item label="请求描述">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入请求描述"
            :rows="3"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Plus, Search, View, EditPen, Delete } from '@element-plus/icons-vue'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const methodFilter = ref('')
const collectionFilter = ref('')

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20
})
const totalRequests = ref(89)

// 集合列表（用于筛选和创建）
const collections = ref([
  { id: 1, name: '用户相关接口' },
  { id: 2, name: '商品相关接口' },
  { id: 3, name: '订单相关接口' },
  { id: 4, name: 'API基础接口' }
])

// 请求数据
const requests = ref([
  {
    id: 1,
    name: '用户登录',
    url: 'https://api.example.com/login',
    method: 'POST',
    collection_id: 1,
    collection_name: '用户相关接口',
    timeout: 5000,
    created_by: 'admin',
    created_at: '2026-01-10 14:30:00',
    updated_at: '2026-01-10 14:30:00'
  },
  {
    id: 2,
    name: '获取用户信息',
    url: 'https://api.example.com/user/info',
    method: 'GET',
    collection_id: 1,
    collection_name: '用户相关接口',
    timeout: 3000,
    created_by: 'testuser',
    created_at: '2026-01-11 09:15:00',
    updated_at: '2026-01-11 09:15:00'
  },
  {
    id: 3,
    name: '创建商品',
    url: 'https://api.example.com/products',
    method: 'POST',
    collection_id: 2,
    collection_name: '商品相关接口',
    timeout: 5000,
    created_by: 'admin',
    created_at: '2026-01-05 16:00:00',
    updated_at: '2026-01-08 10:30:00'
  },
  {
    id: 4,
    name: '获取商品列表',
    url: 'https://api.example.com/products',
    method: 'GET',
    collection_id: 2,
    collection_name: '商品相关接口',
    timeout: 3000,
    created_by: 'testuser',
    created_at: '2026-01-12 10:00:00',
    updated_at: '2026-01-12 10:00:00'
  },
  {
    id: 5,
    name: '创建订单',
    url: 'https://api.example.com/orders',
    method: 'POST',
    collection_id: 3,
    collection_name: '订单相关接口',
    timeout: 5000,
    created_by: 'admin',
    created_at: '2026-01-10 14:30:00',
    updated_at: '2026-01-10 14:30:00'
  }
])

// 对话框
const dialogVisible = ref(false)
const form = ref({
  name: '',
  collection_id: '',
  method: 'GET',
  url: '',
  timeout: 3000,
  description: ''
})

// 获取请求方法标签类型
const getMethodTagType = (method) => {
  const typeMap = {
    GET: 'success',
    POST: 'primary',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return typeMap[method] || 'info'
}

// 搜索
const handleSearch = () => {
  ElMessage.info('搜索功能开发中')
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewRequest(row)
}

// 查看请求
const handleViewRequest = (row) => {
  router.push(`/performance-test/requests/${row.id}`)
}

// 编辑请求
const handleEditRequest = (row) => {
  ElNotification({
    title: '提示',
    message: `开始编辑请求：${row.name}`,
    type: 'success'
  })
}

// 删除请求
const handleDeleteRequest = (row) => {
  ElMessageBox.confirm('确定要删除这个请求吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('请求删除成功')
  }).catch(() => {
    // 取消删除
  })
}

// 新建请求
const handleCreateRequest = () => {
  dialogVisible.value = true
  form.value = {
    name: '',
    collection_id: '',
    method: 'GET',
    url: '',
    timeout: 3000,
    description: ''
  }
}

// 提交表单
const submitForm = () => {
  ElMessage.success('请求创建成功')
  dialogVisible.value = false
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.value.pageSize = size
}

const handleCurrentChange = (current) => {
  pagination.value.currentPage = current
}
</script>

<style scoped>
.request-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-filter {
  margin-bottom: 20px;
  padding: 20px 0;
  background-color: #fafafa;
  border-radius: 8px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>