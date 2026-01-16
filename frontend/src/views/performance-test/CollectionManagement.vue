<template>
  <div class="collection-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>集合管理</h2>
          <el-button type="primary" @click="handleCreateCollection">
            <el-icon><Plus /></el-icon>
            新建集合
          </el-button>
        </div>
      </template>
      
      <!-- 搜索和筛选 -->
      <div class="search-filter">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="请输入集合名称或描述"
              prefix-icon="Search"
            />
          </el-col>
          <el-col :span="6">
            <el-select
              v-model="projectFilter"
              placeholder="所属项目"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option
                v-for="project in projects"
                :key="project.id"
                :label="project.name"
                :value="project.id"
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
      
      <!-- 集合列表 -->
      <el-table
        :data="collections"
        stripe
        border
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="集合ID" width="100" />
        <el-table-column prop="name" label="集合名称" />
        <el-table-column prop="description" label="集合描述" show-overflow-tooltip />
        <el-table-column prop="project_name" label="所属项目" width="150" />
        <el-table-column prop="request_count" label="请求数量" width="120" />
        <el-table-column prop="created_by" label="创建人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleViewCollection(scope.row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" type="primary" @click="handleEditCollection(scope.row)">
              <el-icon><EditPen /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="danger" @click="handleDeleteCollection(scope.row)">
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
          :total="totalCollections"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 新建集合对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建集合"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="集合名称" required>
          <el-input v-model="form.name" placeholder="请输入集合名称" />
        </el-form-item>
        <el-form-item label="所属项目" required>
          <el-select v-model="form.project_id" placeholder="请选择所属项目">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="集合描述">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入集合描述"
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
const projectFilter = ref('')

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20
})
const totalCollections = ref(32)

// 项目列表（用于筛选和创建）
const projects = ref([
  { id: 1, name: '电商网站性能测试' },
  { id: 2, name: 'API服务性能测试' },
  { id: 3, name: '管理后台性能测试' },
  { id: 4, name: '移动端APP性能测试' }
])

// 集合数据
const collections = ref([
  {
    id: 1,
    name: '用户相关接口',
    description: '包含用户登录、注册、查询等接口',
    project_id: 1,
    project_name: '电商网站性能测试',
    request_count: 12,
    created_by: 'admin',
    created_at: '2026-01-10 14:30:00',
    updated_at: '2026-01-10 14:30:00'
  },
  {
    id: 2,
    name: '商品相关接口',
    description: '包含商品查询、分类、详情等接口',
    project_id: 1,
    project_name: '电商网站性能测试',
    request_count: 25,
    created_by: 'testuser',
    created_at: '2026-01-11 09:15:00',
    updated_at: '2026-01-11 09:15:00'
  },
  {
    id: 3,
    name: '订单相关接口',
    description: '包含订单创建、支付、查询等接口',
    project_id: 1,
    project_name: '电商网站性能测试',
    request_count: 18,
    created_by: 'admin',
    created_at: '2026-01-05 16:00:00',
    updated_at: '2026-01-08 10:30:00'
  },
  {
    id: 4,
    name: 'API基础接口',
    description: 'API服务的基础接口集合',
    project_id: 2,
    project_name: 'API服务性能测试',
    request_count: 42,
    created_by: 'testuser',
    created_at: '2026-01-12 10:00:00',
    updated_at: '2026-01-12 10:00:00'
  }
])

// 对话框
const dialogVisible = ref(false)
const form = ref({
  name: '',
  project_id: '',
  description: ''
})

// 搜索
const handleSearch = () => {
  ElMessage.info('搜索功能开发中')
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewCollection(row)
}

// 查看集合
const handleViewCollection = (row) => {
  router.push(`/performance-test/collections/${row.id}`)
}

// 编辑集合
const handleEditCollection = (row) => {
  ElNotification({
    title: '提示',
    message: `开始编辑集合：${row.name}`,
    type: 'success'
  })
}

// 删除集合
const handleDeleteCollection = (row) => {
  ElMessageBox.confirm('确定要删除这个集合吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('集合删除成功')
  }).catch(() => {
    // 取消删除
  })
}

// 新建集合
const handleCreateCollection = () => {
  dialogVisible.value = true
  form.value = {
    name: '',
    project_id: '',
    description: ''
  }
}

// 提交表单
const submitForm = () => {
  ElMessage.success('集合创建成功')
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
.collection-management {
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