<template>
  <div class="request-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">请求管理</h2>
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
        <el-table-column prop="collection_name" label="所属集合" width="150">
          <template #default="scope">
            {{ collections.find(c => c.id === scope.row.collection)?.name || scope.row.collection }}
          </template>
        </el-table-column>
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
          :total="pagination.total"
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
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { Plus, Search, View, EditPen, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'

const router = useRouter()

// 搜索和筛选
const searchQuery = ref('')
const methodFilter = ref('')
const collectionFilter = ref('')

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 数据
const requests = ref([])
const collections = ref([])
const loading = ref(false)

// 获取集合列表
const fetchCollections = async () => {
  try {
    const response = await api.get('/performance-testing/collections/', {
      params: { page_size: 100 }
    })
    collections.value = response.data.results
  } catch (error) {
    console.error('获取集合列表失败:', error)
  }
}

// 获取请求列表
const fetchRequests = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchQuery.value,
      method: methodFilter.value,
      collection: collectionFilter.value
    }
    const response = await api.get('/performance-testing/requests/', { params })
    requests.value = response.data.results
    pagination.total = response.data.count
  } catch (error) {
    ElMessage.error('获取请求列表失败')
  } finally {
    loading.value = false
  }
}

// 对话框
const dialogVisible = ref(false)
const dialogType = ref('create')
const form = reactive({
  id: null,
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
  pagination.currentPage = 1
  fetchRequests()
}

// 处理行点击
const handleRowClick = (row) => {
  // handleViewRequest(row)
}

// 查看请求
const handleViewRequest = (row) => {
  router.push(`/performance-test/requests/${row.id}`)
}

// 编辑请求
const handleEditRequest = (row) => {
  dialogType.value = 'edit'
  form.id = row.id
  form.name = row.name
  form.collection_id = row.collection
  form.method = row.method
  form.url = row.url
  form.timeout = row.timeout
  form.description = row.description
  dialogVisible.value = true
}

// 删除请求
const handleDeleteRequest = (row) => {
  ElMessageBox.confirm('确定要删除这个请求吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/performance-testing/requests/${row.id}/`)
      ElMessage.success('请求删除成功')
      fetchRequests()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    // 取消删除
  })
}

// 新建请求
const handleCreateRequest = () => {
  dialogType.value = 'create'
  form.id = null
  form.name = ''
  form.collection_id = collectionFilter.value || (collections.value.length > 0 ? collections.value[0].id : '')
  form.method = 'GET'
  form.url = ''
  form.timeout = 3000
  form.description = ''
  dialogVisible.value = true
}

// 提交表单
const submitForm = async () => {
  if (!form.name || !form.url || !form.collection_id) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  try {
    const data = {
      name: form.name,
      collection: form.collection_id,
      method: form.method,
      url: form.url,
      timeout: form.timeout,
      description: form.description
    }
    
    if (dialogType.value === 'create') {
      await api.post('/performance-testing/requests/', data)
      ElMessage.success('请求创建成功')
    } else {
      await api.put(`/performance-testing/requests/${form.id}/`, data)
      ElMessage.success('请求更新成功')
    }
    dialogVisible.value = false
    fetchRequests()
  } catch (error) {
    ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
  }
}

// 分页变化
const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchRequests()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchRequests()
}

onMounted(() => {
  fetchCollections()
  fetchRequests()
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
.request-management {
  padding: 0;
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