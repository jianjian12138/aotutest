<template>
  <div class="history-table">
    <el-table 
      :data="data" 
      v-loading="loading" 
      style="width: 100%"
      @selection-change="$emit('selection-change', $event)"
    >
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column prop="request.name" label="请求名称" min-width="200" />
      <el-table-column prop="request.method" label="方法" width="80">
        <template #default="scope">
          <el-tag :type="getMethodType(scope.row.request.method)" size="small">
            {{ scope.row.request.method }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="request_data.url" label="URL" min-width="300" show-overflow-tooltip />
      <el-table-column prop="status_code" label="状态码" width="100">
        <template #default="scope">
          <el-tag 
            v-if="scope.row.status_code"
            :type="getStatusType(scope.row.status_code)" 
            size="small"
          >
            {{ scope.row.status_code }}
          </el-tag>
          <el-tag v-else type="danger" size="small">错误</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="response_time" label="响应时间" width="100">
        <template #default="scope">
          {{ scope.row.response_time?.toFixed(0) || 0 }}ms
        </template>
      </el-table-column>
      <el-table-column prop="environment.name" label="环境" width="120">
        <template #default="scope">
          {{ scope.row.environment?.name || '无环境' }}
        </template>
      </el-table-column>
      <el-table-column prop="executed_by.username" label="执行者" width="120" />
      <el-table-column prop="executed_at" label="执行时间" width="160">
        <template #default="scope">
          {{ formatDate(scope.row.executed_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="$emit('view-detail', scope.row)" size="small">
            查看详情
          </el-button>
          <el-button link type="primary" @click="$emit('retry-request', scope.row)" size="small">
            重新发送
          </el-button>
          <el-button link type="danger" @click="$emit('delete-item', scope.row)" size="small">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import dayjs from 'dayjs'

defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['view-detail', 'retry-request', 'selection-change', 'delete-item'])

const getMethodType = (method) => {
  const typeMap = {
    'GET': 'success',
    'POST': 'primary', 
    'PUT': 'warning',
    'DELETE': 'danger',
    'PATCH': 'info'
  }
  return typeMap[method] || 'info'
}

const getStatusType = (status) => {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'warning'
  if (status >= 400) return 'danger'
  return 'info'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('MM-DD HH:mm')
}
</script>

<style scoped>
.history-table {
  height: 100%;
}
</style>