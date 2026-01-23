<template>
  <div class="wharttest-project-management">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header page-header" style="margin-bottom: 0;">
          <h2 class="page-title">项目管理</h2>
          <el-button type="primary" @click="handleAddProject">
            <el-icon><Plus /></el-icon> 新建项目
          </el-button>
        </div>
      </template>
      
      <div class="table-container">
        <el-table :data="projects" border stripe style="width: 100%">
          <el-table-column prop="name" label="项目名称" min-width="200" />
          <el-table-column prop="description" label="项目描述" min-width="300" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'active' ? 'success' : 'info'">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleViewProject(scope.row)">
                查看
              </el-button>
              <el-button type="warning" size="small" @click="handleEditProject(scope.row)">
                编辑
              </el-button>
              <el-button type="danger" size="small" @click="handleDeleteProject(scope.row)">
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

      <!-- 项目编辑对话框 -->
      <el-dialog
        v-model="dialogVisible"
        :title="dialogType === 'create' ? '新建项目' : '编辑项目'"
        width="500px"
      >
        <el-form :model="form" label-width="120px">
          <el-form-item label="项目名称" required>
            <el-input v-model="form.name" placeholder="请输入项目名称" />
          </el-form-item>
          <el-form-item label="WHartTest ID" required>
            <el-input v-model="form.wharttest_project_id" placeholder="WHartTest中的项目ID" />
          </el-form-item>
          <el-form-item label="关联配置" required>
            <el-select v-model="form.config" placeholder="请选择配置" style="width: 100%">
              <el-option
                v-for="item in configs"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" placeholder="请输入描述" />
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="form.is_active" active-text="激活" inactive-text="禁用" />
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
  getWHartTestProjects, 
  createWHartTestProject, 
  updateWHartTestProject, 
  deleteWHartTestProject,
  getWHartTestConfigs
} from '@/api/wharttest'

const projects = ref([])
const configs = ref([])
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
  wharttest_project_id: '',
  config: null,
  is_active: true
})

// 获取配置列表
const fetchConfigs = async () => {
  try {
    const response = await getWHartTestConfigs({ page_size: 100, is_active: true })
    configs.value = response.results || []
  } catch (error) {
    console.error('获取配置列表失败:', error)
  }
}

// 从API获取项目数据
const fetchProjects = async () => {
  try {
    const response = await getWHartTestProjects({
      page: currentPage.value,
      page_size: pageSize.value
    })
    projects.value = response.data.results || response.results || []
    total.value = response.data.count || response.count || 0
  } catch (error) {
    console.error('获取项目数据失败:', error)
    ElMessage.error('获取项目数据失败')
    projects.value = []
    total.value = 0
  }
}

const handleAddProject = () => {
  dialogType.value = 'create'
  form.id = null
  form.name = ''
  form.description = ''
  form.wharttest_project_id = ''
  form.config = configs.value.length > 0 ? configs.value[0].id : null
  form.is_active = true
  dialogVisible.value = true
}

const handleViewProject = (project) => {
  // 简单查看，复用编辑弹窗但禁用
  dialogType.value = 'edit' // 或 view
  // 这里为了简单，直接填充并显示，实际可禁用输入
  fillForm(project)
  dialogVisible.value = true
}

const handleEditProject = (project) => {
  dialogType.value = 'edit'
  fillForm(project)
  dialogVisible.value = true
}

const fillForm = (project) => {
  form.id = project.id
  form.name = project.name
  form.description = project.description
  form.wharttest_project_id = project.wharttest_project_id
  form.config = project.config
  form.is_active = project.is_active
}

const handleDeleteProject = (project) => {
  ElMessageBox.confirm('确定要删除此项目吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteWHartTestProject(project.id)
      ElMessage.success('项目已删除')
      fetchProjects()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const submitForm = async () => {
  if (!form.name || !form.wharttest_project_id || !form.config) {
    ElMessage.warning('请填写必要信息')
    return
  }

  try {
    const data = {
      name: form.name,
      description: form.description,
      wharttest_project_id: form.wharttest_project_id,
      config: form.config,
      is_active: form.is_active
    }

    if (dialogType.value === 'create') {
      await createWHartTestProject(data)
      ElMessage.success('项目创建成功')
    } else {
      await updateWHartTestProject(form.id, data)
      ElMessage.success('项目更新成功')
    }
    dialogVisible.value = false
    fetchProjects()
  } catch (error) {
    ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchProjects()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchProjects()
}

onMounted(() => {
  fetchConfigs()
  fetchProjects()
})
</script>

<style scoped lang="scss">
.wharttest-project-management {
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