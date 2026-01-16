<template>
  <div class="execution-list">
    <div class="header">
      <h1>测试计划</h1>
      <div class="header-actions">
        <el-button 
          v-if="selectedPlans.length > 0" 
          type="danger" 
          :icon="Delete"
          @click="batchDeletePlans"
          :disabled="isDeleting">
          批量删除 ({{ selectedPlans.length }})
        </el-button>
        <el-button type="primary" @click="openCreatePlanDialog">
          <el-icon><Plus /></el-icon>
          新建测试计划
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true">
        <el-form-item label="项目">
          <el-select v-model="filters.project" placeholder="选择项目" clearable style="width: 200px">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.is_active" placeholder="选择状态" clearable style="width: 120px">
            <el-option label="激活" :value="true"></el-option>
            <el-option label="已关闭" :value="false"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyFilters">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table 
      :data="testPlans" 
      style="width: 100%" 
      v-loading="loading"
      @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column 
        type="index" 
        label="序号" 
        width="80" 
        :index="getSerialNumber" />
      <el-table-column prop="name" label="计划名称" min-width="200">
        <template #default="scope">
          <el-link type="primary" @click="viewPlan(scope.row.id)">
            {{ scope.row.name }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column prop="projects" label="项目" width="200">
        <template #default="scope">
          <span v-if="scope.row.projects && scope.row.projects.length > 0">
            {{ scope.row.projects.join(', ') }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="120"></el-table-column>
      <el-table-column prop="creator.username" label="创建者" width="120"></el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">
            {{ scope.row.is_active ? '激活' : '已关闭' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="scope">
          <el-button size="small" type="primary" @click="viewPlan(scope.row.id)">
            查看执行
          </el-button>
          <el-button size="small" type="warning" @click="editPlan(scope.row)">
            编辑
          </el-button>
          <el-button 
            size="small" 
            :type="scope.row.is_active ? 'danger' : 'success'"
            @click="togglePlanStatus(scope.row)">
            {{ scope.row.is_active ? '关闭' : '激活' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :small="false"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 创建测试计划对话框 -->
    <el-dialog title="新建测试计划" v-model="isCreatePlanDialogOpen" width="600px">
      <el-form :model="newPlanForm" :rules="planRules" ref="planFormRef" label-width="100px">
        <el-form-item label="计划名称" prop="name">
          <el-input v-model="newPlanForm.name" placeholder="请输入计划名称"></el-input>
        </el-form-item>
        <el-form-item label="计划描述">
          <el-input 
            v-model="newPlanForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入计划描述">
          </el-input>
        </el-form-item>
        <el-form-item label="关联项目" prop="projects">
          <el-select 
            v-model="newPlanForm.projects" 
            multiple 
            placeholder="请选择项目" 
            style="width: 100%"
            @change="handleProjectChange">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="关联版本">
          <el-select v-model="newPlanForm.version" placeholder="请选择版本" style="width: 100%">
            <el-option v-for="item in versions" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="测试用例" prop="testcases">
          <el-select 
            v-model="newPlanForm.testcases" 
            multiple 
            :placeholder="loadingTestcases ? '加载中...' : (!newPlanForm.projects || newPlanForm.projects.length === 0 ? '请先选择项目' : '请选择用例')" 
            style="width: 100%"
            :disabled="!newPlanForm.projects || newPlanForm.projects.length === 0"
            :loading="loadingTestcases"
            @visible-change="handleTestcaseSelectOpen">
            <el-option v-for="item in filteredTestcases" :key="item.id" :label="item.title" :value="item.id">
              <span style="float: left">{{ item.title }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ item.project__name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="指派给">
          <el-select v-model="newPlanForm.assignees" multiple placeholder="请选择执行人员" style="width: 100%">
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isCreatePlanDialogOpen = false">取消</el-button>
          <el-button type="primary" @click="createPlan" :loading="creating">创建</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑测试计划对话框 -->
    <el-dialog title="编辑测试计划" v-model="isEditPlanDialogOpen" width="600px">
      <el-form :model="editPlanForm" :rules="planRules" ref="editPlanFormRef" label-width="100px">
        <el-form-item label="计划名称" prop="name">
          <el-input v-model="editPlanForm.name" placeholder="请输入计划名称"></el-input>
        </el-form-item>
        <el-form-item label="计划描述">
          <el-input 
            v-model="editPlanForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入计划描述">
          </el-input>
        </el-form-item>
        <el-form-item label="关联项目" prop="projects">
          <el-select v-model="editPlanForm.projects" multiple placeholder="请选择项目" style="width: 100%">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="关联版本">
          <el-select v-model="editPlanForm.version" placeholder="请选择版本" style="width: 100%">
            <el-option v-for="item in versions" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="指派给">
          <el-select v-model="editPlanForm.assignees" multiple placeholder="请选择执行人员" style="width: 100%">
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch 
            v-model="editPlanForm.is_active" 
            active-text="激活" 
            inactive-text="已关闭">
          </el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isEditPlanDialogOpen = false">取消</el-button>
          <el-button type="primary" @click="updatePlan" :loading="updating">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'

const router = useRouter()
const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const testPlans = ref([])
const projects = ref([])
const versions = ref([])
const testcases = ref([])
const filteredTestcases = ref([])
const loadingTestcases = ref(false)
const users = ref([])
const selectedPlans = ref([])
const isDeleting = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const filters = reactive({
  project: null,
  is_active: null
})

// 表单
const isCreatePlanDialogOpen = ref(false)
const isEditPlanDialogOpen = ref(false)
const planFormRef = ref()
const editPlanFormRef = ref()
const currentEditingPlan = ref(null)
const newPlanForm = reactive({
  name: '',
  description: '',
  projects: [], // 改为数组
  version: null,
  testcases: [],
  assignees: []
})

const editPlanForm = reactive({
  id: null,
  name: '',
  description: '',
  projects: [],
  version: null,
  assignees: [],
  is_active: true
})

const planRules = {
  name: [
    { required: true, message: '请输入计划名称', trigger: 'blur' }
  ],
  projects: [
    { required: true, message: '请选择项目', trigger: 'change' }
  ],
  testcases: [
    { 
      required: true, 
      message: '请选择至少一个测试用例', 
      trigger: 'change',
      validator: (rule, value, callback) => {
        if (!newPlanForm.projects || newPlanForm.projects.length === 0) {
          callback(new Error('请先选择项目'))
        } else if (!value || value.length === 0) {
          callback(new Error('请选择至少一个测试用例'))
        } else {
          callback()
        }
      }
    }
  ]
}

const fetchTestPlans = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      ...filters
    }
    // 过滤掉空值
    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === '') {
        delete params[key]
      }
    })
    
    const response = await api.get('/executions/plans/', { params })
    testPlans.value = response.data.results || response.data || []
    total.value = response.data.count || testPlans.value.length
  } catch (error) {
    ElMessage.error('获取测试计划失败')
  } finally {
    loading.value = false
  }
}

const fetchBasicData = async () => {
  try {
    const [projectsRes, versionsRes, usersRes] = await Promise.all([
      api.get('/projects/'), // 只显示用户参与的项目
      api.get('/versions/'),
      api.get('/users/users/') // 修正用户API路径
    ])
    
    projects.value = (projectsRes.data.results || projectsRes.data || []).filter(item => item !== null && item !== undefined)
    versions.value = (versionsRes.data.results || versionsRes.data || []).filter(item => item !== null && item !== undefined)
    users.value = (usersRes.data.results || usersRes.data || []).filter(item => item !== null && item !== undefined)
  } catch (error) {
    console.error('获取基础数据失败:', error)
  }
}

// 根据选中的项目加载测试用例
const loadTestcasesByProjects = async (projectIds) => {
  if (!projectIds || projectIds.length === 0) {
    filteredTestcases.value = []
    return
  }
  
  loadingTestcases.value = true
  
  try {
    const params = new URLSearchParams()
    projectIds.forEach(id => params.append('project_ids', id))
    
    console.log('API URL:', `/executions/plans/testcases_by_projects/?${params.toString()}`)
    
    const response = await api.get(`/executions/plans/testcases_by_projects/?${params.toString()}`)
    console.log('API Response:', response.data)
    
    filteredTestcases.value = response.data.results || []
    console.log('Filtered testcases:', filteredTestcases.value)
  } catch (error) {
    console.error('Load testcases error:', error)
    if (error.response?.status === 400) {
      ElMessage.warning(error.response.data.detail || '请先选择项目')
    } else if (error.response?.status === 401) {
      ElMessage.error('请先登录')
    } else {
      ElMessage.error('获取测试用例失败: ' + (error.response?.data?.detail || error.message))
    }
    filteredTestcases.value = []
  } finally {
    loadingTestcases.value = false
  }
}

// 处理测试用例选择器打开事件
const handleTestcaseSelectOpen = (visible) => {
  if (visible && (!newPlanForm.projects || newPlanForm.projects.length === 0)) {
    ElMessage.warning('请先选择项目')
    return false
  }
}

// 处理项目选择变化
const handleProjectChange = (selectedProjects) => {
  // 清空已选择的测试用例
  newPlanForm.testcases = []
  
  // 加载新项目的测试用例
  if (selectedProjects && selectedProjects.length > 0) {
    loadTestcasesByProjects(selectedProjects)
  } else {
    filteredTestcases.value = []
  }
}

const createPlan = async () => {
  try {
    await planFormRef.value.validate()
    creating.value = true
    
    await api.post('/executions/plans/', newPlanForm)
    ElMessage.success('测试计划创建成功')
    isCreatePlanDialogOpen.value = false
    resetPlanForm()
    fetchTestPlans()
  } catch (error) {
    if (error.name !== 'ValidateError') {
      ElMessage.error('创建测试计划失败')
    }
  } finally {
    creating.value = false
  }
}

const viewPlan = (id) => {
  router.push(`/ai-generation/executions/${id}`)
}

const editPlan = async (plan) => {
  try {
    // 获取完整的测试计划详情
    const response = await api.get(`/executions/plans/${plan.id}/`)
    const planDetail = response.data
    
    // 设置当前编辑的计划
    currentEditingPlan.value = planDetail
    
    // 填充编辑表单数据
    Object.assign(editPlanForm, {
      id: planDetail.id,
      name: planDetail.name,
      description: planDetail.description || '',
      projects: planDetail.projects?.map(p => {
        // 如果是字符串，需要找到对应的项目ID
        const project = projects.value.find(proj => proj.name === p)
        return project ? project.id : p
      }) || [],
      version: planDetail.version ? versions.value.find(v => v.name === planDetail.version)?.id : null,
      assignees: planDetail.assignees || [],
      is_active: planDetail.is_active
    })
    
    isEditPlanDialogOpen.value = true
  } catch (error) {
    ElMessage.error('获取测试计划详情失败')
  }
}

const updatePlan = async () => {
  try {
    await editPlanFormRef.value.validate()
    updating.value = true
    
    const updateData = {
      name: editPlanForm.name,
      description: editPlanForm.description,
      projects: editPlanForm.projects,
      version: editPlanForm.version,
      assignees: editPlanForm.assignees,
      is_active: editPlanForm.is_active
    }
    
    await api.put(`/executions/plans/${editPlanForm.id}/`, updateData)
    ElMessage.success('测试计划更新成功')
    isEditPlanDialogOpen.value = false
    resetEditForm()
    fetchTestPlans()
  } catch (error) {
    if (error.name !== 'ValidateError') {
      ElMessage.error('更新测试计划失败')
    }
  } finally {
    updating.value = false
  }
}

const resetEditForm = () => {
  Object.assign(editPlanForm, {
    id: null,
    name: '',
    description: '',
    projects: [],
    version: null,
    assignees: [],
    is_active: true
  })
  currentEditingPlan.value = null
  editPlanFormRef.value?.resetFields()
}

const togglePlanStatus = async (plan) => {
  try {
    const action = plan.is_active ? '关闭' : '激活'
    await ElMessageBox.confirm(`确定要${action}这个测试计划吗？`, '确认操作', {
      type: 'warning'
    })
    
    await api.patch(`/executions/plans/${plan.id}/`, {
      is_active: !plan.is_active
    })
    
    ElMessage.success(`${action}成功`)
    fetchTestPlans()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const openCreatePlanDialog = () => {
  resetPlanForm()
  isCreatePlanDialogOpen.value = true
}

const resetPlanForm = () => {
  Object.assign(newPlanForm, {
    name: '',
    description: '',
    projects: [], // 改为数组
    version: null,
    testcases: [],
    assignees: []
  })
  filteredTestcases.value = [] // 清空过滤后的测试用例
  loadingTestcases.value = false // 重置加载状态
  planFormRef.value?.resetFields()
}

const applyFilters = () => {
  currentPage.value = 1
  fetchTestPlans()
}

const resetFilters = () => {
  Object.assign(filters, {
    project: null,
    is_active: null
  })
  currentPage.value = 1
  fetchTestPlans()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchTestPlans()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchTestPlans()
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedPlans.value = selection
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除
const batchDeletePlans = async () => {
  if (selectedPlans.value.length === 0) {
    ElMessage.warning('请先选择要删除的测试计划')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedPlans.value.length} 个测试计划吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    isDeleting.value = true
    let successCount = 0
    let failCount = 0

    for (const plan of selectedPlans.value) {
      try {
        await api.delete(`/executions/plans/${plan.id}/`)
        successCount++
      } catch (error) {
        console.error(`删除测试计划 ${plan.id} 失败:`, error)
        failCount++
      }
    }

    if (successCount > 0) {
      ElMessage.success(`成功删除 ${successCount} 个测试计划${failCount > 0 ? `，${failCount} 个失败` : ''}`)
    } else {
      ElMessage.error('删除失败')
    }

    selectedPlans.value = []
    fetchTestPlans()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  } finally {
    isDeleting.value = false
  }
}

// 监听项目选择变化
watch(
  () => newPlanForm.projects,
  (newProjects, oldProjects) => {
    // 清空已选择的测试用例
    newPlanForm.testcases = []
    
    // 加载新项目的测试用例
    if (newProjects && newProjects.length > 0) {
      loadTestcasesByProjects(newProjects)
    } else {
      filteredTestcases.value = []
    }
  },
  { deep: true }
)

onMounted(() => {
  fetchTestPlans()
  fetchBasicData()
})
</script>

<style scoped>
.execution-list {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
