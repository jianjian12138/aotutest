<template>
  <div class="wharttest-task-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">任务管理</h2>
          <el-button type="primary" @click="handleAddTask">
            <el-icon><Plus /></el-icon> 新建任务
          </el-button>
        </div>
      </template>
      
      <div class="table-container">
        <el-table :data="tasks" border stripe style="width: 100%">
          <el-table-column prop="name" label="任务名称" min-width="200" />
          <el-table-column prop="project_id" label="所属项目" width="150" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.priority === 'high' ? 'danger' : scope.row.priority === 'medium' ? 'warning' : 'success'">
                {{ scope.row.priority }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleViewTask(scope.row)">
                查看
              </el-button>
              <el-button type="warning" size="small" @click="handleEditTask(scope.row)">
                编辑
              </el-button>
              <el-button type="danger" size="small" @click="handleDeleteTask(scope.row)">
                删除
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

      <!-- 任务编辑对话框 -->
      <el-dialog
        v-model="dialogVisible"
        :title="dialogType === 'create' ? '新建任务' : '编辑任务'"
        width="500px"
      >
        <el-form :model="form" label-width="100px">
          <el-form-item label="任务名称" required>
            <el-input v-model="form.name" placeholder="请输入任务名称" />
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
          <el-form-item label="任务类型">
            <el-select v-model="form.task_type" placeholder="请选择类型">
              <el-option label="手动" value="manual" />
              <el-option label="自动" value="automated" />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="form.priority" placeholder="请选择优先级">
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status" placeholder="请选择状态">
              <el-option label="等待中" value="pending" />
              <el-option label="进行中" value="active" />
              <el-option label="已完成" value="completed" />
              <el-option label="挂起" value="suspended" />
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
  getWHartTestTasks, 
  createWHartTestTask, 
  updateWHartTestTask, 
  deleteWHartTestTask,
  getWHartTestProjects
} from '@/api/wharttest'

const tasks = ref([])
const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框
const dialogVisible = ref(false)
const dialogType = ref('create')
const form = reactive({
  id: null,
  name: '',
  description: '',
  project: null,
  task_type: 'manual',
  priority: 'medium',
  status: 'pending'
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

// 从API获取任务数据
const fetchTasks = async () => {
  try {
    const response = await getWHartTestTasks({
      page: currentPage.value,
      page_size: pageSize.value
    })
    tasks.value = response.data.results || response.results || []
    total.value = response.data.count || response.count || 0
  } catch (error) {
    console.error('获取任务数据失败:', error)
    ElMessage.error('获取任务数据失败')
    tasks.value = []
    total.value = 0
  }
}

const getStatusType = (status) => {
  const statusMap = {
    'active': 'success',
    'pending': 'info',
    'completed': 'success',
    'failed': 'danger',
    'suspended': 'warning'
  }
  return statusMap[status] || 'info'
}

const handleAddTask = () => {
  dialogType.value = 'create'
  form.id = null
  form.name = ''
  form.description = ''
  form.project = projects.value.length > 0 ? projects.value[0].id : null
  form.task_type = 'manual'
  form.priority = 'medium'
  form.status = 'pending'
  dialogVisible.value = true
}

const handleViewTask = (task) => {
  dialogType.value = 'edit'
  fillForm(task)
  dialogVisible.value = true
}

const handleEditTask = (task) => {
  dialogType.value = 'edit'
  fillForm(task)
  dialogVisible.value = true
}

const fillForm = (task) => {
  form.id = task.id
  form.name = task.name
  form.description = task.description
  form.project = task.project
  form.task_type = task.task_type
  form.priority = task.priority
  form.status = task.status
}

const handleDeleteTask = (task) => {
  ElMessageBox.confirm('确定要删除此任务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteWHartTestTask(task.id)
      ElMessage.success('任务已删除')
      fetchTasks()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const submitForm = async () => {
  if (!form.name || !form.project) {
    ElMessage.warning('请填写必要信息')
    return
  }

  try {
    const data = {
      name: form.name,
      description: form.description,
      project: form.project,
      task_type: form.task_type,
      priority: form.priority,
      status: form.status
    }

    if (dialogType.value === 'create') {
      await createWHartTestTask(data)
      ElMessage.success('任务创建成功')
    } else {
      await updateWHartTestTask(form.id, data)
      ElMessage.success('任务更新成功')
    }
    dialogVisible.value = false
    fetchTasks()
  } catch (error) {
    ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchTasks()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchTasks()
}

onMounted(() => {
  fetchProjects()
  fetchTasks()
})
</script>

<style scoped lang="scss">
.wharttest-task-management {
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