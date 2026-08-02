<template>
  <BasePage title="统一项目管理">
    <template #actions>
      <PremiumButton type="primary" glow @click="handleCreateProject">
        <el-icon><Plus /></el-icon>
        新建项目
      </PremiumButton>
    </template>

    <div class="unified-project-list-wrapper">
      <PremiumCard class="filter-card" padding="16px 24px">
        <div class="filter-section">
          <el-input
            v-model="searchText"
            placeholder="搜索项目名称"
            clearable
            style="width: 250px"
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-select
            v-model="projectTypeFilter"
            placeholder="项目类型"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="API测试" value="API" />
            <el-option label="UI自动化" value="UI" />
            <el-option label="性能测试" value="PERFORMANCE" />
            <el-option label="通用项目" value="GENERAL" />
          </el-select>

          <el-select
            v-model="statusFilter"
            placeholder="状态"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="进行中" value="active" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已完成" value="completed" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </div>
      </PremiumCard>

      <PremiumCard class="table-card" padding="0">
        <el-table class="premium-table" :data="projects" v-loading="loading" stripe style="width: 100%">
          <el-table-column prop="name" label="项目名称" min-width="200">
        <template #default="{ row }">
          <el-link @click="viewProject(row.id)" type="primary">
            {{ row.name }}
          </el-link>
        </template>
      </el-table-column>

      <el-table-column prop="project_type" label="项目类型" width="120">
        <template #default="{ row }">
          <el-tag :type="getProjectTypeTag(row.project_type)">
            {{ getProjectTypeText(row.project_type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />

      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="members_count" label="成员数" width="80" align="center" />

      <el-table-column prop="owner.username" label="负责人" width="120" />

      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="viewProject(row.id)">查看</el-button>
          <el-button size="small" @click="editProject(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteProject(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

        <div class="pagination-footer">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next, jumper"
            @current-change="handlePageChange"
          />
        </div>
      </PremiumCard>
    </div>

    <!-- 创建/编辑项目对话框 -->
    <el-dialog
      :title="isEdit ? '编辑项目' : '新建项目'"
      v-model="showDialog"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="projectForm" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="projectForm.name" placeholder="请输入项目名称" />
        </el-form-item>

        <el-form-item label="项目类型" prop="project_type">
          <el-select v-model="projectForm.project_type" placeholder="请选择项目类型" style="width: 100%">
            <el-option label="API测试" value="API" />
            <el-option label="UI自动化" value="UI" />
            <el-option label="性能测试" value="PERFORMANCE" />
            <el-option label="通用项目" value="GENERAL" />
          </el-select>
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="projectForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入项目描述"
          />
        </el-form-item>

        <el-form-item label="状态" prop="status">
          <el-select v-model="projectForm.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="进行中" value="active" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已完成" value="completed" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>

        <el-form-item label="基础URL" prop="base_url">
          <el-input v-model="projectForm.base_url" placeholder="请输入基础URL" />
        </el-form-item>

        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker
            v-model="projectForm.start_date"
            type="date"
            placeholder="选择开始日期"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker
            v-model="projectForm.end_date"
            type="date"
            placeholder="选择结束日期"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDialog = false">取消</el-button>
          <PremiumButton type="primary" @click="handleSave" :loading="saving" glow>保存</PremiumButton>
        </span>
      </template>
    </el-dialog>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import {
  getProjectList,
  createProject,
  updateProject,
  deleteProject as deleteProjectApi
} from '@/api/unified/project'

const router = useRouter()

// 数据
const projects = ref([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const searchText = ref('')
const projectTypeFilter = ref('')
const statusFilter = ref('')

// 表单
const projectForm = reactive({
  name: '',
  project_type: 'GENERAL',
  description: '',
  status: 'active',
  base_url: '',
  start_date: '',
  end_date: ''
})

const formRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  project_type: [{ required: true, message: '请选择项目类型', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

let editingId = null

// 方法
const fetchProjects = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      project_type: projectTypeFilter.value,
      status: statusFilter.value
    }
    const response = await getProjectList(params)
    projects.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取项目列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchProjects()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchProjects()
}

const handlePageChange = () => {
  fetchProjects()
}

const handleCreateProject = () => {
  isEdit.value = false
  editingId = null
  Object.assign(projectForm, {
    name: '',
    project_type: 'GENERAL',
    description: '',
    status: 'active',
    base_url: '',
    start_date: '',
    end_date: ''
  })
  showDialog.value = true
}

const editProject = (row) => {
  isEdit.value = true
  editingId = row.id
  Object.assign(projectForm, {
    name: row.name,
    project_type: row.project_type,
    description: row.description,
    status: row.status,
    base_url: row.base_url || '',
    start_date: row.start_date || '',
    end_date: row.end_date || ''
  })
  showDialog.value = true
}

const handleSave = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      const data = { ...projectForm }

      if (isEdit.value) {
        await updateProject(editingId, data)
        ElMessage.success('项目更新成功')
      } else {
        await createProject(data)
        ElMessage.success('项目创建成功')
      }

      showDialog.value = false
      fetchProjects()
    } catch (error) {
      ElMessage.error(isEdit.value ? '项目更新失败' : '项目创建失败')
      console.error(error)
    } finally {
      saving.value = false
    }
  })
}

const deleteProject = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目 "${row.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteProjectApi(row.id)
    ElMessage.success('项目删除成功')
    fetchProjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('项目删除失败')
      console.error(error)
    }
  }
}

const viewProject = (id) => {
  router.push(`/unified/projects/${id}`)
}

// 辅助方法
const getProjectTypeTag = (type) => {
  const tags = {
    API: 'primary',
    UI: 'success',
    PERFORMANCE: 'warning',
    GENERAL: 'info'
  }
  return tags[type] || 'info'
}

const getProjectTypeText = (type) => {
  const texts = {
    API: 'API测试',
    UI: 'UI自动化',
    PERFORMANCE: '性能测试',
    GENERAL: '通用项目'
  }
  return texts[type] || type
}

const getStatusType = (status) => {
  const types = {
    active: 'success',
    paused: 'warning',
    completed: 'info',
    archived: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    active: '进行中',
    paused: '已暂停',
    completed: '已完成',
    archived: '已归档'
  }
  return texts[status] || status
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.unified-project-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-section {
  display: flex;
  gap: 12px;
}
</style>
