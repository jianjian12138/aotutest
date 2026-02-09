<template>
  <div class="page-container">
    <div class="page-header">
      <h3 class="page-title">通知配置管理</h3>
      <div class="header-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新增配置
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <div class="card-container">
        <el-table :data="configs" v-loading="loading" style="width: 100%; flex: 1;">
        <el-table-column prop="name" label="配置名称" min-width="150" />
        <el-table-column prop="config_type" label="类型" width="150">
          <template #default="{ row }">
            <el-tag>{{ getConfigTypeLabel(row.config_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="webhook_url" label="Webhook URL" min-width="200" show-overflow-tooltip />
        <el-table-column label="关联项目" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.api_project_name" type="success">API: {{ row.api_project_name }}</el-tag>
            <el-tag v-else-if="row.project_name" type="info">通用: {{ row.project_name }}</el-tag>
            <span v-else>全局配置</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑通知配置' : '新增通知配置'"
      width="600px"
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="配置类型" prop="config_type">
          <el-select v-model="form.config_type" style="width: 100%">
            <el-option label="飞书机器人" value="webhook_feishu" />
            <el-option label="企业微信机器人" value="webhook_wechat" />
            <el-option label="钉钉机器人" value="webhook_dingtalk" />
            <el-option label="邮件通知" value="email" />
          </el-select>
        </el-form-item>
        
        <template v-if="form.config_type.startsWith('webhook')">
          <el-form-item label="Webhook URL" prop="webhook_url">
            <el-input v-model="form.webhook_url" />
          </el-form-item>
          <el-form-item v-if="form.config_type === 'webhook_dingtalk'" label="加签密钥" prop="secret">
            <el-input v-model="form.secret" />
          </el-form-item>
        </template>
        
        <template v-if="form.config_type === 'email'">
          <el-row :gutter="20">
            <el-col :span="16">
              <el-form-item label="SMTP服务器" prop="smtp_server">
                <el-input v-model="form.smtp_server" placeholder="例如 smtp.163.com" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="端口" prop="smtp_port">
                <el-input v-model.number="form.smtp_port" type="number" placeholder="465" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item label="用户名" prop="smtp_user">
            <el-input v-model="form.smtp_user" placeholder="邮箱账号" />
          </el-form-item>
          
          <el-form-item label="密码" prop="smtp_password">
            <el-input v-model="form.smtp_password" type="password" show-password placeholder="邮箱授权码/密码" />
          </el-form-item>
          
          <el-form-item label="发件人邮箱" prop="email_from">
            <el-input v-model="form.email_from" placeholder="显示的发送者邮箱" />
          </el-form-item>
          
          <el-form-item label="加密方式">
            <el-radio-group v-model="form.encryption">
              <el-radio label="ssl">SSL (推荐 465)</el-radio>
              <el-radio label="tls">TLS (587)</el-radio>
              <el-radio label="none">无</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="默认收件人" prop="email_recipients">
            <el-select
              v-model="form.email_recipients"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="请输入并按回车添加收件人"
              style="width: 100%"
            >
              <el-option
                v-for="item in form.email_recipients"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </el-form-item>
        </template>
        
        <el-form-item label="关联项目" prop="project_id_combined">
          <el-select v-model="form.project_id_combined" placeholder="全局配置(可选)" clearable style="width: 100%" @change="handleProjectChange">
            <el-option-group label="接口测试项目">
              <el-option
                v-for="item in apiProjects"
                :key="'api_' + item.id"
                :label="item.name"
                :value="'api_' + item.id"
              />
            </el-option-group>
            <el-option-group label="通用项目">
              <el-option
                v-for="item in projects"
                :key="'gen_' + item.id"
                :label="item.name"
                :value="'gen_' + item.id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        
        <el-form-item label="是否启用" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import schedulerApi from '@/api/scheduler'
import api from '@/utils/api'

const loading = ref(false)
const configs = ref([])
const projects = ref([])
const apiProjects = ref([])
const dialogVisible = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const form = reactive({
  id: null,
  name: '',
  config_type: 'webhook_feishu',
  webhook_url: '',
  secret: '',
  smtp_server: '',
  smtp_port: 465,
  smtp_user: '',
  smtp_password: '',
  email_from: '',
  use_ssl: true,
  use_tls: false,
  encryption: 'ssl',
  email_recipients: [],
  project: null,
  api_project: null,
  project_id_combined: '',
  is_active: true,
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  config_type: [{ required: true, message: '请选择配置类型', trigger: 'change' }],
  webhook_url: [{ required: true, message: '请输入Webhook URL', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await schedulerApi.getNotificationConfigs()
    configs.value = res.data.results || res.data
  } catch (error) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

const loadProjects = async () => {
  try {
    // 加载通用项目
    const res = await api.get('/projects/')
    projects.value = res.data.results || res.data
    
    // 加载接口测试项目
    const apiRes = await api.get('/api-testing/projects/')
    apiProjects.value = apiRes.data.results || apiRes.data
  } catch (error) {
    console.error('加载项目失败:', error)
  }
}

const handleProjectChange = (val) => {
  if (!val) {
    form.project = null
    form.api_project = null
    return
  }
  
  if (val.startsWith('api_')) {
    form.api_project = parseInt(val.replace('api_', ''))
    form.project = null
  } else if (val.startsWith('gen_')) {
    form.project = parseInt(val.replace('gen_', ''))
    form.api_project = null
  }
}

const getConfigTypeLabel = (type) => {
  const map = {
    'webhook_feishu': '飞书机器人',
    'webhook_wechat': '企业微信机器人',
    'webhook_dingtalk': '钉钉机器人',
    'email': '邮件通知'
  }
  return map[type] || type
}

const handleAdd = () => {
  isEdit.value = false
  form.id = null
  form.name = ''
  form.config_type = 'webhook_feishu'
  form.webhook_url = ''
  form.secret = ''
  form.smtp_server = ''
  form.smtp_port = 465
  form.smtp_user = ''
  form.smtp_password = ''
  form.email_from = ''
  form.encryption = 'ssl'
  form.email_recipients = []
  form.project = null
  form.api_project = null
  form.project_id_combined = ''
  form.description = ''
  form.is_active = true
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, row)
  // 确保收件人是数组
  if (!Array.isArray(form.email_recipients)) {
    form.email_recipients = []
  }
  
  // 设置组合项目 ID
  if (row.api_project) {
    form.project_id_combined = 'api_' + row.api_project
  } else if (row.project) {
    form.project_id_combined = 'gen_' + row.project
  } else {
    form.project_id_combined = ''
  }

  // 设置加密方式显示
  if (row.use_ssl) form.encryption = 'ssl'
  else if (row.use_tls) form.encryption = 'tls'
  else form.encryption = 'none'
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确认删除该配置吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await schedulerApi.deleteNotificationConfig(row.id)
      ElMessage.success('删除成功')
      loadData()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        // 准备提交的数据，过滤掉前端专用的 encryption 字段
        const submitData = { ...form }
        submitData.use_ssl = form.encryption === 'ssl'
        submitData.use_tls = form.encryption === 'tls'
        delete submitData.encryption
        delete submitData.project_id_combined
        
        if (isEdit.value) {
          await schedulerApi.updateNotificationConfig(form.id, submitData)
          ElMessage.success('更新成功')
        } else {
          await schedulerApi.createNotificationConfig(submitData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadData()
      } catch (error) {
        console.error('保存通知配置失败:', error)
        ElMessage.error(error.response?.data?.detail || (isEdit.value ? '更新失败' : '创建失败'))
      } finally {
        submitting.value = false
      }
    }
  })
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch (e) {
    return dateStr
  }
}

onMounted(() => {
  loadData()
  loadProjects()
})
</script>

<style scoped>
.page-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  background-color: var(--el-bg-color-page);
  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}

.page-header {
  flex-shrink: 0;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  margin: 0;
}

.page-title::before {
  content: '';
  width: 4px;
  height: 16px;
  background-color: var(--el-color-primary);
  margin-right: 8px;
  border-radius: 2px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.main-content {
  flex: 1;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-container {
  flex: 1;
  background: #fff;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}
</style>
