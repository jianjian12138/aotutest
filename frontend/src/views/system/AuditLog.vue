<template>
  <div class="audit-log">
    <div class="toolbar">
      <el-select v-model="filters.action" placeholder="动作" clearable style="width:140px" @change="load">
        <el-option v-for="a in actions" :key="a" :label="a" :value="a" />
      </el-select>
      <el-input v-model="filters.search" placeholder="路径/IP/trace_id 搜索" clearable style="width:280px"
        @clear="load" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="list" v-loading="loading" border stripe height="calc(100vh - 220px)">
      <el-table-column prop="created_at" label="时间" width="170" />
      <el-table-column prop="action" label="动作" width="100" />
      <el-table-column prop="method" label="方法" width="90" />
      <el-table-column prop="path" label="路径" min-width="220" show-overflow-tooltip />
      <el-table-column prop="user_name" label="用户" width="120" />
      <el-table-column prop="ip_address" label="IP" width="140" />
      <el-table-column prop="response_status" label="状态码" width="90" />
      <el-table-column prop="trace_id" label="Trace" width="150" show-overflow-tooltip />
    </el-table>

    <el-pagination v-if="total>0" class="pager" background layout="prev,pager,next,total"
      :total="total" :page-size="pageSize" @current-change="onPage" />
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'AuditLog',
  data() {
    return {
      list: [], total: 0, loading: false, pageSize: 20, page: 1,
      filters: { action: '', search: '' },
      actions: ['CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'OTHER'],
    }
  },
  created() { this.load() },
  methods: {
    async load() {
      this.loading = true
      try {
        const params = { page: this.page, page_size: this.pageSize }
        if (this.filters.action) params.action = this.filters.action
        if (this.filters.search) params.search = this.filters.search
        const res = await api.get('/audit/', { params })
        const d = res.data.data || res.data
        this.list = d.results || d
        this.total = d.count || this.list.length
      } catch (e) {
        ElMessage.error('加载审计日志失败：' + (e.response?.data?.message || e.message))
      } finally { this.loading = false }
    },
    onPage(p) { this.page = p; this.load() },
  },
}
</script>

<style scoped>
.audit-log { padding: 16px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 16px; justify-content: flex-end; }
</style>
