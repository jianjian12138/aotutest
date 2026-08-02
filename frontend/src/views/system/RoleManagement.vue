<template>
  <div class="role-mgmt">
    <div class="toolbar">
      <h3>角色与权限管理</h3>
      <el-button type="primary" @click="openCreate">新建角色</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="10">
        <el-table :data="roles" v-loading="loading" @row-click="selectRole" highlight-current-row border>
          <el-table-column prop="name" label="角色" min-width="120" />
          <el-table-column prop="code" label="编码" width="140" />
          <el-table-column label="操作" width="160">
            <template #default="{row}">
              <el-button size="small" @click.stop="openEdit(row)">编辑</el-button>
              <el-button size="small" type="warning" @click.stop="openAssign(row)">分配用户</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-col>

      <el-col :span="14" v-if="current">
        <el-card shadow="never">
          <template #header>当前角色：{{ current.name }}（{{ current.code }}）</template>
          <el-checkbox-group v-model="currentPerms">
            <div v-for="g in groupedPerms" :key="g.app" class="perm-group">
              <div class="perm-app">{{ g.app }}</div>
              <el-checkbox v-for="p in g.items" :key="p.id" :label="p.id" border size="small">
                {{ p.name }} <span class="perm-code">{{ p.codename }}</span>
              </el-checkbox>
            </div>
          </el-checkbox-group>
          <el-button type="success" :loading="saving" @click="savePerms">保存权限</el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- 新建/编辑角色 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑角色' : '新建角色'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="编码" required><el-input v-model="form.code" :disabled="editing" placeholder="唯一编码，如 tester" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitRole">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分配用户 -->
    <el-dialog v-model="assignVisible" title="分配用户角色" width="520px">
      <el-alert
        v-if="currentRole"
        :title="`为所选用户分配角色：当前聚焦「${currentRole.name}」`"
        type="info" :closable="false" style="margin-bottom:12px" />
      <el-form label-width="80px">
        <el-form-item label="选择用户">
          <el-select v-model="assignUser" filterable placeholder="选择用户" style="width:100%" @change="onPickUser">
            <el-option v-for="u in allUsers" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="assignUsers" multiple filterable placeholder="勾选该用户拥有的角色" style="width:100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveAssign">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'RoleManagement',
  data() {
    return {
      roles: [], loading: false, saving: false,
      permissions: [], current: null, currentPerms: [],
      dialogVisible: false, editing: null,
      form: { name: '', code: '', description: '' },
      assignVisible: false, assignUser: null, assignUsers: [], allUsers: [], currentRole: null,
    }
  },
  computed: {
    groupedPerms() {
      const map = {}
      this.permissions.forEach(p => {
        const app = p.content_type ? p.content_type.app_label : 'other'
        ;(map[app] = map[app] || []).push(p)
      })
      return Object.keys(map).map(app => ({ app, items: map[app] }))
    },
  },
  created() { this.loadRoles(); this.loadPermissions(); this.loadUsers() },
  methods: {
    unwrap(res) { const d = res.data.data || res.data; return d.results || d },
    async loadRoles() {
      this.loading = true
      try { this.roles = this.unwrap(await api.get('/roles/')) } finally { this.loading = false }
    },
    async loadPermissions() {
      try { this.permissions = this.unwrap(await api.get('/permissions/')) } catch (e) { /* ignore */ }
    },
    async loadUsers() {
      try { this.allUsers = this.unwrap(await api.get('/user-roles/')) } catch (e) { /* ignore */ }
    },
    selectRole(row) {
      this.current = row
      this.currentPerms = (row.permissions || []).map(p => p.id)
    },
    async savePerms() {
      if (!this.current) return
      this.saving = true
      try {
        await api.put(`/roles/${this.current.id}/`, { ...this.current, permissions: this.currentPerms })
        ElMessage.success('权限已保存')
        this.loadRoles()
      } catch (e) {
        ElMessage.error('保存失败：' + (e.response?.data?.message || e.message))
      } finally { this.saving = false }
    },
    openCreate() {
      this.editing = null
      this.form = { name: '', code: '', description: '' }
      this.dialogVisible = true
    },
    openEdit(row) {
      this.editing = row
      this.form = { name: row.name, code: row.code, description: row.description }
      this.dialogVisible = true
    },
    async submitRole() {
      if (!this.form.name || !this.form.code) { ElMessage.warning('请填写名称与编码'); return }
      this.saving = true
      try {
        if (this.editing) await api.put(`/roles/${this.editing.id}/`, this.form)
        else await api.post('/roles/', this.form)
        ElMessage.success('已保存')
        this.dialogVisible = false
        this.loadRoles()
      } catch (e) {
        ElMessage.error('保存失败：' + (e.response?.data?.message || e.message))
      } finally { this.saving = false }
    },
    async openAssign(row) {
      // 记录当前聚焦的角色，便于在对话框中预勾选；
      // 真正的分配以“用户”为中心（后端 set_roles 的 pk 是用户 id）。
      this.currentRole = row
      this.assignUser = null
      this.assignUsers = []
      this.assignVisible = true
    },
    async onPickUser(userId) {
      if (!userId) { this.assignUsers = []; return }
      try {
        const u = this.unwrap(await api.get(`/user-roles/${userId}/`))
        const cur = (u.roles || []).map(r => r.id)
        // 预勾选当前聚焦角色，方便一键赋予
        if (this.currentRole && !cur.includes(this.currentRole.id)) cur.push(this.currentRole.id)
        this.assignUsers = cur
      } catch (e) { this.assignUsers = [] }
    },
    async saveAssign() {
      if (!this.assignUser) { ElMessage.warning('请先选择用户'); return }
      this.saving = true
      try {
        await api.put(`/user-roles/${this.assignUser}/set_roles/`, { roles: this.assignUsers })
        ElMessage.success('用户角色已更新')
        this.assignVisible = false
      } catch (e) {
        ElMessage.error('分配失败：' + (e.response?.data?.message || e.message))
      } finally { this.saving = false }
    },
  },
}
</script>

<style scoped>
.role-mgmt { padding: 16px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.perm-group { margin-bottom: 10px; }
.perm-app { font-weight: 600; margin-bottom: 6px; color: #409eff; }
.perm-code { color: #999; font-size: 12px; margin-left: 4px; }
</style>
