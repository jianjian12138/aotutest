<template>
  <div class="tenant-mgmt">
    <div class="toolbar">
      <h3>租户（组织）管理</h3>
      <el-button type="primary" @click="openCreate">新建租户</el-button>
    </div>

    <el-table :data="list" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="code" label="编码" width="160" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="140">
        <template #default="{row}">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑租户' : '新建租户'" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="编码" required>
          <el-input v-model="form.code" :disabled="editing" placeholder="唯一英文编码" />
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'TenantManagement',
  data() {
    return {
      list: [], loading: false, saving: false,
      dialogVisible: false, editing: null,
      form: { name: '', code: '', description: '' },
    }
  },
  created() { this.load() },
  methods: {
    unwrap(res) { const d = res.data.data || res.data; return d.results || d },
    async load() {
      this.loading = true
      try { this.list = this.unwrap(await api.get('/organizations/')) }
      catch (e) { ElMessage.error('加载租户失败：' + (e.response?.data?.message || e.message)) }
      finally { this.loading = false }
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
    async submit() {
      if (!this.form.name || !this.form.code) { ElMessage.warning('请填写名称与编码'); return }
      this.saving = true
      try {
        if (this.editing) await api.put(`/organizations/${this.editing.id}/`, this.form)
        else await api.post('/organizations/', this.form)
        ElMessage.success('已保存')
        this.dialogVisible = false
        this.load()
      } catch (e) {
        ElMessage.error('保存失败：' + (e.response?.data?.message || e.message))
      } finally { this.saving = false }
    },
  },
}
</script>

<style scoped>
.tenant-mgmt { padding: 16px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
</style>
