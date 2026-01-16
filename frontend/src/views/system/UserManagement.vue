<template>
  <div class="user-management">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header">
          <h2 class="page-title">用户管理</h2>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索用户名/邮箱"
              clearable
              style="width: 300px; margin-right: 10px"
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="showAddDialog = true">
              <el-icon><Plus /></el-icon>
              新增用户
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="content">
        <!-- 用户列表 -->
        <el-table 
          :data="filteredUsers" 
          v-loading="loading" 
          style="width: 100%"
          border
          stripe
        >
          <el-table-column prop="id" label="用户ID" width="80" />
          <el-table-column prop="username" label="用户名" min-width="150" />
          <el-table-column prop="email" label="邮箱" min-width="200" />
          <el-table-column prop="first_name" label="名" width="100" />
          <el-table-column prop="last_name" label="姓" width="100" />
          <el-table-column prop="is_staff" label="管理员" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.is_staff ? 'success' : 'info'">
                {{ scope.row.is_staff ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="scope">
              <el-switch
                v-model="scope.row.is_active"
                active-color="#13ce66"
                inactive-color="#ff4d4f"
                @change="handleStatusChange(scope.row)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="scope">
              <el-button link type="primary" @click="handleEdit(scope.row)">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>

    <!-- 新增用户对话框 -->
    <el-dialog
      v-model="showAddDialog"
      title="新增用户"
      width="600px"
      @close="resetAddForm"
    >
      <el-form
        ref="addFormRef"
        :model="addForm"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="addForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="addForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="addForm.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="addForm.confirmPassword" type="password" placeholder="请确认密码" />
        </el-form-item>
        <el-form-item label="名" prop="first_name">
          <el-input v-model="addForm.first_name" placeholder="请输入名" />
        </el-form-item>
        <el-form-item label="姓" prop="last_name">
          <el-input v-model="addForm.last_name" placeholder="请输入姓" />
        </el-form-item>
        <el-form-item label="管理员" prop="is_staff">
          <el-switch v-model="addForm.is_staff" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddUser" :loading="submitting">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑用户"
      width="600px"
      @close="resetEditForm"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="editForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="editForm.password" type="password" placeholder="请输入密码（不修改请留空）" />
        </el-form-item>
        <el-form-item label="名" prop="first_name">
          <el-input v-model="editForm.first_name" placeholder="请输入名" />
        </el-form-item>
        <el-form-item label="姓" prop="last_name">
          <el-input v-model="editForm.last_name" placeholder="请输入姓" />
        </el-form-item>
        <el-form-item label="管理员" prop="is_staff">
          <el-switch v-model="editForm.is_staff" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpdateUser" :loading="submitting">
          更新
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

// 状态管理
const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框控制
const showAddDialog = ref(false)
const showEditDialog = ref(false)

// 表单引用
const addFormRef = ref()
const editFormRef = ref()

// 新增用户表单
const addForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  first_name: '',
  last_name: '',
  is_staff: false
})

// 编辑用户表单
const editForm = reactive({
  id: null,
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  is_staff: false
})

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== addForm.password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 格式化日期
const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

// 过滤后的用户列表
const filteredUsers = computed(() => {
  if (!searchKeyword.value) {
    return users.value
  }
  const keyword = searchKeyword.value.toLowerCase()
  return users.value.filter(user => 
    user.username.toLowerCase().includes(keyword) ||
    user.email.toLowerCase().includes(keyword)
  )
})

// 加载用户列表
const loadUsers = async () => {
  loading.value = true
  try {
    const response = await api.get('/users/users/')
    users.value = response.data.results || response.data
    total.value = response.data.count || users.value.length
  } catch (error) {
    ElMessage.error('加载用户列表失败')
    console.error('加载用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索用户
const handleSearch = () => {
  currentPage.value = 1
}

// 分页处理
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page) => {
  currentPage.value = page
}

// 重置新增表单
const resetAddForm = () => {
  Object.assign(addForm, {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    is_staff: false
  })
  addFormRef.value?.resetFields()
}

// 重置编辑表单
const resetEditForm = () => {
  Object.assign(editForm, {
    id: null,
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    is_staff: false
  })
  editFormRef.value?.resetFields()
}

// 新增用户
const handleAddUser = async () => {
  if (!addFormRef.value) return
  
  const valid = await addFormRef.value.validate()
  if (!valid) return
  
  submitting.value = true
  try {
    const response = await api.post('/users/users/', {
      username: addForm.username,
      email: addForm.email,
      password: addForm.password,
      first_name: addForm.first_name,
      last_name: addForm.last_name,
      is_staff: addForm.is_staff
    })
    
    ElMessage.success('用户创建成功')
    showAddDialog.value = false
    await loadUsers()
  } catch (error) {
    ElMessage.error('创建用户失败')
    console.error('创建用户失败:', error)
  } finally {
    submitting.value = false
  }
}

// 编辑用户
const handleEdit = (user) => {
  Object.assign(editForm, {
    id: user.id,
    username: user.username,
    email: user.email,
    password: '',
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    is_staff: user.is_staff
  })
  showEditDialog.value = true
}

// 更新用户
const handleUpdateUser = async () => {
  if (!editFormRef.value) return
  
  const valid = await editFormRef.value.validate()
  if (!valid) return
  
  submitting.value = true
  try {
    const data = {
      username: editForm.username,
      email: editForm.email,
      first_name: editForm.first_name,
      last_name: editForm.last_name,
      is_staff: editForm.is_staff
    }
    
    // 只有当密码不为空时才更新密码
    if (editForm.password) {
      data.password = editForm.password
    }
    
    await api.put(`/users/users/${editForm.id}/`, data)
    
    ElMessage.success('用户更新成功')
    showEditDialog.value = false
    await loadUsers()
  } catch (error) {
    ElMessage.error('更新用户失败')
    console.error('更新用户失败:', error)
  } finally {
    submitting.value = false
  }
}

// 删除用户
const handleDelete = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await api.delete(`/users/users/${user.id}/`)
    ElMessage.success('用户删除成功')
    await loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除用户失败')
      console.error('删除用户失败:', error)
    }
  }
}

// 修改用户状态
const handleStatusChange = async (user) => {
  try {
    await api.patch(`/users/users/${user.id}/`, {
      is_active: user.is_active
    })
    ElMessage.success('用户状态更新成功')
  } catch (error) {
    // 恢复原始状态
    user.is_active = !user.is_active
    ElMessage.error('更新用户状态失败')
    console.error('更新用户状态失败:', error)
  }
}

// 组件挂载时加载数据
onMounted(async () => {
  await loadUsers()
})
</script>

<style scoped>
.user-management {
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

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.header-actions {
  display: flex;
  align-items: center;
}
</style>