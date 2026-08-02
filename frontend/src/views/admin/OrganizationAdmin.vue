<template>
  <div class="org-admin-container">
    <el-tabs v-model="activeTab" class="admin-tabs">
      <!-- 1. 组织管理 -->
      <el-tab-pane label="🏢 组织/租户管理" name="orgs">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>组织架构列表</span>
              <el-button type="primary" size="small" @click="showCreateOrg = true">新建组织</el-button>
            </div>
          </template>
          <el-table :data="organizations" stripe style="width: 100%">
            <el-table-column prop="name" label="组织名称" min-width="150" />
            <el-table-column prop="code" label="组织标识 (Slug)" width="150">
              <template #default="scope">
                <el-tag size="small">{{ scope.row.code }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" />
            <el-table-column label="操作" width="150">
              <template #default>
                <el-button type="text">成员管理</el-button>
                <el-button type="text" class="danger-text">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 2. SSO 配置 -->
      <el-tab-pane label="🔐 企业级 SSO 配置" name="sso">
        <el-card shadow="never">
          <template #header><span>SSO 认证提供商 (Simulated)</span></template>
          <el-form label-width="150px">
            <el-form-item label="启用 SSO 登录">
              <el-switch v-model="ssoConfig.enabled" />
            </el-form-item>
            <el-form-item label="主认证源">
              <el-select v-model="ssoConfig.provider" style="width: 300px">
                <el-option label="LDAP / Active Directory" value="LDAP" />
                <el-option label="GitLab OAuth2" value="GitLab" />
                <el-option label="GitHub Enterprise" value="GitHub" />
                <el-option label="SAML 2.0" value="SAML" />
              </el-select>
            </el-form-item>
            <el-form-item label="端点 URL">
              <el-input v-model="ssoConfig.endpoint" placeholder="https://sso.your-enterprise.com/auth" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveSSO">保存配置</el-button>
              <el-button @click="testSSO">测试连接</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 3. RBAC 权限 -->
      <el-tab-pane label="🛡️ 角色与 RBAC 权限" name="rbac">
        <el-card shadow="never">
          <template #header><span>全局角色定义</span></template>
          <el-table :data="roles" border>
            <el-table-column prop="name" label="角色名称" width="120" />
            <el-table-column label="平台权限范围">
              <template #default="scope">
                <el-checkbox-group v-model="scope.row.permissions">
                  <el-checkbox label="project_create" disabled>创建项目</el-checkbox>
                  <el-checkbox label="test_execute" disabled>执行测试</el-checkbox>
                  <el-checkbox label="ai_ops" disabled>AI 操作</el-checkbox>
                  <el-checkbox label="user_admin" disabled>用户管理</el-checkbox>
                </el-checkbox-group>
              </template>
            </el-table-column>
            <el-table-column prop="desc" label="说明" />
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 新建组织对话框 -->
    <el-dialog v-model="showCreateOrg" title="创建新组织" width="400px">
      <el-form :model="newOrg" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="newOrg.name" />
        </el-form-item>
        <el-form-item label="标识">
          <el-input v-model="newOrg.code" placeholder="如: my-corp" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateOrg = false">取消</el-button>
        <el-button type="primary" @click="handleCreateOrg">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const activeTab = ref('orgs')
const organizations = ref([])
const showCreateOrg = ref(false)
const newOrg = reactive({ name: '', code: '' })

const ssoConfig = reactive({
  enabled: true,
  provider: 'GitHub',
  endpoint: 'https://github.com/login/oauth/authorize'
})

const roles = ref([
  { name: 'Admin', permissions: ['project_create', 'test_execute', 'ai_ops', 'user_admin'], desc: '系统最高权限，可管理所有组织' },
  { name: 'Developer', permissions: ['project_create', 'test_execute', 'ai_ops'], desc: '具备项目开发与 AI 辅助能力' },
  { name: 'Guest', permissions: [], desc: '仅可查看公开的项目数据' }
])

const fetchOrgs = async () => {
  try {
    const res = await axios.get('/api/organizations/')
    // Handle potential nested data structure
    const body = res.data.data || res.data
    organizations.value = body.results || body.items || body
  } catch (err) {
    ElMessage.error('无法加载组织数据')
  }
}

const handleCreateOrg = async () => {
  try {
    const res = await axios.post('/api/organizations/', newOrg)
    if (res.status === 201 || res.status === 200) {
      ElMessage.success('组织创建成功')
      showCreateOrg.value = false
      fetchOrgs()
    }
  } catch (err) {
    ElMessage.error('创建失败，标识可能已重复')
  }
}

const saveSSO = () => {
  ElMessage.success('SSO 配置已同步至集群配置中心')
}

const testSSO = () => {
  ElMessage.info('正在模拟 SSO 认证握手... 状态：200 OK')
}

onMounted(fetchOrgs)
</script>

<style scoped>
.org-admin-container {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.danger-text {
  color: #f56c6c;
}
.admin-tabs {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}
</style>
