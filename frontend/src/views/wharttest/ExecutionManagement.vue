<template>
  <div class="wharttest-execution-management">
    <el-card shadow="hover" class="page-card">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">执行管理</h2>
          <el-button type="primary" @click="handleAddExecution">
            <el-icon><Plus /></el-icon> 新建执行
          </el-button>
        </div>
      </template>
      
      <div class="table-container">
        <el-table :data="executions" border stripe style="width: 100%">
          <el-table-column prop="name" label="执行名称" min-width="200" />
          <el-table-column prop="project_id" label="所属项目" width="150" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result" label="执行结果" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.result === 'success' ? 'success' : 'danger'">{{ scope.row.result }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_time" label="开始时间" width="180" />
          <el-table-column prop="end_time" label="结束时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleViewExecution(scope.row)">
                查看
              </el-button>
              <el-button type="warning" size="small" @click="handleRetryExecution(scope.row)">
                重试
              </el-button>
              <el-button type="danger" size="small" @click="handleAbortExecution(scope.row)">
                终止
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>

      <!-- 执行创建对话框 -->
      <el-dialog
        v-model="dialogVisible"
        title="新建执行"
        width="500px"
      >
        <el-form :model="form" label-width="100px">
          <el-form-item label="执行名称" required>
            <el-input v-model="form.name" placeholder="请输入执行名称" />
          </el-form-item>
          <el-form-item label="所属项目" required>
            <el-select v-model="form.project" placeholder="请选择项目" style="width: 100%">
              <el-option
                v-for="item in projects"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" placeholder="请输入描述" />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="submitForm">确定</el-button>
          </span>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  getWHartTestExecutions, 
  createWHartTestExecution, 
  executeWHartTest, 
  stopWHartTest,
  getWHartTestProjects
} from '@/api/wharttest'

const executions = ref([])
const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框
const dialogVisible = ref(false)
const form = reactive({
  name: '',
  description: '',
  project: null
})

// 获取项目列表
const fetchProjects = async () => {
  try {
    const response = await getWHartTestProjects({ page_size: 100, is_active: true })
    projects.value = response.results || []
  } catch (error) {
    console.error('获取项目列表失败:', error)
  }
}

// 从API获取执行数据
const fetchExecutions = async () => {
  try {
    const response = await getWHartTestExecutions({
      page: currentPage.value,
      page_size: pageSize.value
    })
    executions.value = response.data.results || response.results || []
    total.value = response.data.count || response.count || 0
  } catch (error) {
    console.error('获取执行数据失败:', error)
    ElMessage.error('获取执行数据失败')
    executions.value = []
    total.value = 0
  }
}

const getStatusType = (status) => {
  const statusMap = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'success': 'success',
    'failed': 'danger',
    'aborted': 'info',
    'stopped': 'info'
  }
  return statusMap[status.toLowerCase()] || 'info'
}

const handleAddExecution = () => {
  form.name = ''
  form.description = ''
  form.project = projects.value.length > 0 ? projects.value[0].id : null
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!form.name || !form.project) {
    ElMessage.warning('请填写必要信息')
    return
  }

  try {
    await createWHartTestExecution({
      name: form.name,
      description: form.description,
      project: form.project
    })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchExecutions()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

const handleViewExecution = (execution) => {
  ElMessageBox.alert(`
    <p><strong>名称:</strong> ${execution.name}</p>
    <p><strong>状态:</strong> ${execution.status}</p>
    <p><strong>结果:</strong> ${JSON.stringify(execution.result)}</p>
    <p><strong>日志:</strong> ${execution.logs || '无'}</p>
  `, '执行详情', {
    dangerouslyUseHTMLString: true,
    customStyle: { maxWidth: '600px' }
  })
}

const handleRetryExecution = (execution) => {
  ElMessageBox.confirm('确定要重试此执行吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await executeWHartTest(execution.id)
      ElMessage.success('已触发重试')
      fetchExecutions()
    } catch (error) {
      ElMessage.error('重试失败')
    }
  }).catch(() => {})
}

const handleAbortExecution = (execution) => {
  ElMessageBox.confirm('确定要终止此执行吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await stopWHartTest(execution.id)
      ElMessage.success('执行已终止')
      fetchExecutions()
    } catch (error) {
      ElMessage.error('终止失败')
    }
  }).catch(() => {})
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchExecutions()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchExecutions()
}

onMounted(() => {
  fetchProjects()
  fetchExecutions()
})
</script>

<style scoped lang="scss">
.wharttest-execution-management {
  padding: 0;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: #2c3e50;
  }
}

.table-container {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>