<template>
  <div class="cicd-config">
    <div class="page-header">
      <h1>🛠️ CI/CD 配置</h1>
      <p>配置 Jenkins、GitLab 等 CI/CD 服务器连接信息</p>
    </div>

    <div class="main-content">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <h2>服务器列表</h2>
            <el-button type="primary" @click="showAddDialog = true">
              <el-icon><Plus /></el-icon> 添加服务器
            </el-button>
          </div>
        </template>

        <el-table :data="servers" style="width: 100%" v-loading="loading">
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column prop="server_type" label="类型" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.server_type === 'JENKINS' ? 'warning' : 'danger'">
                {{ scope.row.server_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'info'">
                {{ scope.row.is_active ? '激活' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="editServer(scope.row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteServer(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="isEditing ? '编辑服务器' : '添加服务器'"
      width="500px"
    >
      <el-form ref="serverForm" :model="formData" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="例如: Jenkins Production" />
        </el-form-item>
        <el-form-item label="类型" prop="server_type">
          <el-select v-model="formData.server_type" placeholder="选择服务器类型" style="width: 100%">
            <el-option label="Jenkins" value="JENKINS" />
            <el-option label="GitLab" value="GITLAB" />
          </el-select>
        </el-form-item>
        <el-form-item label="URL" prop="url">
          <el-input v-model="formData.url" placeholder="例如: http://jenkins.example.com" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="Token/密码" prop="token">
          <el-input 
            v-model="formData.token" 
            type="password" 
            show-password 
            placeholder="API Token 或 密码" 
          />
        </el-form-item>
        <el-form-item label="是否激活">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="success" plain @click="testConnection" :loading="testing">测试连接</el-button>
          <el-button type="primary" @click="saveServer" :loading="saving">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const showAddDialog = ref(false)
const isEditing = ref(false)
const serverForm = ref(null)
const servers = ref([])

const formData = reactive({
  id: null,
  name: '',
  server_type: 'JENKINS',
  url: '',
  username: '',
  token: '',
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入服务器名称', trigger: 'blur' }],
  server_type: [{ required: true, message: '请选择服务器类型', trigger: 'change' }],
  url: [{ required: true, message: '请输入服务器URL', trigger: 'blur' }]
}

const loadServers = async () => {
  loading.value = true
  try {
    const response = await api.get('/cicd/servers/')
    servers.value = response.data.results || response.data
  } catch (error) {
    console.error('加载服务器失败:', error)
    ElMessage.error('加载服务器失败')
  } finally {
    loading.value = false
  }
}

const editServer = (row) => {
  isEditing.value = true
  Object.assign(formData, row)
  showAddDialog.value = true
}

const saveServer = async () => {
  if (!serverForm.value) return
  await serverForm.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (isEditing.value) {
        await api.patch(`/cicd/servers/${formData.id}/`, formData)
        ElMessage.success('更新成功')
      } else {
        await api.post('/cicd/servers/', formData)
        ElMessage.success('创建成功')
      }
      showAddDialog.value = false
      loadServers()
    } catch (error) {
      ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      saving.value = false
    }
  })
}

const deleteServer = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该服务器吗？', '警告', { type: 'warning' })
    await api.delete(`/cicd/servers/${row.id}/`)
    ElMessage.success('删除成功')
    loadServers()
  } catch (e) {
    // cancel
  }
}

const testConnection = async () => {
  // 模拟测试连接，实际后端可能需要提供一个 test_connection 接口
  testing.value = true
  try {
    // 假设后端有一个 test_connection action
    // await api.post(`/cicd/servers/test_connection/`, formData)
    setTimeout(() => {
        ElMessage.success('连接测试成功 (模拟)')
        testing.value = false
    }, 1000)
  } catch (error) {
    ElMessage.error('连接失败')
    testing.value = false
  }
}

onMounted(() => {
  loadServers()
})
</script>

<style scoped>
.cicd-config {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>