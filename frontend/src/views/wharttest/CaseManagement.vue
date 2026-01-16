<template>
  <div class="case-management">
    <div class="header">
      <h2>用例管理</h2>
      <p>管理由 AI 生成或人工创建的测试用例。</p>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-input v-model="searchQuery" placeholder="搜索用例..." style="width: 300px" prefix-icon="Search" />
        <el-select v-model="filterStatus" placeholder="状态" style="width: 120px; margin-left: 10px">
          <el-option label="全部" value="" />
          <el-option label="待评审" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已废弃" value="rejected" />
        </el-select>
        <div class="actions" style="margin-left: auto">
          <el-button type="primary" @click="generateCases">
            <el-icon><MagicStick /></el-icon> AI 生成用例
          </el-button>
          <el-button type="success" @click="createCase">
            <el-icon><Plus /></el-icon> 新建用例
          </el-button>
        </div>
      </div>

      <el-table :data="cases" style="width: 100%; margin-top: 20px" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="用例标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="module" label="所属模块" width="120" />
        <el-table-column prop="priority" label="优先级" width="100">
           <template #default="scope">
             <el-tag :type="getPriorityType(scope.row.priority)">{{ scope.row.priority }}</el-tag>
           </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
             <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="120">
           <template #default="scope">
             <el-tag effect="plain" :type="scope.row.source === 'AI' ? 'warning' : ''">{{ scope.row.source }}</el-tag>
           </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
            <el-button size="small" type="primary" v-if="scope.row.status === 'pending'" @click="approveCase(scope.row)">通过</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination background layout="prev, pager, next" :total="100" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Search, MagicStick, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const searchQuery = ref('')
const filterStatus = ref('')

const cases = ref([
  { id: 101, title: '用户登录-正常流程', module: 'Auth', priority: 'P0', status: 'approved', source: 'Manual' },
  { id: 102, title: '用户登录-密码错误', module: 'Auth', priority: 'P1', status: 'approved', source: 'Manual' },
  { id: 103, title: '用户注册-邮箱格式校验', module: 'Auth', priority: 'P1', status: 'pending', source: 'AI' },
  { id: 104, title: '商品搜索-关键字为空', module: 'Product', priority: 'P2', status: 'pending', source: 'AI' },
])

const getPriorityType = (p) => {
  const map = { 'P0': 'danger', 'P1': 'warning', 'P2': 'info' }
  return map[p] || ''
}

const getStatusType = (s) => {
  const map = { 'approved': 'success', 'pending': 'warning', 'rejected': 'info' }
  return map[s] || ''
}

const getStatusText = (s) => {
  const map = { 'approved': '已通过', 'pending': '待评审', 'rejected': '已废弃' }
  return map[s] || s
}

const generateCases = () => {
  ElMessage.info('正在调用 AI 生成测试用例...')
  // 模拟生成
  setTimeout(() => {
    cases.value.unshift({
      id: 105 + Math.floor(Math.random() * 100),
      title: 'AI 生成的新测试用例 - ' + new Date().toLocaleTimeString(),
      module: 'Auto',
      priority: 'P1',
      status: 'pending',
      source: 'AI'
    })
    ElMessage.success('生成完成')
  }, 1500)
}

const createCase = () => {
  ElMessage.info('打开新建用例表单')
}

const viewDetail = (row) => {
  ElMessage.info(`查看用例 ${row.id} 详情`)
}

const approveCase = (row) => {
  row.status = 'approved'
  ElMessage.success('用例已通过')
}
</script>

<style scoped>
.case-management {
  padding: 20px;
}
.header {
  margin-bottom: 20px;
}
.filter-bar {
  display: flex;
  align-items: center;
}
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>