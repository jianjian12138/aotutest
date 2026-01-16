<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">版本管理</h1>
      <div class="header-actions">
        <el-button 
          v-if="selectedVersions.length > 0" 
          type="danger" 
          @click="batchDeleteVersions"
          :disabled="isDeleting">
          <el-icon><Delete /></el-icon>
          批量删除 ({{ selectedVersions.length }})
        </el-button>
        <el-button type="primary" @click="createVersion">
          <el-icon><Plus /></el-icon>
          新建版本
        </el-button>
      </div>
    </div>
    
    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-input
              v-model="searchText"
              placeholder="搜索版本名称"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="projectFilter" placeholder="关联项目" clearable @change="handleFilter">
              <el-option
                v-for="project in projects"
                :key="project.id"
                :label="project.name"
                :value="project.id"
              />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-select v-model="baselineFilter" placeholder="版本类型" clearable @change="handleFilter">
              <el-option label="基线版本" :value="true" />
              <el-option label="普通版本" :value="false" />
            </el-select>
          </el-col>
        </el-row>
      </div>
      
      <el-table 
        :data="versions" 
        v-loading="loading" 
        style="width: 100%"
        @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column type="index" label="序号" width="80" :index="getSerialNumber" />
        <el-table-column prop="name" label="版本名称" min-width="100">
          <template #default="{ row }">
            <div class="version-name">
              <span>{{ row.name }}</span>
              <el-tag v-if="row.is_baseline" type="warning" size="small" class="baseline-tag">基线</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="projects" label="关联项目" width="300">
          <template #default="{ row }">
            <div v-if="row.projects && row.projects.length > 0" class="project-tags">
              <el-tag 
                v-for="project in row.projects.slice(0, 2)" 
                :key="project.id" 
                size="small" 
                type="primary"
                class="project-tag"
              >
                {{ project.name }}
              </el-tag>
              <el-tooltip v-if="row.projects.length > 2" :content="getProjectsTooltip(row.projects)">
                <el-tag size="small" type="info" class="project-tag">
                  +{{ row.projects.length - 2 }}
                </el-tag>
              </el-tooltip>
            </div>
            <span v-else class="no-project">未关联项目</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="testcases_count" label="用例数量" width="100">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.testcases_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_by.username" label="创建者" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editVersion(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteVersion(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
    
    <!-- 版本表单对话框 -->
    <el-dialog 
      v-model="versionDialogVisible" 
      :title="isEdit ? '编辑版本' : '创建版本'" 
      width="600px"
    >
      <el-form :model="versionForm" :rules="versionRules" ref="versionFormRef" label-width="120px">
        <el-form-item label="版本名称" prop="name">
          <el-input v-model="versionForm.name" placeholder="请输入版本名称" />
        </el-form-item>
        
        <el-form-item label="关联项目" prop="project_ids">
          <el-select 
            v-model="versionForm.project_ids" 
            placeholder="请选择项目（可多选）" 
            multiple
            style="width: 100%"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="版本描述">
          <el-input
            v-model="versionForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入版本描述"
          />
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="versionForm.is_baseline">设为基线版本</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="versionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveVersion" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const loading = ref(false)
const versions = ref([])
const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchText = ref('')
const projectFilter = ref('')
const baselineFilter = ref('')
const selectedVersions = ref([])
const isDeleting = ref(false)

const versionDialogVisible = ref(false)
const versionFormRef = ref()
const saving = ref(false)
const isEdit = ref(false)
const editingVersionId = ref(null)

const versionForm = reactive({
  name: '',
  description: '',
  project_ids: [],
  is_baseline: false
})

const versionRules = {
  name: [{ required: true, message: '请输入版本名称', trigger: 'blur' }],
  project_ids: [{ required: true, message: '请选择关联项目', trigger: 'change' }]
}

const fetchVersions = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      projects: projectFilter.value,
      is_baseline: baselineFilter.value
    }
    const response = await api.get('/versions/', { params })
    versions.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取版本列表失败')
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error('获取项目列表失败')
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchVersions()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchVersions()
}

const handlePageChange = () => {
  fetchVersions()
}

const createVersion = () => {
  isEdit.value = false
  resetVersionForm()
  versionDialogVisible.value = true
}

const editVersion = (version) => {
  isEdit.value = true
  editingVersionId.value = version.id
  
  versionForm.name = version.name
  versionForm.description = version.description
  versionForm.project_ids = version.projects.map(p => p.id)
  versionForm.is_baseline = version.is_baseline
  
  versionDialogVisible.value = true
}

const saveVersion = async () => {
  if (!versionFormRef.value) return
  
  try {
    await versionFormRef.value.validate()
    saving.value = true
    
    if (isEdit.value) {
      await api.put(`/versions/${editingVersionId.value}/`, versionForm)
      ElMessage.success('版本更新成功')
    } else {
      await api.post('/versions/', versionForm)
      ElMessage.success('版本创建成功')
    }
    
    versionDialogVisible.value = false
    fetchVersions()
    
  } catch (error) {
    if (error.response?.data) {
      const errors = Object.values(error.response.data).flat()
      ElMessage.error(errors[0] || '保存失败')
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

const deleteVersion = async (version) => {
  try {
    await ElMessageBox.confirm('确定要删除这个版本吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/versions/${version.id}/`)
    ElMessage.success('版本删除成功')
    fetchVersions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('版本删除失败')
    }
  }
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedVersions.value = selection
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除
const batchDeleteVersions = async () => {
  if (selectedVersions.value.length === 0) {
    ElMessage.warning('请先选择要删除的版本')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedVersions.value.length} 个版本吗？此操作不可恢复。`,
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

    // 逐个删除选中的版本
    for (const version of selectedVersions.value) {
      try {
        await api.delete(`/versions/${version.id}/`)
        successCount++
      } catch (error) {
        console.error(`删除版本 ${version.id} 失败:`, error)
        failCount++
      }
    }

    // 显示删除结果
    if (successCount > 0) {
      ElMessage.success(`成功删除 ${successCount} 个版本${failCount > 0 ? `，${failCount} 个失败` : ''}`)
    } else {
      ElMessage.error('删除失败')
    }

    // 清空选择并重新加载列表
    selectedVersions.value = []
    fetchVersions()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败: ' + (error.message || '未知错误'))
    }
  } finally {
    isDeleting.value = false
  }
}

const resetVersionForm = () => {
  versionForm.name = ''
  versionForm.description = ''
  versionForm.project_ids = []
  versionForm.is_baseline = false
  editingVersionId.value = null
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const getProjectsTooltip = (projects) => {
  return projects.map(p => p.name).join('、')
}

onMounted(() => {
  fetchProjects()
  fetchVersions()
})
</script>

<style lang="scss" scoped>
.filter-bar {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.version-name {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .baseline-tag {
    font-size: 12px;
  }
}

.project-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  
  .project-tag {
    margin: 0;
  }
}

.no-project {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}
</style>