<template>
  <div class="defect-mgmt">
    <div class="toolbar">
      <el-select v-model="filters.status" placeholder="状态" clearable style="width:140px" @change="loadDefects">
        <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filters.severity" placeholder="严重程度" clearable style="width:140px" @change="loadDefects">
        <el-option v-for="s in severityOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-input v-model="filters.search" placeholder="标题/描述搜索" clearable style="width:240px" @clear="loadDefects" @keyup.enter="loadDefects" />
      <el-button type="primary" @click="loadDefects">查询</el-button>
      <el-button type="success" @click="openCreate">提缺陷</el-button>
    </div>

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column label="状态" width="110">
        <template #default="{row}">
          <el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="严重程度" width="110">
        <template #default="{row}">{{ severityLabel(row.severity) }}</template>
      </el-table-column>
      <el-table-column label="指派人" width="120">
        <template #default="{row}">{{ row.assignee ? row.assignee.username : '—' }}</template>
      </el-table-column>
      <el-table-column label="报告人" width="120">
        <template #default="{row}">{{ row.reporter ? row.reporter.username : '—' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{row}">
          <el-button v-for="t in row.allowed_transitions" :key="t" size="small" @click="doTransition(row, t)">
            {{ statusLabel(t) }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-if="total>0" class="pager" background layout="prev,pager,next,total"
      :total="total" :page-size="pageSize" @current-change="onPage" />

    <!-- 创建缺陷 -->
    <el-dialog v-model="createVisible" title="提交缺陷" width="640px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="缺陷标题" />
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="form.severity" style="width:100%">
            <el-option v-for="s in severityOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width:100%">
            <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联执行ID">
          <el-input v-model.number="form.related_execution_id" type="number" placeholder="可选：测试执行用例 ID" />
        </el-form-item>
        <el-form-item label="环境">
          <el-input v-model="form.environment" placeholder="如 staging / prod" />
        </el-form-item>
        <el-form-item label="复现步骤">
          <el-input v-model="form.steps" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

const STATUS = [
  { value: 'NEW', label: '新建' }, { value: 'OPEN', label: '待修复' },
  { value: 'FIXING', label: '修复中' }, { value: 'VERIFIED', label: '待验证' },
  { value: 'CLOSED', label: '已关闭' }, { value: 'REJECTED', label: '已拒绝' },
  { value: 'REOPENED', label: '重新打开' },
]
const SEVERITY = [
  { value: 'critical', label: '致命' }, { value: 'major', label: '严重' },
  { value: 'minor', label: '一般' }, { value: 'trivial', label: '轻微' },
]
const PRIORITY = [
  { value: 'P0', label: 'P0-最高' }, { value: 'P1', label: 'P1-高' },
  { value: 'P2', label: 'P2-中' }, { value: 'P3', label: 'P3-低' },
]

export default {
  name: 'DefectManagement',
  data() {
    return {
      list: [], total: 0, loading: false, pageSize: 20, page: 1,
      filters: { status: '', severity: '', search: '' },
      createVisible: false, submitting: false,
      form: { title: '', severity: 'major', priority: 'P2', steps: '', description: '', environment: '', related_execution_id: null },
      statusOptions: STATUS, severityOptions: SEVERITY, priorityOptions: PRIORITY,
    }
  },
  created() { this.loadDefects() },
  methods: {
    statusLabel(v) { return (STATUS.find(s => s.value === v) || {}).label || v },
    severityLabel(v) { return (SEVERITY.find(s => s.value === v) || {}).label || v },
    statusTag(v) {
      return { NEW: 'info', OPEN: 'warning', FIXING: 'primary', VERIFIED: 'success', CLOSED: '', REJECTED: 'danger', REOPENED: 'warning' }[v] || 'info'
    },
    async loadDefects() {
      this.loading = true
      try {
        const params = { page: this.page, page_size: this.pageSize }
        if (this.filters.status) params.status = this.filters.status
        if (this.filters.severity) params.severity = this.filters.severity
        if (this.filters.search) params.search = this.filters.search
        const res = await api.get('/defects/defects/', { params })
        const d = res.data.data || res.data
        this.list = d.results || d
        this.total = d.count || this.list.length
      } catch (e) {
        ElMessage.error('加载缺陷失败：' + (e.response?.data?.message || e.message))
      } finally { this.loading = false }
    },
    onPage(p) { this.page = p; this.loadDefects() },
    openCreate() {
      this.form = { title: '', severity: 'major', priority: 'P2', steps: '', description: '', environment: '', related_execution_id: null }
      this.createVisible = true
    },
    async submitCreate() {
      if (!this.form.title) { ElMessage.warning('请填写标题'); return }
      this.submitting = true
      try {
        const payload = { ...this.form }
        if (!payload.related_execution_id) delete payload.related_execution_id
        await api.post('/defects/defects/', payload)
        ElMessage.success('缺陷已提交')
        this.createVisible = false
        this.loadDefects()
      } catch (e) {
        ElMessage.error('提交失败：' + (e.response?.data?.message || e.message))
      } finally { this.submitting = false }
    },
    async doTransition(row, to) {
      try {
        await api.post(`/defects/defects/${row.id}/transition/`, { to_status: to, comment: '' })
        ElMessage.success('已流转至：' + this.statusLabel(to))
        this.loadDefects()
      } catch (e) {
        ElMessage.error('流转失败：' + (e.response?.data?.message || e.message))
      }
    },
  },
}
</script>

<style scoped>
.defect-mgmt { padding: 16px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 16px; justify-content: flex-end; }
</style>
