<template>
  <div class="ni-placeholder">
    <el-result
      icon="info"
      :title="moduleName + ' 能力本期未交付'"
      :sub-title="message || '该模块正在规划中，暂未开放。如需启用请与平台管理员联系。'"
    >
      <template #extra>
        <el-tag v-if="eta" type="warning" effect="plain">{{ eta }}</el-tag>
      </template>
    </el-result>

    <el-card v-if="planned && planned.length" class="planned-card" shadow="never">
      <template #header>规划能力</template>
      <el-row :gutter="16">
        <el-col
          v-for="item in planned"
          :key="(item && (item.key || item.name)) || item"
          :xs="12"
          :sm="12"
          :md="6"
          style="margin-bottom: 16px"
        >
          <el-card shadow="hover" class="planned-item">
            <div class="planned-title">{{ typeof item === 'string' ? item : (item && item.name) }}</div>
            <div class="planned-desc">{{ typeof item === 'string' ? '' : (item && item.desc) }}</div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
defineProps({
  moduleName: { type: String, default: '该模块' },
  message: { type: String, default: '' },
  planned: { type: Array, default: () => [] },
  eta: { type: String, default: '规划中' }
})
</script>

<style scoped>
.ni-placeholder {
  padding: 12px 0;
}
.planned-card {
  max-width: 960px;
  margin: 0 auto;
}
.planned-item {
  height: 100%;
  text-align: center;
}
.planned-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}
.planned-desc {
  font-size: 12px;
  color: #909399;
}
</style>
