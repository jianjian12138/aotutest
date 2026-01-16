<template>
  <div class="project-management">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header">
          <h2 class="page-title">项目管理</h2>
          <div class="header-actions">
            <el-button type="primary" @click="handleCreateProject">
              <el-icon><Plus /></el-icon>
              新建项目
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="content">
        <!-- 搜索和筛选 -->
        <div class="search-filter">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-input
                v-model="searchQuery"
                placeholder="请输入项目名称或描述"
                prefix-icon="Search"
              />
            </el-col>
            <el-col :span="6">
              <el-select
                v-model="statusFilter"
                placeholder="项目状态"
                clearable
              >
                <el-option label="全部" value="" />
                <el-option label="活跃" value="active" />
                <el-option label="已归档" value="archived" />
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
        
        <!-- 项目列表 -->
        <el-table
          :data="projects"
          stripe
          border
          style="width: 100%"
          @row-click="handleRowClick"
        >
          <el-table-column prop="id" label="项目ID" width="100" />
          <el-table-column prop="name" label="项目名称" />
          <el-table-column prop="description" label="项目描述" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag
                :type="getStatusTagType(scope.row.status)"
                size="small"
              >
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_by" label="创建人" width="120" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="handleViewProject(scope.row)">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button size="small" type="primary" @click="handleEditProject(scope.row)">
                <el-icon><EditPen /></el-icon>
                编辑
              </el-button>
              <el-button size="small" type="danger" @click="handleDeleteProject(scope.row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="totalProjects"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>
    
    <!-- 新建项目对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建项目"
      width="600px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入项目描述"
            :rows="3"
          />
        </el-form-item>
        <el-form-item label="项目状态">
          <el-select v-model="form.status" placeholder="请选择项目状态">
            <el-option label="活跃" value="active" />
            <el-option label="已归档" value="archived" />
          </el-select>
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
const statusFilter = ref('')

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20
})
const totalProjects = ref(25)

// 项目数据
const projects = ref([
  {
    id: 1,
    name: '电商网站性能测试',
    description: '使用Locust测试电商网站的性能',
    status: 'active',
    created_by: 'admin',
    created_at: '2026-01-10 14:30:00',
    updated_at: '2026-01-10 14:30:00'
  },
  {
    id: 2,
    name: 'API服务性能测试',
    description: '测试API服务的并发处理能力',
    status: 'active',
    created_by: 'testuser',
    created_at: '2026-01-11 09:15:00',
    updated_at: '2026-01-11 09:15:00'
  },
  {
    id: 3,
    name: '管理后台性能测试',
    description: '测试管理后台的性能表现',
    status: 'archived',
    created_by: 'admin',
    created_at: '2026-01-05 16:00:00',
    updated_at: '2026-01-08 10:30:00'
  },
  {
    id: 4,
    name: '移动端APP性能测试',
    description: '测试移动端APP的API性能',
    status: 'active',
    created_by: 'testuser',
    created_at: '2026-01-12 10:00:00',
    updated_at: '2026-01-12 10:00:00'
  }
])

// 对话框
const dialogVisible = ref(false)
const form = ref({
  name: '',
  description: '',
  status: 'active'
})

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    active: 'success',
    archived: 'info'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    active: '活跃',
    archived: '已归档'
  }
  return textMap[status] || status
}

// 搜索
const handleSearch = () => {
  ElMessage.info('搜索功能开发中')
}

// 处理行点击
const handleRowClick = (row) => {
  handleViewProject(row)
}

// 查看项目
const handleViewProject = (row) => {
  router.push(`/performance-test/projects/${row.id}`)
}

// 编辑项目
const handleEditProject = (row) => {
  ElNotification({
    title: '提示',
    message: `开始编辑项目：${row.name}`,
    type: 'success'
  })
}

// 删除项目
const handleDeleteProject = (row) => {
  ElMessageBox.confirm('确定要删除这个项目吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('项目删除成功')
  }).catch(() => {
    // 取消删除
  })
}

// 新建项目
const handleCreateProject = () => {
  dialogVisible.value = true
  form.value = {
    name: '',
    description: '',
    status: 'active'
  }
}

// 提交表单
const submitForm = () => {
  ElMessage.success('项目创建成功')
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
.project-management {
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
  font-size: 20px;
  font-weight: 600;
}

.content {
  padding: 20px 0;
}

.search-filter {
  margin-bottom: 20px;
  padding: 20px 0;
  background-color: #fafafa;
  border-radius: 8px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}
</style>