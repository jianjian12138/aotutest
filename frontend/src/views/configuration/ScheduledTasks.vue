<template>
  <div class="page-container">
    <div class="page-header">
      <h3 class="page-title">定时任务管理</h3>
      <div class="header-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新增任务
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <div class="card-container">
        <!-- 搜索过滤 -->
        <div class="search-filter">
          <el-form :inline="true" :model="filters">
            <el-form-item label="任务名称">
              <el-input v-model="filters.search" placeholder="搜索任务名称" clearable @keyup.enter="loadData" />
            </el-form-item>
            <el-form-item label="任务类型">
              <el-select v-model="filters.task_type" placeholder="全部类型" clearable @change="loadData">
                <el-option label="接口测试" value="API" />
                <el-option label="UI自动化" value="UI" />
                <el-option label="性能测试" value="PERFORMANCE" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadData">查询</el-button>
              <el-button @click="resetFilters">重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 任务列表 -->
        <el-table :data="tasks" v-loading="loading" style="width: 100%; flex: 1;">
        <el-table-column prop="name" label="任务名称" min-width="150" />
        <el-table-column label="所属项目" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.api_project_name" type="success">API: {{ row.api_project_name }}</el-tag>
            <el-tag v-else-if="row.project_name" type="info">通用: {{ row.project_name }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="task_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTaskTypeTag(row.task_type)">{{ row.task_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_type" label="触发方式" width="100" />
        <el-table-column prop="cron_expression" label="Cron表达式" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_run_time" label="最后运行" width="160" />
        <el-table-column prop="next_run_time" label="下次运行" width="160" />
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleRunOnce(row)">立即运行</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
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
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑任务' : '新增任务'"
      width="600px"
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="所属项目" prop="project_id_combined">
          <el-select v-model="form.project_id_combined" placeholder="选择项目" style="width: 100%" @change="handleProjectChange">
            <el-option-group label="接口测试项目">
              <el-option
                v-for="item in apiProjects"
                :key="'api_' + item.id"
                :label="item.name"
                :value="'api_' + item.id"
              />
            </el-option-group>
            <el-option-group label="通用项目">
              <el-option
                v-for="item in projects"
                :key="'gen_' + item.id"
                :label="item.name"
                :value="'gen_' + item.id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" placeholder="选择类型" style="width: 100%">
            <el-option label="接口测试" value="API" />
            <el-option label="UI自动化" value="UI" />
            <el-option label="性能测试" value="PERFORMANCE" />
          </el-select>
        </el-form-item>
        
        <!-- 动态表单项：根据类型显示不同的关联选择 -->
        <el-form-item v-if="form.task_type === 'API'" label="API套件" prop="api_test_suite">
           <el-input v-model="form.api_test_suite" placeholder="请输入API测试套件ID" />
           <!-- TODO: Replace with Select fetching API suites -->
        </el-form-item>
        <el-form-item v-if="form.task_type === 'UI'" label="UI套件" prop="ui_test_suite">
           <el-input v-model="form.ui_test_suite" placeholder="请输入UI测试套件ID" />
        </el-form-item>
        <el-form-item v-if="form.task_type === 'PERFORMANCE'" label="性能套件" prop="performance_test_suite">
           <el-input v-model="form.performance_test_suite" placeholder="请输入性能测试套件ID" />
        </el-form-item>

        <el-form-item label="触发类型" prop="trigger_type">
          <el-radio-group v-model="form.trigger_type">
            <el-radio label="CRON">Cron表达式</el-radio>
            <el-radio label="INTERVAL">固定间隔</el-radio>
            <el-radio label="ONCE">单次执行</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item v-if="form.trigger_type === 'CRON'" label="Cron表达式" prop="cron_expression">
          <el-input v-model="form.cron_expression" placeholder="例如: 0 0 * * *" />
        </el-form-item>
        <el-form-item v-if="form.trigger_type === 'INTERVAL'" label="间隔(秒)" prop="interval_seconds">
          <el-input-number v-model="form.interval_seconds" :min="1" />
        </el-form-item>
        
        <el-form-item label="通知配置" prop="notification_config">
          <el-select v-model="form.notification_config" placeholder="选择通知配置" clearable style="width: 100%">
            <el-option
              v-for="item in notificationConfigs"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="状态" prop="status">
          <el-switch
            v-model="form.status"
            active-value="ACTIVE"
            inactive-value="PAUSED"
            active-text="激活"
            inactive-text="暂停"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import schedulerApi from '@/api/scheduler'
import api from '@/utils/api' // Generic api for projects

const loading = ref(false)
const tasks = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const projects = ref([])
const apiProjects = ref([])
const notificationConfigs = ref([])

const filters = reactive({
  search: '',
  task_type: ''
})

const form = reactive({
  id: null,
  name: '',
  project: null,
  api_project: null,
  project_id_combined: '',
  task_type: 'API',
  trigger_type: 'CRON',
  cron_expression: '',
  interval_seconds: 3600,
  status: 'ACTIVE',
  api_test_suite: null,
  ui_test_suite: null,
  performance_test_suite: null,
  notification_config: null
})

const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  project_id_combined: [{ required: true, message: '请选择项目', trigger: 'change' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      name: filters.search,
      task_type: filters.task_type
    }
    const res = await schedulerApi.getTasks(params)
    tasks.value = res.data.results
    total.value = res.data.count
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

const loadProjects = async () => {
  try {
    // 加载通用项目
    const res = await api.get('/projects/')
    projects.value = res.data.results || res.data
    
    // 加载接口测试项目
    const apiRes = await api.get('/api-testing/projects/')
    apiProjects.value = apiRes.data.results || apiRes.data
  } catch (error) {
    console.error('加载项目失败:', error)
  }
}

const handleProjectChange = (val) => {
  if (!val) {
    form.project = null
    form.api_project = null
    return
  }
  
  if (val.startsWith('api_')) {
    form.api_project = parseInt(val.replace('api_', ''))
    form.project = null
  } else if (val.startsWith('gen_')) {
    form.project = parseInt(val.replace('gen_', ''))
    form.api_project = null
  }
}

const loadNotificationConfigs = async () => {
  try {
    const res = await schedulerApi.getNotificationConfigs()
    notificationConfigs.value = res.data.results || res.data
  } catch (error) {
    console.error(error)
  }
}

const getTaskTypeTag = (type) => {
  const map = {
    'API': 'primary',
    'UI': 'warning',
    'PERFORMANCE': 'danger'
  }
  return map[type] || 'info'
}

const handleAdd = () => {
  isEdit.value = false
  form.id = null
  form.name = ''
  form.status = 'ACTIVE'
  // reset other fields
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, row)
  
  // 设置组合项目 ID
  if (row.api_project) {
    form.project_id_combined = 'api_' + row.api_project
  } else if (row.project) {
    form.project_id_combined = 'gen_' + row.project
  } else {
    form.project_id_combined = ''
  }
  
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确认删除该任务吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await schedulerApi.deleteTask(row.id)
      ElMessage.success('删除成功')
      loadData()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const handleRunOnce = async (row) => {
  try {
    await schedulerApi.runTaskOnce(row.id)
    ElMessage.success('任务已触发执行')
  } catch (error) {
    ElMessage.error('触发失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        const submitData = { ...form }
        delete submitData.project_id_combined
        
        if (isEdit.value) {
          await schedulerApi.updateTask(form.id, submitData)
          ElMessage.success('更新成功')
        } else {
          await schedulerApi.createTask(submitData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadData()
      } catch (error) {
        console.error('保存任务失败:', error)
        ElMessage.error(error.response?.data?.detail || (isEdit.value ? '更新失败' : '创建失败'))
      } finally {
        submitting.value = false
      }
    }
  })
}

const handleSizeChange = (val) => {
  pageSize.value = val
  loadData()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadData()
}

const resetFilters = () => {
  filters.search = ''
  filters.task_type = ''
  loadData()
}

onMounted(() => {
  loadData()
  loadProjects()
  loadNotificationConfigs()
})
</script>

<style scoped>
.page-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  background-color: var(--el-bg-color-page);
  max-width: 100%; /* 新增：覆盖全局样式的 max-width: 1600px，确保铺满 */
}

.page-header {
  flex-shrink: 0;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  margin: 0;
}

.page-title::before {
  content: '';
  width: 4px;
  height: 16px;
  background-color: var(--el-color-primary);
  margin-right: 8px;
  border-radius: 2px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.main-content {
  flex: 1;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-container {
  flex: 1;
  background: #fff;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.search-filter {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
