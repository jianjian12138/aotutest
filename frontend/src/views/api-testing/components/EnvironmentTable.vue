<template>
  <div class="environment-table">
    <el-table :data="data" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="环境名称" min-width="200" />
      <el-table-column prop="scope" label="作用域" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.scope === 'GLOBAL' ? 'primary' : 'success'">
            {{ scope.row.scope === 'GLOBAL' ? '全局' : '局部' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="scope === 'LOCAL'" prop="project_name" label="关联项目" width="150" />
      <el-table-column label="变量数量" width="100">
        <template #default="scope">
          {{ Object.keys(scope.row.variables || {}).length }}
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="scope">
          <el-tag v-if="scope.row.is_active" type="success" size="small">激活</el-tag>
          <el-tag v-else type="info" size="small">未激活</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_by.username" label="创建者" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="scope">
          <el-button-group>
            <el-button 
              v-if="!scope.row.is_active"
              link 
              type="success" 
              @click="$emit('activate', scope.row)"
              size="small"
            >
              激活
            </el-button>
            <el-button link type="primary" @click="viewVariables(scope.row)" size="small">
              查看变量
            </el-button>
            <el-button link type="primary" @click="$emit('edit', scope.row)" size="small">
              编辑
            </el-button>
            <el-button link type="primary" @click="$emit('duplicate', scope.row)" size="small">
              复制
            </el-button>
            <el-button link type="danger" @click="$emit('delete', scope.row)" size="small">
              删除
            </el-button>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    <!-- 查看变量对话框 -->
    <el-dialog
      v-model="showViewDialog"
      title="环境变量"
      width="600px"
    >
      <div v-if="viewingEnvironment" class="variables-view">
        <div class="env-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="环境名称">
              {{ viewingEnvironment.name }}
            </el-descriptions-item>
            <el-descriptions-item label="作用域">
              <el-tag :type="viewingEnvironment.scope === 'GLOBAL' ? 'primary' : 'success'">
                {{ viewingEnvironment.scope === 'GLOBAL' ? '全局' : '局部' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="viewingEnvironment.project_name" label="关联项目">
              {{ viewingEnvironment.project_name }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag v-if="viewingEnvironment.is_active" type="success">激活</el-tag>
              <el-tag v-else type="info">未激活</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="variables-table">
          <h4>环境变量列表</h4>
          <el-table :data="formatVariables(viewingEnvironment.variables)" style="width: 100%">
            <el-table-column prop="key" label="变量名" width="150" />
            <el-table-column prop="initialValue" label="初始值" />
            <el-table-column prop="currentValue" label="当前值" />
          </el-table>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showViewDialog = false">关闭</el-button>
        <el-button type="primary" @click="$emit('edit', viewingEnvironment)">
          编辑环境
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import dayjs from 'dayjs'

defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  scope: {
    type: String,
    default: 'GLOBAL'
  }
})

defineEmits(['edit', 'delete', 'activate', 'duplicate'])

const showViewDialog = ref(false)
const viewingEnvironment = ref(null)

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const formatVariables = (variables) => {
  if (!variables || typeof variables !== 'object') return []
  
  return Object.keys(variables).map(key => {
    const value = variables[key]
    if (typeof value === 'object') {
      return {
        key,
        initialValue: value.initialValue || '',
        currentValue: value.currentValue || value.initialValue || ''
      }
    } else {
      return {
        key,
        initialValue: value || '',
        currentValue: value || ''
      }
    }
  })
}

const viewVariables = (environment) => {
  viewingEnvironment.value = environment
  showViewDialog.value = true
}
</script>

<style scoped>
.environment-table {
  height: 100%;
}

.variables-view {
  max-height: 70vh;
  overflow-y: auto;
}

.env-info {
  margin-bottom: 20px;
}

.variables-table h4 {
  margin: 20px 0 10px 0;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}
</style>